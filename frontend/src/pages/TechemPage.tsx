import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Group,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQuery } from "@tanstack/react-query";
import { api, fmt } from "../api/client";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import PageHelp from "../components/PageHelp";
import { techemHelp } from "../help/helpContent";
import { useTestData } from "../context/TestDataContext";
import { useObject } from "../context/ObjectContext";
import { useCrud } from "../hooks/useCrud";
import { visibleProperties } from "../utils/testData";
import type { Property, TechemSheet } from "../api/types";

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

// Standard-Heizperiode: 01.07. – 30.06. des Folgejahres (aktuell laufende Periode)
const defaultPeriod = () => {
  const now = new Date();
  const y = now.getFullYear();
  if (now.getMonth() + 1 >= 7) return { von: `${y}-07-01`, bis: `${y + 1}-06-30` };
  return { von: `${y - 1}-07-01`, bis: `${y}-06-30` };
};

export default function TechemPage() {
  const props = useCrud<Property>("/properties", "properties");
  const { hideTest } = useTestData();
  const { propertyFilter, setPropertyFilter } = useObject();
  const propertyId = propertyFilter ? Number(propertyFilter) : null;

  const [period, setPeriod] = useState(defaultPeriod());
  const [del, setDel] = useState<TechemSheet | null>(null);
  const [form, setForm] = useState({
    gas_kwh: "",
    gas_cost: "",
    maintenance_cost: "",
    chimney_cost: "",
    notes: "",
  });

  const sheets = useQuery({
    queryKey: ["techem-sheets", propertyId],
    enabled: propertyId != null,
    queryFn: async () =>
      (await api.get<TechemSheet[]>("/techem", { params: { property_id: propertyId } })).data,
  });

  const sheet = useQuery({
    queryKey: ["techem-sheet", propertyId, period.von, period.bis],
    enabled: propertyId != null && !!period.von && !!period.bis,
    queryFn: async () =>
      (
        await api.get<TechemSheet>("/techem/sheet", {
          params: { property_id: propertyId, von: period.von, bis: period.bis },
        })
      ).data,
  });

  // Gespeicherte Werte des Zeitraums in das Formular übernehmen
  useEffect(() => {
    const s = sheet.data;
    if (s) {
      setForm({
        gas_kwh: s.gas_kwh ? String(s.gas_kwh) : "",
        gas_cost: s.gas_cost ? String(s.gas_cost) : "",
        maintenance_cost: s.maintenance_cost ? String(s.maintenance_cost) : "",
        chimney_cost: s.chimney_cost ? String(s.chimney_cost) : "",
        notes: s.notes ?? "",
      });
    }
  }, [sheet.data]);

  const save = async () => {
    if (!propertyId) return;
    try {
      await api.put("/techem/sheet", {
        property_id: propertyId,
        von: period.von,
        bis: period.bis,
        gas_kwh: Number(form.gas_kwh || 0),
        gas_cost: Number(form.gas_cost || 0),
        maintenance_cost: Number(form.maintenance_cost || 0),
        chimney_cost: Number(form.chimney_cost || 0),
        notes: form.notes || null,
      });
      await Promise.all([sheets.refetch(), sheet.refetch()]);
      ok("Heizkosten-Blatt gespeichert");
    } catch {
      err();
    }
  };

  const loadSheet = (s: TechemSheet) => setPeriod({ von: s.von, bis: s.bis });

  const removeSheet = async () => {
    if (!del?.id) return;
    try {
      await api.delete(`/techem/${del.id}`);
      const deleted = del;
      setDel(null);
      await sheets.refetch();
      // Falls der gelöschte Zeitraum gerade bearbeitet wird, Formular zurücksetzen
      if (deleted.von === period.von && deleted.bis === period.bis) {
        setForm({ gas_kwh: "", gas_cost: "", maintenance_cost: "", chimney_cost: "", notes: "" });
      }
      ok("Heizkosten-Blatt gelöscht");
    } catch {
      err();
    }
  };

  const canSave = propertyId != null && !!period.von && !!period.bis;

  return (
    <Stack>
      <Group>
        <Title order={2}>Techem – Heizkosten-Datenaufbereitung</Title>
        <PageHelp content={techemHelp} />
      </Group>
      <Text size="sm" c="dimmed">
        Je Objekt und Heizperiode (Standard 01.07.–30.06. des Folgejahres). Fließt nicht in die
        Mieter-Abrechnung ein.
      </Text>

      <Group>
        <Select
          label="Objekt"
          placeholder="Objekt wählen"
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyFilter ?? ""}
          onChange={setPropertyFilter}
          w={280}
        />
        <TextInput
          type="date"
          label="Zeitraum von"
          value={period.von}
          onChange={(e) => setPeriod({ ...period, von: e.currentTarget.value })}
        />
        <TextInput
          type="date"
          label="Zeitraum bis"
          value={period.bis}
          onChange={(e) => setPeriod({ ...period, bis: e.currentTarget.value })}
        />
      </Group>

      {propertyId != null && (
        <Card withBorder p="md">
          <Title order={4} mb="xs">
            Heizkosten-Blatt {period.von} – {period.bis}
          </Title>

          <Table striped highlightOnHover mb="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={80}>Einheit</Table.Th>
                <Table.Th>Heizstrom (Unterzähler)</Table.Th>
                <Table.Th>Gas</Table.Th>
                <Table.Th>Wartung Heizung</Table.Th>
                <Table.Th>Kaminfeger</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td fw={700}>kWh</Table.Td>
                <Table.Td>
                  <Text size="xl" fw={700}>
                    {sheet.data ? `${fmt(Number(sheet.data.strom_kwh), 0)}` : "—"}
                  </Text>
                  <Text size="xs" c="dimmed">
                    automatisch aus dem Unterzähler
                  </Text>
                </Table.Td>
                <Table.Td>
                  <NumberInput
                    aria-label="Gasverbrauch (kWh)"
                    placeholder="kWh"
                    value={form.gas_kwh}
                    onChange={(v) => setForm({ ...form, gas_kwh: String(v ?? "") })}
                    decimalScale={0}
                  />
                </Table.Td>
                <Table.Td></Table.Td>
                <Table.Td></Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={700}>€</Table.Td>
                <Table.Td>
                  <Text size="lg" fw={600}>
                    {sheet.data ? `${fmt(Number(sheet.data.strom_brutto), 2)} brutto` : "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <NumberInput
                    aria-label="Gaskosten (€ brutto)"
                    placeholder="€"
                    value={Number(form.gas_cost || 0)}
                    onChange={(v) => setForm({ ...form, gas_cost: String(v ?? "") })}
                    decimalScale={2}
                    fixedDecimalScale
                  />
                </Table.Td>
                <Table.Td>
                  <NumberInput
                    aria-label="Wartung Heizung (€)"
                    placeholder="€"
                    value={Number(form.maintenance_cost || 0)}
                    onChange={(v) => setForm({ ...form, maintenance_cost: String(v ?? "") })}
                    decimalScale={2}
                    fixedDecimalScale
                  />
                </Table.Td>
                <Table.Td>
                  <NumberInput
                    aria-label="Kaminfeger (€)"
                    placeholder="€"
                    value={Number(form.chimney_cost || 0)}
                    onChange={(v) => setForm({ ...form, chimney_cost: String(v ?? "") })}
                    decimalScale={2}
                    fixedDecimalScale
                  />
                </Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>

          <TextInput
            label="Notizen"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
            mb="sm"
          />

          <Group mt="xs">
            <Button onClick={save} disabled={!canSave}>
              Speichern
            </Button>
          </Group>
        </Card>
      )}

      <Title order={4}>Gespeicherte Zeiträume</Title>
      <Table.ScrollContainer minWidth={700}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Zeitraum</Table.Th>
              <Table.Th>Heizstrom (kWh)</Table.Th>
              <Table.Th>Heizstrom (€)</Table.Th>
              <Table.Th>Gas (kWh)</Table.Th>
              <Table.Th>Gas (€)</Table.Th>
              <Table.Th>Wartung (€)</Table.Th>
              <Table.Th>Kaminfeger (€)</Table.Th>
              <Table.Th>Notizen</Table.Th>
              <Table.Th></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(sheets.data ?? []).map((s) => (
              <Table.Tr key={`${s.von}-${s.bis}`}>
                <Table.Td>
                  {s.von} – {s.bis}
                </Table.Td>
                <Table.Td>{fmt(Number(s.strom_kwh), 0)}</Table.Td>
                <Table.Td>{fmt(Number(s.strom_brutto), 2)} €</Table.Td>
                <Table.Td>{fmt(Number(s.gas_kwh), 0)}</Table.Td>
                <Table.Td>{fmt(Number(s.gas_cost), 2)} €</Table.Td>
                <Table.Td>{fmt(Number(s.maintenance_cost), 2)} €</Table.Td>
                <Table.Td>{fmt(Number(s.chimney_cost), 2)} €</Table.Td>
                <Table.Td>{s.notes ?? "—"}</Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <Button size="compact-xs" variant="light" onClick={() => loadSheet(s)}>
                      Laden
                    </Button>
                    <Button size="compact-xs" variant="light" color="red" onClick={() => setDel(s)}>
                      Löschen
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {(sheets.data ?? []).length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={9}>
                  <Text size="sm" c="dimmed">
                    Noch keine Zeiträume gespeichert.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      <ConfirmDeleteModal
        opened={!!del}
        message={`Heizkosten-Blatt (${del?.von} – ${del?.bis}) wird dauerhaft gelöscht.`}
        confirmText="LÖSCHEN"
        onClose={() => setDel(null)}
        onConfirm={removeSheet}
      />
    </Stack>
  );
}
