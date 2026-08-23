import { useState } from "react";
import {
  Badge,
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
import { api, fmt } from "../api/client";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import { useTestData } from "../context/TestDataContext";
import { useCrud } from "../hooks/useCrud";
import { testPropertyIds, visibleProperties, visibleUnits } from "../utils/testData";
import type { LeaseUnit, Meter, MeterReading, Property } from "../api/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const METER_TYPES = [
  { value: "APARTMENT_WATER", label: "Wohnungs-Wasserzähler" },
  { value: "WASHING_MACHINE", label: "Waschmaschine" },
  { value: "GARDEN", label: "Gartenwasser" },
  { value: "HEATING_ELECTRICITY", label: "Heizstrom" },
  { value: "GAS", label: "Gas" },
  { value: "ELECTRICITY", label: "Strom" },
  { value: "OTHER", label: "Sonstiger" },
];

const UNITS = [
  { value: "m3", label: "m³" },
  { value: "kWh", label: "kWh" },
];

const TYPE_LABEL = Object.fromEntries(METER_TYPES.map((t) => [t.value, t.label]));

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

export default function MetersPage() {
  const { list, create, update, remove } = useCrud<Meter>("/meters", "meters");
  const props = useCrud<Property>("/properties", "properties");
  const units = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const { hideTest } = useTestData();
  const [propertyFilter, setPropertyFilter] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Meter | null>(null);
  const [del, setDel] = useState<Meter | null>(null);
  const [form, setForm] = useState({
    property_id: "",
    lease_unit_id: "",
    name: "",
    meter_type: "OTHER",
    unit: "m3",
  });

  const openCreate = () => {
    setEdit(null);
    setForm({ property_id: propertyFilter ?? "", lease_unit_id: "", name: "", meter_type: "OTHER", unit: "m3" });
    setOpen(true);
  };
  const openEdit = (m: Meter) => {
    setEdit(m);
    setForm({
      property_id: m.property_id != null ? String(m.property_id) : "",
      lease_unit_id: m.lease_unit_id != null ? String(m.lease_unit_id) : "",
      name: m.name,
      meter_type: m.meter_type,
      unit: m.unit,
    });
    setOpen(true);
  };
  const save = () => {
    const payload = {
      property_id: form.property_id ? Number(form.property_id) : null,
      lease_unit_id: form.lease_unit_id ? Number(form.lease_unit_id) : null,
      name: form.name,
      meter_type: form.meter_type,
      unit: form.unit,
    };
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };

  const propName = (id: number | null) => (id != null ? props.list.data?.find((p) => p.id === id)?.name ?? "" : "—");
  const unitName = (id: number | null) => (id != null ? units.list.data?.find((u) => u.id === id)?.designation ?? "" : "—");

  const testIds = testPropertyIds(props.list.data ?? []);
  const isTestMeter = (m: Meter) => {
    if (m.property_id != null && testIds.has(m.property_id)) return true;
    if (m.lease_unit_id != null) {
      const unitProp = units.list.data?.find((u) => u.id === m.lease_unit_id)?.property_id;
      if (unitProp != null && testIds.has(unitProp)) return true;
    }
    return false;
  };
  const filtered = (list.data ?? []).filter(
    (m) =>
      !(hideTest && isTestMeter(m)) &&
      (!propertyFilter ||
        m.property_id === Number(propertyFilter) ||
        (propertyFilter && m.lease_unit_id && units.list.data?.find((u) => u.id === m.lease_unit_id)?.property_id === Number(propertyFilter))),
  );

  return (
    <Stack>
      <Title order={2}>Zähler & Zählerstände</Title>
      <Group>
        <Select
          label="Objekt filter"
          placeholder="Alle"
          clearable
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyFilter}
          onChange={setPropertyFilter}
          w={280}
        />
        <Button onClick={openCreate} mt="auto">
          Neuer Zähler
        </Button>
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Typ</Table.Th>
            <Table.Th>Einheit</Table.Th>
            <Table.Th>Objekt</Table.Th>
            <Table.Th>Mieteinheit</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {filtered.map((m) => (
            <Table.Tr key={m.id}>
              <Table.Td>{m.name}</Table.Td>
              <Table.Td>
                <Badge variant="light">{TYPE_LABEL[m.meter_type] ?? m.meter_type}</Badge>
              </Table.Td>
              <Table.Td>{m.unit}</Table.Td>
              <Table.Td>{propName(m.property_id)}</Table.Td>
              <Table.Td>{unitName(m.lease_unit_id)}</Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(m)}>
                    Ändern
                  </Button>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => setDel(m)}>
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <ReadingsSection meters={filtered} />

      <ConfirmDeleteModal
        opened={!!del}
        message={`Zähler „${del?.name}“ samt aller Zählerstände wird dauerhaft gelöscht.`}
        confirmText={del?.name ?? ""}
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) remove.mutate(del.id);
          setDel(null);
        }}
      />

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Zähler ändern" : "Neuer Zähler"}>
        <Stack>
          <TextInput
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Select
            label="Typ"
            data={METER_TYPES}
            value={form.meter_type}
            onChange={(v) => setForm({ ...form, meter_type: v ?? "OTHER" })}
          />
          <Select
            label="Einheit"
            data={UNITS}
            value={form.unit}
            onChange={(v) => setForm({ ...form, unit: v ?? "m3" })}
          />
          <Select
            label="Objekt (für gemeinsame Zähler)"
            placeholder="—"
            clearable
            data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
            value={form.property_id || null}
            onChange={(v) => setForm({ ...form, property_id: v ?? "" })}
          />
          <Select
            label="Mieteinheit (für Wohnungs-/WM-Zähler)"
            placeholder="—"
            clearable
            data={visibleUnits(units.list.data ?? [], testIds).map((u) => ({ value: String(u.id), label: u.designation }))}
            value={form.lease_unit_id || null}
            onChange={(v) => setForm({ ...form, lease_unit_id: v ?? "" })}
          />
          <Button onClick={save}>Speichern</Button>
        </Stack>
      </Modal>
    </Stack>
  );
}

