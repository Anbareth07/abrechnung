import { useState } from "react";
import {
  Accordion,
  Button,
  Checkbox,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import PageHelp from "../components/PageHelp";
import { rechnungenHelp } from "../help/helpContent";
import { useTestData } from "../context/TestDataContext";
import { useObject } from "../context/ObjectContext";
import { useCrud } from "../hooks/useCrud";
import { testPropertyIds, visibleProperties } from "../utils/testData";
import type { AllocationConfig, CostCategory, Invoice, LeaseUnit, Property } from "../api/types";

// Abrechnungsjahre: von 2025 bis aktuelles Jahr + 3
const CURRENT_YEAR = new Date().getFullYear();
const DEFAULT_YEAR = CURRENT_YEAR - 1;
const YEARS = Array.from({ length: CURRENT_YEAR + 3 - 2025 + 1 }, (_, i) => String(2025 + i));

/** Umlageschlüssel → deutsche Bezeichnung (für den Hinweistext). */
const KEY_LABELS: Record<string, string> = {
  WF: "Wohnfläche",
  NF: "Nutzfläche",
  WOHNUNG: "Wohnung",
  CONSUMPTION: "Verbrauch",
  NONE: "keine Umlage",
};

const fmt = (v: number) => v.toLocaleString("de-DE", { maximumFractionDigits: 2 });

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

export default function InvoicesPage() {
  const { list, create, update, remove } = useCrud<Invoice>("/invoices", "invoices");
  const props = useCrud<Property>("/properties", "properties");
  const cats = useCrud<CostCategory>("/cost-categories", "cost-categories");
  const units = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const configs = useCrud<AllocationConfig>("/allocation-configs", "allocation-configs");
  const { hideTest } = useTestData();
  const { propertyFilter, setPropertyFilter } = useObject();
  const [yearFilter, setYearFilter] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Invoice | null>(null);
  const [del, setDel] = useState<Invoice | null>(null);
  const [form, setForm] = useState({
    property_id: "",
    year: String(DEFAULT_YEAR),
    cost_category_id: "",
    lease_unit_id: "",
    title: "",
    amount: "",
    comment: "",
  });
  // Dialog nach dem Speichern offen lassen (z. B. für mehrere Rechnungen derselben Kostenstelle)
  const [keepOpen, setKeepOpen] = useState(false);

  const catName = (id: number) => cats.list.data?.find((c) => c.id === id)?.name ?? "";
  const propName = (id: number) => props.list.data?.find((p) => p.id === id)?.name ?? "";
  const unitName = (id?: number | null) =>
    units.list.data?.find((u) => u.id === id)?.designation ?? "";

  // Konfigurierte Kostenstellen des Objekts (Umlageschlüssel), sortiert
  const propConfigs = (configs.list.data ?? [])
    .filter((c) => c.property_id === Number(form.property_id))
    .sort((a, b) => a.sort_order - b.sort_order);
  const selConfig = propConfigs.find((c) => c.cost_category_id === Number(form.cost_category_id));
  // Kostenstelle mit Umlageschlüssel "Wohnung" → zusätzlich Wohnung wählbar
  const isWohnung = selConfig?.allocation_key === "WOHNUNG";

  const openCreate = () => {
    setEdit(null);
    setKeepOpen(false);
    setForm({
      property_id: propertyFilter ?? "",
      year: String(DEFAULT_YEAR),
      cost_category_id: "",
      lease_unit_id: "",
      title: "",
      amount: "",
      comment: "",
    });
    setOpen(true);
  };

  const openEdit = (inv: Invoice) => {
    setEdit(inv);
    setForm({
      property_id: String(inv.property_id),
      year: inv.period_start?.slice(0, 4) || String(DEFAULT_YEAR),
      cost_category_id: String(inv.cost_category_id),
      lease_unit_id: inv.lease_unit_id != null ? String(inv.lease_unit_id) : "",
      title: inv.description ?? "",
      amount: String(inv.items[0]?.gross_amount ?? inv.gross_amount ?? ""),
      comment:
        inv.meta && "kommentar" in inv.meta
          ? String((inv.meta as Record<string, unknown>).kommentar)
          : "",
    });
    setOpen(true);
  };

  const openClone = (inv: Invoice) => {
    // Neue Rechnung auf Basis einer bestehenden – Jahr wird auf das Folgejahr gesetzt
    setEdit(null);
    setKeepOpen(false);
    const srcYear = Number(inv.period_start?.slice(0, 4) ?? DEFAULT_YEAR);
    const nextYear = String(srcYear + 1);
    const year = YEARS.includes(nextYear) ? nextYear : String(srcYear);
    setForm({
      property_id: String(inv.property_id),
      year,
      cost_category_id: String(inv.cost_category_id),
      lease_unit_id: inv.lease_unit_id != null ? String(inv.lease_unit_id) : "",
      title: inv.description ?? "",
      amount: String(inv.items[0]?.gross_amount ?? inv.gross_amount ?? inv.annual_amount ?? ""),
      comment:
        inv.meta && "kommentar" in inv.meta
          ? String((inv.meta as Record<string, unknown>).kommentar)
          : "",
    });
    setOpen(true);
  };

  const toPayload = () => {
    const periodStart = `${form.year}-01-01`;
    const periodEnd = `${form.year}-12-31`;
    const amount = form.amount === "" ? "0" : form.amount;
    return {
      property_id: Number(form.property_id),
      cost_category_id: Number(form.cost_category_id),
      kind: null,
      lease_unit_id: isWohnung ? Number(form.lease_unit_id) : null,
      description: form.title || null,
      gross_amount: amount === "0" ? null : amount,
      meta: form.comment ? { kommentar: form.comment } : {},
      period_start: periodStart,
      period_end: periodEnd,
      items: [
        {
          from_date: periodStart,
          to_date: periodEnd,
          description: form.title || null,
          gross_amount: amount,
        },
      ],
    };
  };

  const save = () => {
    const payload = toPayload();
    const done = () => {
      if (keepOpen && !edit) {
        // Dialog bleibt offen; nur Titel/Summe/Kommentar zurücksetzen
        setForm((prev) => ({ ...prev, title: "", amount: "", comment: "" }));
        ok("Gespeichert – bereit für die nächste Rechnung");
      } else {
        setOpen(false);
        ok("Gespeichert");
      }
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };

  const testIds = testPropertyIds(props.list.data ?? []);
  const filtered = (list.data ?? []).filter(
    (inv) =>
      (!propertyFilter || inv.property_id === Number(propertyFilter)) &&
      (!yearFilter || (inv.period_start?.slice(0, 4) ?? "") === yearFilter) &&
      (!hideTest || !testIds.has(inv.property_id)),
  );

  const canSave =
    form.property_id !== "" &&
    form.year !== "" &&
    form.cost_category_id !== "" &&
    form.title.trim() !== "" &&
    form.amount !== "" &&
    Number(form.amount) > 0 &&
    (!isWohnung || form.lease_unit_id !== "");

  const invoiceSum = (inv: Invoice): string =>
    inv.items.length
      ? String(inv.items.reduce((s, i) => s + Number(i.gross_amount), 0))
      : inv.gross_amount != null
        ? String(inv.gross_amount)
        : inv.annual_amount != null
          ? String(inv.annual_amount)
          : "";

  const invoiceComment = (inv: Invoice): string =>
    inv.meta && "kommentar" in inv.meta
      ? String((inv.meta as Record<string, unknown>).kommentar)
      : "";

  // Übersicht gruppieren: Objekt → Jahr
  type YearGroup = { year: string; invoices: Invoice[]; sum: number };
  type PropGroup = { propertyId: number; count: number; sum: number; years: YearGroup[] };
  const propGroups: PropGroup[] = (() => {
    const byProp = new Map<number, Map<string, Invoice[]>>();
    for (const inv of filtered) {
      const year = inv.period_start?.slice(0, 4) ?? "—";
      if (!byProp.has(inv.property_id)) byProp.set(inv.property_id, new Map());
      const ym = byProp.get(inv.property_id)!;
      if (!ym.has(year)) ym.set(year, []);
      ym.get(year)!.push(inv);
    }
    const groups: PropGroup[] = [];
    for (const [pid, ym] of byProp) {
      const years: YearGroup[] = [...ym.entries()]
        .map(([year, invoices]) => ({
          year,
          invoices,
          sum: invoices.reduce((s, i) => s + Number(invoiceSum(i) || "0"), 0),
        }))
        .sort((a, b) => (a.year < b.year ? 1 : -1)); // neueste zuerst
      groups.push({
        propertyId: pid,
        count: years.reduce((s, y) => s + y.invoices.length, 0),
        sum: years.reduce((s, y) => s + y.sum, 0),
        years,
      });
    }
    return groups.sort((a, b) =>
      propName(a.propertyId).localeCompare(propName(b.propertyId), "de"),
    );
  })();

  return (
    <Stack>
      <Group>
        <Title order={2}>Rechnungen</Title>
        <PageHelp content={rechnungenHelp} />
      </Group>
      <Group>
        <Select
          label="Objekt"
          placeholder="Alle Objekte"
          clearable
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyFilter}
          onChange={setPropertyFilter}
          w={280}
        />
        <Select
          label="Jahr"
          placeholder="Alle Jahre"
          clearable
          data={YEARS.map((y) => ({ value: y, label: y }))}
          value={yearFilter}
          onChange={setYearFilter}
          w={140}
        />
        <Button onClick={openCreate} mt="auto">
          Neue Rechnung
        </Button>
      </Group>

      <Accordion multiple defaultValue={propGroups.map((g) => String(g.propertyId))}>
        {propGroups.map((g) => (
          <Accordion.Item key={g.propertyId} value={String(g.propertyId)}>
            <Accordion.Control>
              {propName(g.propertyId)} – {g.count} Rechnungen · {fmt(g.sum)} €
            </Accordion.Control>
            <Accordion.Panel>
              <Accordion multiple defaultValue={g.years.map((y) => y.year)}>
                {g.years.map((y) => (
                  <Accordion.Item key={y.year} value={y.year}>
                    <Accordion.Control>
                      {y.year} – {y.invoices.length} Rechnungen · {fmt(y.sum)} €
                    </Accordion.Control>
                    <Accordion.Panel>
                      <Table striped highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Kostenstelle</Table.Th>
                            <Table.Th>Wohnung</Table.Th>
                            <Table.Th>Titel</Table.Th>
                            <Table.Th>Summe</Table.Th>
                            <Table.Th>Kommentar</Table.Th>
                            <Table.Th></Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {y.invoices.map((inv) => (
                            <Table.Tr key={inv.id}>
                              <Table.Td>{catName(inv.cost_category_id)}</Table.Td>
                              <Table.Td>
                                {inv.lease_unit_id != null ? unitName(inv.lease_unit_id) : "—"}
                              </Table.Td>
                              <Table.Td>{inv.description ?? "—"}</Table.Td>
                              <Table.Td>
                                {invoiceSum(inv) !== ""
                                  ? `${Number(invoiceSum(inv)).toLocaleString("de-DE", { maximumFractionDigits: 2 })} €`
                                  : "—"}
                              </Table.Td>
                              <Table.Td>
                                {invoiceComment(inv) ? (
                                  <Tooltip label={invoiceComment(inv)} multiline withArrow>
                                    <Text lineClamp={1} maw={220}>
                                      {invoiceComment(inv)}
                                    </Text>
                                  </Tooltip>
                                ) : (
                                  "—"
                                )}
                              </Table.Td>
                              <Table.Td>
                                <Group gap="xs" justify="flex-end">
                                  <Button size="compact-xs" variant="light" onClick={() => openClone(inv)}>
                                    Klonen
                                  </Button>
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
                    </Accordion.Panel>
                  </Accordion.Item>
                ))}
              </Accordion>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Rechnung ändern" : "Neue Rechnung"} size="lg">
        <Stack>
          <Group grow>
            <Select
              label="Objekt"
              data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
              value={form.property_id || null}
              onChange={(v) =>
                setForm((prev) => ({ ...prev, property_id: v ?? "", cost_category_id: "", lease_unit_id: "" }))
              }
            />
            <Select
              label="Jahr"
              data={YEARS.map((y) => ({ value: y, label: y }))}
              value={form.year || null}
              onChange={(v) =>
                setForm((prev) => ({
                  ...prev,
                  year: v ?? String(DEFAULT_YEAR),
                  cost_category_id: "",
                  lease_unit_id: "",
                }))
              }
            />
          </Group>

          <Group grow>
            <Select
              label="Rechnungstyp"
              data={[{ value: "RECHNUNG", label: "Rechnung" }]}
              value="RECHNUNG"
              onChange={() => {}}
            />
            <Select
              label="Kostenstelle"
              placeholder="Kostenstelle wählen"
              data={propConfigs.map((c) => ({
                value: String(c.cost_category_id),
                label: catName(c.cost_category_id) || `Kostenart ${c.cost_category_id}`,
              }))}
              value={form.cost_category_id || null}
              onChange={(v) =>
                setForm((prev) => ({ ...prev, cost_category_id: v ?? "", lease_unit_id: "" }))
              }
            />
          </Group>

          {isWohnung && (
            <Select
              label="Wohnung (je Wohnung)"
              placeholder="Wohnung wählen"
              data={(units.list.data ?? [])
                .filter((u) => u.property_id === Number(form.property_id))
                .map((u) => ({ value: String(u.id), label: u.designation }))}
              value={form.lease_unit_id || null}
              onChange={(v) => setForm({ ...form, lease_unit_id: v ?? "" })}
            />
          )}

          <Group grow>
            <TextInput
              label="Titel"
              placeholder="z. B. Grundsteuer 2025"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.currentTarget.value })}
            />
            <NumberInput
              label="Summe (€)"
              placeholder="0,00"
              value={form.amount}
              onChange={(v) => setForm({ ...form, amount: String(v ?? "") })}
              decimalScale={2}
              min={0}
            />
          </Group>
          <TextInput
            label="Kommentar (optional)"
            placeholder="z. B. Rechnungsnummer, Erläuterung"
            value={form.comment}
            onChange={(e) => setForm({ ...form, comment: e.currentTarget.value })}
          />

          <Text size="sm" c="dimmed">
            Alle Rechnungen dieser Kostenstelle im Jahr {form.year} werden zusammengerechnet und
            nach Umlageschlüssel {KEY_LABELS[selConfig?.allocation_key ?? ""] ?? "–"} auf die Mieter
            verteilt.
          </Text>

          <Group justify="flex-end" gap="md">
            <Checkbox
              label="Dialog offen lassen (weitere Rechnung)"
              checked={keepOpen}
              onChange={(e) => setKeepOpen(e.currentTarget.checked)}
              disabled={!!edit}
            />
            <Button onClick={save} disabled={!canSave}>
              Speichern
            </Button>
          </Group>
        </Stack>
      </Modal>

      <ConfirmDeleteModal
        opened={!!del}
        message={`Rechnung (${del?.description ?? del?.period_start}) wird dauerhaft gelöscht.`}
        confirmText={del?.description || "LÖSCHEN"}
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) remove.mutate(del.id);
          setDel(null);
        }}
      />
    </Stack>
  );
}
