import { useState } from "react";
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import { useTestData } from "../context/TestDataContext";
import { useCrud } from "../hooks/useCrud";
import { testPropertyIds, visibleProperties } from "../utils/testData";
import type { CostCategory, Invoice, InvoiceItem, LeaseUnit, Property } from "../api/types";

interface ItemDraft {
  from_date: string;
  to_date: string;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  gross_amount: string;
}

const EMPTY_ITEM: ItemDraft = {
  from_date: "",
  to_date: "",
  description: "",
  quantity: "",
  unit: "",
  unit_price: "",
  gross_amount: "",
};

/** Rechnungsarten – die Auswahl bestimmt das Eingabelayout. */
const INVOICE_KINDS = [
  { value: "GRUNDSTEUER", label: "Grundsteuer" },
  { value: "WASSER", label: "Wasser" },
  { value: "STROM", label: "Strom" },
  { value: "VERSICHERUNG_HAFTPFLICHT", label: "Versicherung Haftpflicht" },
  { value: "VERSICHERUNG_WOHNGEBAEUDE", label: "Versicherung Wohngebäude" },
  { value: "GARTEN", label: "Garten" },
  { value: "LEGIONELLEN", label: "Legionellenmessung" },
  { value: "SCHORNSTEINFEGER", label: "Schornsteinfeger" },
  { value: "SONSTIGE", label: "Sonstige" },
];

/** Art → passende Kostenart-Namen (Aliase), find-or-create je Objekt. */
const KIND_CATEGORY_NAMES: Record<string, string[]> = {
  GRUNDSTEUER: ["Grundsteuer"],
  WASSER: ["Wasser", "Trinkwasser", "Trinkwassergebühr"],
  STROM: ["Strom", "Hausstrom"],
  VERSICHERUNG_HAFTPFLICHT: ["Haftpflichtversicherung"],
  VERSICHERUNG_WOHNGEBAEUDE: ["Gebäudeversicherung", "Gebäudebrand-/Elementarversicherung"],
  GARTEN: ["Gartenpflege"],
  LEGIONELLEN: ["Legionellenmessung"],
  SCHORNSTEINFEGER: ["Schornsteinfeger", "Schornstein/Wartung"],
};

const kindLabel = (kind?: string | null) =>
  INVOICE_KINDS.find((k) => k.value === kind)?.label ?? "";

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