function ReadingsSection({ meters }: { meters: Meter[] }) {
  const qc = useQueryClient();
  const [meterId, setMeterId] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [value, setValue] = useState("");
  const [delReading, setDelReading] = useState<MeterReading | null>(null);

  const readings = useQuery({
    queryKey: ["meter-readings", meterId],
    enabled: !!meterId,
    queryFn: async () =>
      (await api.get<MeterReading[]>("/meter-readings", { params: { meter_id: Number(meterId) } })).data,
  });

  const createReading = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/meter-readings", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meter-readings"] });
      setDate("");
      setValue("");
      ok("Gespeichert");
    },
    onError: err,
  });
  const deleteReading = useMutation({
    mutationFn: (id: number) => api.delete(`/meter-readings/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["meter-readings"] }),
  });

  const selected = meters.find((m) => String(m.id) === meterId);

  return (
    <Stack mt="md">
      <Title order={4}>Zählerstände</Title>
      <Group>
        <Select
          label="Zähler"
          placeholder="Zähler wählen"
          data={meters.map((m) => ({ value: String(m.id), label: m.name }))}
          value={meterId}
          onChange={setMeterId}
          w={320}
        />
        {selected && (
          <>
            <TextInput type="date" label="Datum" value={date} onChange={(e) => setDate(e.currentTarget.value)} />
            <NumberInput
              label={`Wert (${selected.unit})`}
              value={value}
              onChange={(v) => setValue(String(v ?? ""))}
              decimalScale={4}
            />
            <Button
              mt="auto"
              disabled={!date || value === ""}
              onClick={() => createReading.mutate({ meter_id: Number(meterId), reading_date: date, value })}
            >
              Hinzufügen
            </Button>
          </>
        )}
      </Group>

      {meterId && (
        <Table striped highlightOnHover maw={520}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Datum</Table.Th>
              <Table.Th>Wert</Table.Th>
              <Table.Th></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(readings.data ?? []).map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.reading_date}</Table.Td>
                <Table.Td>{fmt(r.value, 4)}</Table.Td>
                <Table.Td>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => setDelReading(r)}>
                    Löschen
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <ConfirmDeleteModal
        opened={!!delReading}
        title="Zählerstand löschen?"
        message={`Zählerstand vom ${delReading?.reading_date} wird dauerhaft gelöscht.`}
        confirmText="LÖSCHEN"
        onClose={() => setDelReading(null)}
        onConfirm={() => {
          if (delReading) deleteReading.mutate(delReading.id);
          setDelReading(null);
        }}
      />
    </Stack>
  );
}
