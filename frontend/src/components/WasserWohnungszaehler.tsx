import { useState } from "react";
import {
  Accordion,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  NumberInput,
  SegmentedControl,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCrud } from "../hooks/useCrud";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";
import ZaehlerwechselFields from "./ZaehlerwechselFields";
import ReadingSource, { READING_SOURCE_OPTIONS } from "./ReadingSource";
import type { LeaseUnit, Meter, MeterReading } from "../api/types";

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

const fmt = (v: number | undefined | null, digits = 2) =>
  v == null ? "—" : v.toLocaleString("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });

const ZAEHLER_TYPEN = [
  { value: "APARTMENT_WATER", label: "Wohnung" },
  { value: "WASHING_MACHINE", label: "Waschmaschine" },
];

export default function WasserWohnungszaehler({
  propertyId,
  waschAktiv,
  onToggleWasch,
}: {
  propertyId: number;
  waschAktiv: boolean;
  onToggleWasch: (v: boolean) => void;
}) {
  const units = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const meters = useCrud<Meter>("/meters", "meters");
  const readings = useCrud<MeterReading>("/meter-readings", "meter-readings");

  // Nur Mieteinheiten mit Wohnfläche > 0 (z. B. keine Garagen/Extrazimmer), nach Name sortiert
  const propUnits = (units.list.data ?? [])
    .filter((u) => u.property_id === propertyId && Number(u.living_area) > 0)
    .sort((a, b) => a.designation.localeCompare(b.designation, "de"));
  const unitIds = new Set(propUnits.map((u) => u.id));
  const propMeters = (meters.list.data ?? []).filter(
    (m) => m.lease_unit_id != null && unitIds.has(m.lease_unit_id),
  );
  const propReadings = (readings.list.data ?? []).filter((r) =>
    propMeters.some((m) => m.id === r.meter_id),
  );

  const [readOpen, setReadOpen] = useState(false);
  const [readEdit, setReadEdit] = useState<MeterReading | null>(null);
  const [readForm, setReadForm] = useState({
    meter_id: 0,
    reading_date: "",
    value: "",
    vor_zaehlerwechsel: false,
    neuer_zaehler_start: "",
    source: "RECHNUNG",
  });
  const [readDel, setReadDel] = useState<MeterReading | null>(null);

  const openReadNew = (meter: Meter) => {
    setReadEdit(null);
    const sorted = propReadings
      .filter((r) => r.meter_id === meter.id)
      .sort((a, b) => a.reading_date.localeCompare(b.reading_date));
    const last = sorted[sorted.length - 1];
    setReadForm({
      meter_id: meter.id,
      // fortlaufend: Datum leer (User wählt), Wert mit letztem Stand vorbelegt
      reading_date: last ? "" : "2025-01-01",
      value: last ? String(Number(last.value)) : "",
      vor_zaehlerwechsel: false,
      neuer_zaehler_start: "",
      source: "RECHNUNG",
    });
    setReadOpen(true);
  };
  const openReadEdit = (r: MeterReading) => {
    setReadEdit(r);
    setReadForm({
      meter_id: r.meter_id,
      reading_date: r.reading_date,
      value: String(Number(r.value)),
      vor_zaehlerwechsel: Boolean(r.vor_zaehlerwechsel),
      neuer_zaehler_start: r.neuer_zaehler_start != null ? String(Number(r.neuer_zaehler_start)) : "",
      source: r.source ?? "RECHNUNG",
    });
    setReadOpen(true);
  };
  const saveReading = () => {
    const payload = {
      meter_id: readForm.meter_id,
      reading_date: readForm.reading_date,
      value: Number(readForm.value),
      vor_zaehlerwechsel: readForm.vor_zaehlerwechsel,
      neuer_zaehler_start: readForm.vor_zaehlerwechsel
        ? Number(readForm.neuer_zaehler_start === "" ? "0" : readForm.neuer_zaehler_start)
        : 0,
      source: readForm.source,
    };
    const done = () => {
      setReadOpen(false);
      ok("Gespeichert");
    };
    if (readEdit) readings.update.mutate({ id: readEdit.id, data: payload }, { onSuccess: done, onError: err });
    else readings.create.mutate(payload, { onSuccess: done, onError: err });
  };
  const canSaveReading = readForm.reading_date !== "" && readForm.value !== "";

  const createMeter = (unit: LeaseUnit, type: string) => {
    const label = type === "APARTMENT_WATER" ? "Wasser" : "Waschmaschine";
    meters.create.mutate(
      {
        lease_unit_id: unit.id,
        meter_type: type,
        name: `${unit.designation} ${label}`,
        unit: "m3",
      },
      { onSuccess: () => ok(`Zähler „${unit.designation} ${label}" angelegt`), onError: err },
    );
  };

  const meterOf = (unitId: number, type: string) =>
    propMeters.find((m) => m.lease_unit_id === unitId && m.meter_type === type);

  return (
    <Card withBorder p="sm">
      <Text fw={600} mb={4}>
        Wohnungszähler
      </Text>
      <Text size="xs" c="dimmed" mb="md">
        Je Wohnung 2 Zähler (Wohnung + Waschmaschine). Stände werden fortlaufend erfasst – die Kosten
        werden nach dem Verbrauchsanteil je Wohnung verteilt (Summe aller Wohnungsverbräuche).
      </Text>
      <Checkbox
        mb="md"
        label="Waschmaschinen-Zähler berücksichtigen (optional)"
        description="Wenn deaktiviert, zählen nur die Wohnungs-Wasserzähler – die Waschmaschinen-Werte fließen nicht ein."
        checked={waschAktiv}
        onChange={(e) => onToggleWasch(e.currentTarget.checked)}
      />

      {propUnits.map((unit) => (
        <Card key={unit.id} withBorder p={0} mb="sm">
          <Accordion defaultValue={String(unit.id)}>
            <Accordion.Item value={String(unit.id)}>
              <Accordion.Control>{unit.designation}</Accordion.Control>
              <Accordion.Panel>
                <Group grow align="start" p="xs">
                  {ZAEHLER_TYPEN.filter((t) => waschAktiv || t.value !== "WASHING_MACHINE").map((t) => {
                    const meter = meterOf(unit.id, t.value);
                    const meterReadings = propReadings
                      .filter((r) => r.meter_id === meter?.id)
                      .sort((a, b) => a.reading_date.localeCompare(b.reading_date));
                    return (
                      <Stack key={t.value} gap="xs">
                        <Group justify="space-between">
                          <Text size="sm" fw={600}>
                            {t.label}
                          </Text>
                          {meter ? (
                            <Button size="compact-xs" variant="light" onClick={() => openReadNew(meter)}>
                              + Stand
                            </Button>
                          ) : (
                            <Button size="compact-xs" variant="light" onClick={() => createMeter(unit, t.value)}>
                              + Zähler
                            </Button>
                          )}
                        </Group>
                        <Table>
                          <Table.Thead>
                            <Table.Tr>
                              <Table.Th>Datum</Table.Th>
                              <Table.Th>Wert (m³)</Table.Th>
                              <Table.Th>Quelle</Table.Th>
                              <Table.Th></Table.Th>
                            </Table.Tr>
                          </Table.Thead>
                          <Table.Tbody>
                            {meter && meterReadings.length === 0 && (
                              <Table.Tr>
                                <Table.Td colSpan={4}>
                                  <Text size="xs" c="dimmed">
                                    Keine Stände
                                  </Text>
                                </Table.Td>
                              </Table.Tr>
                            )}
                            {meter &&
                              meterReadings.map((r) => (
                                <Table.Tr key={r.id}>
                                  <Table.Td>{r.reading_date}</Table.Td>
                                  <Table.Td>
                                    {r.vor_zaehlerwechsel ? (
                                      <Group gap={4} wrap="nowrap">
                                        <Text span>{fmt(Number(r.value), 0)}</Text>
                                        <Text span c="dimmed">
                                          → {fmt(Number(r.neuer_zaehler_start ?? 0), 0)}
                                        </Text>
                                      </Group>
                                    ) : (
                                      fmt(Number(r.value), 0)
                                    )}
                                  </Table.Td>
                                  <Table.Td>
                                    <ReadingSource source={r.source} />
                                  </Table.Td>
                                  <Table.Td>
                                    <Group gap="xs" justify="flex-end">
                                      <Button size="compact-xs" variant="light" onClick={() => openReadEdit(r)}>
                                        Ändern
                                      </Button>
                                      <Button
                                        size="compact-xs"
                                        variant="light"
                                        color="red"
                                        onClick={() => setReadDel(r)}
                                      >
                                        Löschen
                                      </Button>
                                    </Group>
                                  </Table.Td>
                                </Table.Tr>
                              ))}
                          </Table.Tbody>
                        </Table>
                      </Stack>
                    );
                  })}
                </Group>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </Card>
      ))}

      <Modal
        opened={readOpen}
        onClose={() => setReadOpen(false)}
        title={readEdit ? "Zählerstand ändern" : "Zählerstand hinzufügen"}
        size="sm"
      >
        <Stack>
          <TextInput
            type="date"
            label="Datum"
            value={readForm.reading_date}
            onChange={(e) => setReadForm({ ...readForm, reading_date: e.currentTarget.value })}
          />
          <NumberInput
            label="Wert (m³)"
            value={Number(readForm.value || 0)}
            onChange={(v) => setReadForm({ ...readForm, value: String(v ?? "") })}
            decimalScale={4}
            min={0}
          />
          <Stack gap={4}>
            <Text size="sm" fw={500}>
              Herkunft
            </Text>
            <SegmentedControl
              data={READING_SOURCE_OPTIONS}
              value={readForm.source}
              onChange={(v) => setReadForm({ ...readForm, source: v })}
              fullWidth
            />
          </Stack>
          <ZaehlerwechselFields
            vor={readForm.vor_zaehlerwechsel}
            start={readForm.neuer_zaehler_start}
            onVor={(v) => setReadForm({ ...readForm, vor_zaehlerwechsel: v })}
            onStart={(v) => setReadForm({ ...readForm, neuer_zaehler_start: v })}
          />
          <Text size="xs" c="dimmed">
            Fortlaufend: Der letzte Stand ist als Startwert vorbelegt.
          </Text>
          <Group justify="flex-end">
            <Button onClick={saveReading} disabled={!canSaveReading}>
              Speichern
            </Button>
          </Group>
        </Stack>
      </Modal>

      <ConfirmDeleteModal
        opened={!!readDel}
        title="Zählerstand löschen?"
        message={`Zählerstand vom ${readDel?.reading_date} wird dauerhaft gelöscht.`}
        confirmText="LÖSCHEN"
        onClose={() => setReadDel(null)}
        onConfirm={() => {
          if (readDel) readings.remove.mutate(readDel.id);
          setReadDel(null);
        }}
      />
    </Card>
  );
}
