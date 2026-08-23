import { useState } from "react";
import {
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
import { fmt } from "../api/client";
import { useCrud } from "../hooks/useCrud";
import type { Property, TechemRecord } from "../api/types";

const KINDS = [
  { value: "GAS", label: "Gas" },
  { value: "HEATING_ELECTRICITY", label: "Heizstrom" },
];

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

export default function TechemPage() {
  const { list, create, update, remove } = useCrud<TechemRecord>("/techem", "techem");
  const props = useCrud<Property>("/properties", "properties");
  const [propertyFilter, setPropertyFilter] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<TechemRecord | null>(null);
  const [form, setForm] = useState({
    property_id: "",
    kind: "GAS",
    invoice_date: "",
    quantity_kwh: "",
    gross_amount: "",
    notes: "",
  });

  const openCreate = () => {
    setEdit(null);
    setForm({
      property_id: propertyFilter ?? "",
      kind: "GAS",
      invoice_date: "",
      quantity_kwh: "",
      gross_amount: "",
      notes: "",
    });
    setOpen(true);
  };
  const openEdit = (r: TechemRecord) => {
    setEdit(r);
    setForm({
      property_id: String(r.property_id),
      kind: r.kind,
      invoice_date: r.invoice_date,
      quantity_kwh: r.quantity_kwh != null ? String(r.quantity_kwh) : "",
      gross_amount: String(r.gross_amount),
      notes: r.notes ?? "",
    });
    setOpen(true);
  };
  const save = () => {
    const payload = {
      property_id: Number(form.property_id),
      kind: form.kind,
      invoice_date: form.invoice_date,
      quantity_kwh: form.quantity_kwh === "" ? null : form.quantity_kwh,
      gross_amount: form.gross_amount || "0",
      notes: form.notes || null,
    };
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };

  const propName = (id: number) => props.list.data?.find((p) => p.id === id)?.name ?? "";
  const filtered = (list.data ?? []).filter(
    (r) => !propertyFilter || r.property_id === Number(propertyFilter),
  );

  const exportCsv = () => {
    const header = "Objekt;Art;Rechnungsdatum;Menge (kWh);Brutto (EUR);Notizen";
    const rows = filtered.map((r) =>
      [
        propName(r.property_id),
        r.kind,
        r.invoice_date,
        r.quantity_kwh ?? "",
        String(r.gross_amount),
        (r.notes ?? "").replace(/;/g, ","),
      ].join(";"),
    );
    const csv = "\uFEFF" + [header, ...rows].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "techem.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack>
      <Title order={2}>Techem-Datenaufbereitung (Heizkosten)</Title>
      <Text size="sm" c="dimmed">
        Nur für das Objekt 2 – fließt nicht in die Mieter-Abrechnung ein. Heizjahr: 01.07.–30.06.
      </Text>
      <Group>
        <Select
          label="Objekt filter"
          placeholder="Objekt"
          clearable
          data={(props.list.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyFilter}
          onChange={setPropertyFilter}
          w={280}
        />
        <Button onClick={openCreate} mt="auto">
          Neuer Eintrag
        </Button>
        <Button variant="outline" mt="auto" onClick={exportCsv} disabled={filtered.length === 0}>
          CSV-Export
        </Button>
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Objekt</Table.Th>
            <Table.Th>Art</Table.Th>
            <Table.Th>Rechnungsdatum</Table.Th>
            <Table.Th>Menge (kWh)</Table.Th>
            <Table.Th>Brutto (€)</Table.Th>
            <Table.Th>Notizen</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {filtered.map((r) => (
            <Table.Tr key={r.id}>
              <Table.Td>{propName(r.property_id)}</Table.Td>
              <Table.Td>{r.kind === "GAS" ? "Gas" : "Heizstrom"}</Table.Td>
              <Table.Td>{r.invoice_date}</Table.Td>
              <Table.Td>{r.quantity_kwh != null ? fmt(r.quantity_kwh, 0) : "—"}</Table.Td>
              <Table.Td>{fmt(r.gross_amount, 2)}</Table.Td>
              <Table.Td>{r.notes ?? "—"}</Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(r)}>
                    Ändern
                  </Button>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => remove.mutate(r.id)}>
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Eintrag ändern" : "Neuer Eintrag"}>
        <Stack>
          <Select
            label="Objekt"
            data={(props.list.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
            value={form.property_id || null}
            onChange={(v) => setForm({ ...form, property_id: v ?? "" })}
          />
          <Select
            label="Art"
            data={KINDS}
            value={form.kind}
            onChange={(v) => setForm({ ...form, kind: v ?? "GAS" })}
          />
          <TextInput
            type="date"
            label="Rechnungsdatum"
            value={form.invoice_date}
            onChange={(e) => setForm({ ...form, invoice_date: e.currentTarget.value })}
          />
          <NumberInput
            label="Menge (kWh)"
            value={form.quantity_kwh}
            onChange={(v) => setForm({ ...form, quantity_kwh: String(v ?? "") })}
            decimalScale={0}
          />
          <NumberInput
            label="Brutto (€)"
            value={form.gross_amount}
            onChange={(v) => setForm({ ...form, gross_amount: String(v ?? "") })}
            decimalScale={2}
          />
          <TextInput
            label="Notizen"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
          />
          <Button onClick={save}>Speichern</Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
