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
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import { useTestData } from "../context/TestDataContext";
import { useCrud } from "../hooks/useCrud";
import { testPropertyIds, visibleProperties } from "../utils/testData";
import type { CostCategory, Invoice, InvoiceItem, Property } from "../api/types";

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

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

export default function InvoicesPage() {
  const { list, create, update, remove } = useCrud<Invoice>("/invoices", "invoices");
  const props = useCrud<Property>("/properties", "properties");
  const cats = useCrud<CostCategory>("/cost-categories", "cost-categories");
  const { hideTest } = useTestData();
  const [propertyFilter, setPropertyFilter] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Invoice | null>(null);
  const [del, setDel] = useState<Invoice | null>(null);
  const [form, setForm] = useState({
    property_id: "",
    cost_category_id: "",
    invoice_number: "",
    supplier: "",
    description: "",
    issue_date: "",
    period_start: "",
    period_end: "",
  });
  const [items, setItems] = useState<ItemDraft[]>([{ ...EMPTY_ITEM }]);

  const catName = (id: number) => cats.list.data?.find((c) => c.id === id)?.name ?? "";
  const propName = (id: number) => props.list.data?.find((p) => p.id === id)?.name ?? "";

  const openCreate = () => {
    setEdit(null);
    setForm({
      property_id: propertyFilter ?? "",
      cost_category_id: "",
      invoice_number: "",
      supplier: "",
      description: "",
      issue_date: "",
      period_start: "",
      period_end: "",
    });
    setItems([{ ...EMPTY_ITEM }]);
    setOpen(true);
  };

  const openEdit = (inv: Invoice) => {
    setEdit(inv);
    setForm({
      property_id: String(inv.property_id),
      cost_category_id: String(inv.cost_category_id),
      invoice_number: inv.invoice_number ?? "",
      supplier: inv.supplier ?? "",
      description: inv.description ?? "",
      issue_date: inv.issue_date ?? "",
      period_start: inv.period_start,
      period_end: inv.period_end,
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
    setOpen(true);
  };

  const setItem = (idx: number, patch: Partial<ItemDraft>) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  };

  const toPayload = () => {
    const itemPayload: InvoiceItem[] = items.map((it) => ({
      from_date: it.from_date,
      to_date: it.to_date,
      description: it.description || null,
      quantity: it.quantity === "" ? null : it.quantity,
      unit: it.unit || null,
      unit_price: it.unit_price === "" ? null : it.unit_price,
      gross_amount: it.gross_amount || "0",
    }));
    const base = {
      property_id: Number(form.property_id),
      cost_category_id: Number(form.cost_category_id),
      invoice_number: form.invoice_number || null,
      supplier: form.supplier || null,
      description: form.description || null,
      issue_date: form.issue_date || null,
      period_start: form.period_start,
      period_end: form.period_end,
    };
    return { ...base, items: itemPayload };
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
              <Table.Td>{catName(inv.cost_category_id)}</Table.Td>
              <Table.Td>
                {inv.period_start} – {inv.period_end}
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
              onChange={(v) => setForm({ ...form, property_id: v ?? "" })}
            />
            <Select
              label="Kostenart"
              data={(cats.list.data ?? [])
                .filter((c) => c.property_id === Number(form.property_id))
                .map((c) => ({ value: String(c.id), label: c.name }))}
              value={form.cost_category_id || null}
              onChange={(v) => setForm({ ...form, cost_category_id: v ?? "" })}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Rechnungsnummer"
              value={form.invoice_number}
              onChange={(e) => setForm({ ...form, invoice_number: e.currentTarget.value })}
            />
            <TextInput
              label="Lieferant"
              value={form.supplier}
              onChange={(e) => setForm({ ...form, supplier: e.currentTarget.value })}
            />
          </Group>
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

          <Group justify="flex-end">
            <Button onClick={save}>Speichern</Button>
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