export default function InvoicesPage() {
  const { list, create, update, remove } = useCrud<Invoice>("/invoices", "invoices");
  const props = useCrud<Property>("/properties", "properties");
  const cats = useCrud<CostCategory>("/cost-categories", "cost-categories");
  const units = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const { hideTest } = useTestData();
  const [propertyFilter, setPropertyFilter] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Invoice | null>(null);
  const [del, setDel] = useState<Invoice | null>(null);
  const qc = useQueryClient();
  const [form, setForm] = useState({
    property_id: "",
    kind: "",
    cost_category_id: "",
    lease_unit_id: "",
    invoice_number: "",
    supplier: "",
    description: "",
    issue_date: "",
    period_start: "",
    period_end: "",
    valid_from: "",
    annual_amount: "",
  });
  const [items, setItems] = useState<ItemDraft[]>([{ ...EMPTY_ITEM }]);
  // Geltungsbereich beim Schornsteinfeger: Objekt (ganzes Haus) oder Wohneinheit
  const [scope, setScope] = useState<"" | "OBJEKT" | "WOHNEINHEIT">("OBJEKT");

  const catName = (id: number) => cats.list.data?.find((c) => c.id === id)?.name ?? "";
  const propName = (id: number) => props.list.data?.find((p) => p.id === id)?.name ?? "";
  const unitName = (id?: number | null) =>
    units.list.data?.find((u) => u.id === id)?.designation ?? "";

  /** Find-or-create der Kostenart passend zur Art (außer Sonstige). */
  const ensureCategory = async (propertyId: number, kind: string): Promise<number | null> => {
    const aliases = KIND_CATEGORY_NAMES[kind];
    if (!aliases?.length) return null; // Sonstige → User wählt Kostenart
    const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9äöüß]/g, "");
    const hit = (cats.list.data ?? []).find(
      (c) => c.property_id === propertyId && aliases.some((a) => norm(c.name) === norm(a)),
    );
    if (hit) return hit.id;
    const created = (
      await api.post<CostCategory>("/cost-categories", { property_id: propertyId, name: aliases[0] })
    ).data;
    qc.invalidateQueries({ queryKey: ["cost-categories"] });
    return created.id;
  };

  const onKindChange = async (v: string | null) => {
    const kind = v ?? "";
    const pid = Number(form.property_id);
    setForm((prev) => ({ ...prev, kind, cost_category_id: "" }));
    if (!pid || !kind) return;
    const catId = await ensureCategory(pid, kind);
    if (catId) setForm((prev) => ({ ...prev, cost_category_id: String(catId) }));
  };

  const onPropertyChange = async (v: string | null) => {
    const pid = v ?? "";
    const kind = form.kind;
    setForm((prev) => ({ ...prev, property_id: pid, cost_category_id: "", lease_unit_id: "" }));
    if (!pid || !kind) return;
    const catId = await ensureCategory(Number(pid), kind);
    if (catId) setForm((prev) => ({ ...prev, cost_category_id: String(catId) }));
  };

  const openCreate = () => {
    setEdit(null);
    setForm({
      property_id: propertyFilter ?? "",
      kind: "",
      cost_category_id: "",
      lease_unit_id: "",
      invoice_number: "",
      supplier: "",
      description: "",
      issue_date: "",
      period_start: "",
      period_end: "",
      valid_from: "",
      annual_amount: "",
    });
    setItems([{ ...EMPTY_ITEM }]);
    setScope("OBJEKT");
    setOpen(true);
  };

  const openEdit = (inv: Invoice) => {
    setEdit(inv);
    setForm({
      property_id: String(inv.property_id),
      kind: inv.kind ?? "",
      cost_category_id: String(inv.cost_category_id),
      lease_unit_id: inv.lease_unit_id != null ? String(inv.lease_unit_id) : "",
      invoice_number: inv.invoice_number ?? "",
      supplier: inv.supplier ?? "",
      description: inv.description ?? "",
      issue_date: inv.issue_date ?? "",
      period_start: inv.period_start,
      period_end: inv.period_end,
      valid_from: inv.valid_from ?? "",
      annual_amount: inv.annual_amount != null ? String(inv.annual_amount) : "",
    });
    setItems(
      inv.items.length
        ? inv.items.map((i) => ({
            from_date: i.from_date,
            to_date: i.to_date,
            description: i.description ?? "",
            quantity: i.quantity != null ? String(i.quantity) : "",
            unit: i.unit ?? "",
            unit_price: i.unit_price != null ? String(i.unit_price) : "",
            gross_amount: String(i.gross_amount),
          }))
        : [{ ...EMPTY_ITEM }],
    );
    setScope(inv.lease_unit_id != null ? "WOHNEINHEIT" : "OBJEKT");
    setOpen(true);
  };

  const setItem = (idx: number, patch: Partial<ItemDraft>) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  };

  const isGrundsteuer = form.kind === "GRUNDSTEUER";

  const toPayload = () => {
    const itemPayload: InvoiceItem[] = items
      // Leere Positionsdaten → Rechnungszeitraum verwenden (flache Rechnung)
      .map((it) => ({
        from_date: it.from_date || form.period_start,
        to_date: it.to_date || form.period_end,
        description: it.description || null,
        quantity: it.quantity === "" ? null : it.quantity,
        unit: it.unit || null,
        unit_price: it.unit_price === "" ? null : it.unit_price,
        gross_amount: it.gross_amount || "0",
      }))
      // Wirklich leere Zeilen (kein Betrag) verwerfen
      .filter((it) => it.gross_amount !== "0");
    const period = isGrundsteuer
      ? { period_start: form.valid_from, period_end: form.valid_from }
      : { period_start: form.period_start, period_end: form.period_end };
    return {
      property_id: Number(form.property_id),
      cost_category_id: Number(form.cost_category_id),
      kind: form.kind || null,
      valid_from: form.valid_from || null,
      annual_amount: form.annual_amount === "" ? null : form.annual_amount,
      lease_unit_id:
        scope === "WOHNEINHEIT" && form.lease_unit_id !== "" ? Number(form.lease_unit_id) : null,
      invoice_number: form.invoice_number || null,
      supplier: form.supplier || null,
      description: form.description || null,
      issue_date: form.issue_date || null,
      ...period,
      items: isGrundsteuer ? [] : itemPayload,
    };
  };

  const save = () => {
    const payload = toPayload();
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };

  const testIds = testPropertyIds(props.list.data ?? []);
  const filtered = (list.data ?? []).filter(
    (inv) =>
      (!propertyFilter || inv.property_id === Number(propertyFilter)) &&
      (!hideTest || !testIds.has(inv.property_id)),
  );

  const canSave =
    form.property_id !== "" &&
    form.kind !== "" &&
    form.cost_category_id !== "" &&
    (isGrundsteuer
      ? form.valid_from !== "" && form.annual_amount !== ""
      : form.period_start !== "" && form.period_end !== "") &&
    (scope !== "WOHNEINHEIT" || form.lease_unit_id !== "");

  return (
    <Stack>
      <Title order={2}>Rechnungen</Title>
      <Group>
        <Select
          label="Objekt filter"
          placeholder="Alle Objekte"
          clearable
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyFilter}
          onChange={setPropertyFilter}
          w={280}
        />
        <Button onClick={openCreate} mt="auto">
          Neue Rechnung
        </Button>
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Objekt</Table.Th>
            <Table.Th>Art</Table.Th>
            <Table.Th>Kostenart</Table.Th>
            <Table.Th>Zeitraum</Table.Th>
            <Table.Th>Lieferant</Table.Th>
            <Table.Th>Positionen</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {filtered.map((inv) => (
            <Table.Tr key={inv.id}>
              <Table.Td>{propName(inv.property_id)}</Table.Td>
              <Table.Td>{kindLabel(inv.kind) || "—"}</Table.Td>
              <Table.Td>{catName(inv.cost_category_id)}</Table.Td>
              <Table.Td>
                {inv.kind === "GRUNDSTEUER" && inv.valid_from
                  ? `ab ${inv.valid_from}`
                  : `${inv.period_start} – ${inv.period_end}`}
                {inv.lease_unit_id != null && ` · ${unitName(inv.lease_unit_id)}`}
              </Table.Td>
              <Table.Td>{inv.supplier ?? "—"}</Table.Td>
              <Table.Td>{inv.items.length}</Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(inv)}>
                    Ändern
                  </Button>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => setDel(inv)}>
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Rechnung ändern" : "Neue Rechnung"} size="lg">
        <Stack>
          <Group grow>
            <Select
              label="Objekt"
              data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
              value={form.property_id || null}
              onChange={onPropertyChange}
            />
            <Select
              label="Rechnungsart"
              placeholder="Art wählen"
              data={INVOICE_KINDS}
              value={form.kind || null}
              onChange={onKindChange}
            />
          </Group>
          <Group grow>
            {form.kind === "SONSTIGE" ? (
              <Select
                label="Kostenart"
                data={(cats.list.data ?? [])
                  .filter((c) => c.property_id === Number(form.property_id))
                  .map((c) => ({ value: String(c.id), label: c.name }))}
                value={form.cost_category_id || null}
                onChange={(v) => setForm({ ...form, cost_category_id: v ?? "" })}
              />
            ) : (
              <TextInput
                label="Kostenart (automatisch)"
                readOnly
                value={catName(Number(form.cost_category_id))}
                placeholder="Rechnungsart wählen"
              />
            )}
            <TextInput
              label="Rechnungsnummer"
              value={form.invoice_number}
              onChange={(e) => setForm({ ...form, invoice_number: e.currentTarget.value })}
            />
          </Group>

          {isGrundsteuer ? (
            <>
              <Group grow>
                <TextInput
                  type="date"
                  label="Gültig ab (Bescheid)"
                  value={form.valid_from}
                  onChange={(e) => setForm({ ...form, valid_from: e.currentTarget.value })}
                />
                <NumberInput
                  label="Jahresbetrag (€)"
                  value={form.annual_amount}
                  onChange={(v) => setForm({ ...form, annual_amount: String(v ?? "") })}
                  decimalScale={2}
                />
              </Group>
              <Text size="sm" c="dimmed">
                Die Grundsteuer gilt ab diesem Datum für jedes Abrechnungsjahr, bis ein neuer
                Bescheid erfasst wird.
              </Text>
            </>
          ) : (
            <>
              <Group grow>
                <TextInput
                  type="date"
                  label="Leistung von"
                  value={form.period_start}
                  onChange={(e) => setForm({ ...form, period_start: e.currentTarget.value })}
                />
                <TextInput
                  type="date"
                  label="Leistung bis"
                  value={form.period_end}
                  onChange={(e) => setForm({ ...form, period_end: e.currentTarget.value })}
                />
              </Group>

              {form.kind === "SCHORNSTEINFEGER" && (
                <Group grow>
                  <Select
                    label="Geltungsbereich"
                    data={[
                      { value: "OBJEKT", label: "Objekt (ganzes Haus)" },
                      { value: "WOHNEINHEIT", label: "Wohneinheit" },
                    ]}
                    value={scope || "OBJEKT"}
                    onChange={(v) => {
                      const next = (v as "OBJEKT" | "WOHNEINHEIT") || "OBJEKT";
                      setScope(next);
                      if (next !== "WOHNEINHEIT") {
                        setForm((prev) => ({ ...prev, lease_unit_id: "" }));
                      }
                    }}
                  />
                  {scope === "WOHNEINHEIT" && (
                    <Select
                      label="Wohneinheit"
                      placeholder="Einheit wählen"
                      data={(units.list.data ?? [])
                        .filter((u) => u.property_id === Number(form.property_id))
                        .map((u) => ({ value: String(u.id), label: u.designation }))}
                      value={form.lease_unit_id || null}
                      onChange={(v) => setForm({ ...form, lease_unit_id: v ?? "" })}
                    />
                  )}
                </Group>
              )}

              <Title order={5}>Positionen / Zeitabschnitte</Title>
              {items.map((it, idx) => (
                <Stack key={idx} p="xs" style={{ border: "1px solid #dee2e6", borderRadius: 6 }}>
                  <Group grow>
                    <TextInput
                      type="date"
                      label="Von"
                      value={it.from_date}
                      onChange={(e) => setItem(idx, { from_date: e.currentTarget.value })}
                    />
                    <TextInput
                      type="date"
                      label="Bis"
                      value={it.to_date}
                      onChange={(e) => setItem(idx, { to_date: e.currentTarget.value })}
                    />
                    <TextInput
                      label="Beschreibung"
                      value={it.description}
                      onChange={(e) => setItem(idx, { description: e.currentTarget.value })}
                    />
                  </Group>
                  <Group grow>
                    <NumberInput
                      label="Menge"
                      value={it.quantity}
                      onChange={(v) => setItem(idx, { quantity: String(v ?? "") })}
                      decimalScale={4}
                    />
                    <TextInput
                      label="Einheit (m³, kWh, …)"
                      value={it.unit}
                      onChange={(e) => setItem(idx, { unit: e.currentTarget.value })}
                    />
                    <NumberInput
                      label="Einzelpreis"
                      value={it.unit_price}
                      onChange={(v) => setItem(idx, { unit_price: String(v ?? "") })}
                      decimalScale={6}
                    />
                    <NumberInput
                      label="Betrag (brutto, €)"
                      value={it.gross_amount}
                      onChange={(v) => setItem(idx, { gross_amount: String(v ?? "") })}
                      decimalScale={2}
                    />
                  </Group>
                  {items.length > 1 && (
                    <ActionIcon color="red" variant="light" onClick={() => setItems((prev) => prev.filter((_, i) => i !== idx))}>
                      ✕
                    </ActionIcon>
                  )}
                </Stack>
              ))}
              <Button variant="light" onClick={() => setItems((prev) => [...prev, { ...EMPTY_ITEM }])}>
                + Position hinzufügen
              </Button>
            </>
          )}

          <Group justify="flex-end">
            <Button onClick={save} disabled={!canSave}>
              Speichern
            </Button>
          </Group>
        </Stack>
      </Modal>

      <ConfirmDeleteModal
        opened={!!del}
        message={`Rechnung (${del?.period_start} – ${del?.period_end}) wird dauerhaft gelöscht.`}
        confirmText={del?.supplier || "LÖSCHEN"}
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) remove.mutate(del.id);
          setDel(null);
        }}
      />
    </Stack>
  );
}
