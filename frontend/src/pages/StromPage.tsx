import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Accordion,
  Button,
  Card,
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
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api } from "../api/client";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import ZaehlerwechselFields from "../components/ZaehlerwechselFields";
import PageHelp from "../components/PageHelp";
import { stromHelp } from "../help/helpContent";
import { useTestData } from "../context/TestDataContext";
import { useObject } from "../context/ObjectContext";
import { useCrud } from "../hooks/useCrud";
import { visibleProperties } from "../utils/testData";
import type { CostCategory, Property, StromPrice, StromReading } from "../api/types";

const KINDS = [
  { value: "GRUNDGEBUEHR", label: "Grundgebühr (€/Jahr)" },
  { value: "ARBEITSPREIS", label: "Arbeitspreis (€/kWh)" },
  { value: "STROMSTEUER", label: "Stromsteuer (€/kWh)" },
];
const KIND_LABEL = Object.fromEntries(KINDS.map((k) => [k.value, k.label]));

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = (msg = "Fehler beim Speichern") => notifications.show({ message: msg, color: "red" });
const fmt = (v: number | undefined | null, digits = 2) =>
  v == null ? "—" : v.toLocaleString("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });

/** Betrag je Art: Grundgebühr 2 Nachkommastellen, Arbeitspreis/Stromsteuer wie eingegeben (max. 5). */
const fmtBetrag = (v: number | undefined | null, kind: string) => {
  if (v == null) return "—";
  return v.toLocaleString("de-DE", {
    minimumFractionDigits: kind === "GRUNDGEBUEHR" ? 2 : 0,
    maximumFractionDigits: kind === "GRUNDGEBUEHR" ? 2 : 5,
  });
};

/** Wert-Zelle mit Zählerwechsel-Markierung (z. B. "1240 → 0"), wie bei den Wasserzählern. */
const ReadingWert = ({ r }: { r: { value: string | number; vor_zaehlerwechsel?: boolean; neuer_zaehler_start?: string | number | null } }) => {
  if (!r.vor_zaehlerwechsel) return fmt(Number(r.value), 0);
  return (
    <Group gap={4} wrap="nowrap">
      <Text span>{fmt(Number(r.value), 0)}</Text>
      <Text span c="dimmed">
        → {fmt(Number(r.neuer_zaehler_start ?? 0), 0)}
      </Text>
    </Group>
  );
};

/** Tag-Addition auf "YYYY-MM-DD" (zeitzonen-sicher). */
const addDays = (date: string, days: number) => {
  const [y, m, d] = date.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  const yy = dt.getFullYear();
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  const dd = String(dt.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
};

export default function StromPage() {
  const props = useCrud<Property>("/properties", "properties");
  const prices = useCrud<StromPrice>("/strom/prices", "strom-prices");
  const readings = useCrud<StromReading>("/strom/readings", "strom-readings");
  const { hideTest } = useTestData();
  const { propertyFilter, setPropertyFilter } = useObject();
  const propertyId = propertyFilter ? Number(propertyFilter) : null;

  const [priceOpen, setPriceOpen] = useState(false);
  const [priceEdit, setPriceEdit] = useState<StromPrice | null>(null);
  const [priceKind, setPriceKind] = useState("GRUNDGEBUEHR");
  const [priceForm, setPriceForm] = useState({ valid_from: "", valid_to: "", amount: "", vat_rate: "19" });
  const [priceDel, setPriceDel] = useState<StromPrice | null>(null);

  const [readOpen, setReadOpen] = useState(false);
  const [readEdit, setReadEdit] = useState<StromReading | null>(null);
  const [readRole, setReadRole] = useState("HAUPTZAEHLER");
  const [readForm, setReadForm] = useState({
    reading_date: "",
    value: "",
    vor_zaehlerwechsel: false,
    neuer_zaehler_start: "",
  });
  const [readDel, setReadDel] = useState<StromReading | null>(null);

  // Verbindung Strom → Abrechnung: Stromkosten einer bestehenden Kostenstelle zuordnen (je Objekt)
  const currentProp = (props.list.data ?? []).find((p) => p.id === propertyId);
  const { data: costCats } = useQuery({
    queryKey: ["strom-cost-categories", propertyId],
    queryFn: async () =>
      (await api.get<CostCategory[]>("/cost-categories", { params: { property_id: propertyId } })).data,
    enabled: propertyId != null,
  });
  const saveStromCategory = async (v: string | null) => {
    if (!propertyId) return;
    let payload: number | null;
    if (v == null || v === "none") payload = null; // nicht in Abrechnung
    else if (v === "strom") payload = 0; // eigene Zeile "Strom"
    else payload = Number(v); // bestehende Kostenstelle
    try {
      await api.patch(`/properties/${propertyId}`, { strom_allocation_category_id: payload });
      await props.list.refetch();
      ok("Strom-Zuordnung gespeichert");
    } catch {
      err("Speichern fehlgeschlagen");
    }
  };
  const stromCatValue =
    currentProp?.strom_allocation_category_id == null
      ? "none"
      : currentProp.strom_allocation_category_id === 0
        ? "strom"
        : String(currentProp.strom_allocation_category_id);

  // Unterzähler optional: wenn deaktiviert, fließen dessen Werte nicht in die Berechnung ein
  const unterAktiv = currentProp?.strom_unterzaehler_aktiv !== false;
  const saveStromUnter = async (v: boolean) => {
    if (!propertyId) return;
    try {
      await api.patch(`/properties/${propertyId}`, { strom_unterzaehler_aktiv: v });
      await props.list.refetch();
      ok(v ? "Unterzähler wird berücksichtigt" : "Unterzähler deaktiviert – Werte fließen nicht ein");
    } catch {
      err("Speichern fehlgeschlagen");
    }
  };

  const propPrices = (prices.list.data ?? []).filter((p) => p.property_id === propertyId);
  const propReadings = (readings.list.data ?? []).filter((r) => r.property_id === propertyId);
  const haupt = propReadings.filter((r) => r.role === "HAUPTZAEHLER");
  const unter = propReadings.filter((r) => r.role === "UNTERZAEHLER");

  const openPriceNew = (kind: string) => {
    setPriceEdit(null);
    setPriceKind(kind);
    const last = propPrices
      .filter((p) => p.kind === kind)
      .sort((a, b) => a.valid_to.localeCompare(b.valid_to))
      .at(-1);
    setPriceForm({
      // Startwert immer fix: nahtloser Anschluss an den letzten Zeitraum (sonst 1.1.2025)
      valid_from: last ? addDays(last.valid_to, 1) : "2025-01-01",
      valid_to: "",
      // Gebührenfelder mit dem letzten bekannten Wert vorbelegen
      amount: last ? String(Number(last.amount)) : "",
      vat_rate: last ? String(last.vat_rate) : "19",
    });
    setPriceOpen(true);
  };
  const openPriceEdit = (p: StromPrice) => {
    setPriceEdit(p);
    setPriceKind(p.kind);
    setPriceForm({ valid_from: p.valid_from, valid_to: p.valid_to, amount: String(Number(p.amount)), vat_rate: String(p.vat_rate) });
    setPriceOpen(true);
  };
  const savePrice = () => {
    if (!propertyId) return;
    const payload = {
      property_id: propertyId,
      kind: priceKind,
      valid_from: priceForm.valid_from,
      valid_to: priceForm.valid_to,
      amount: Number(priceForm.amount),
      vat_rate: Number(priceForm.vat_rate === "" ? "19" : priceForm.vat_rate),
    };
    const done = () => {
      setPriceOpen(false);
      ok("Gespeichert");
    };
    const onError = (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      err(typeof detail === "string" ? detail : undefined);
    };

    // Neuer Block: Wenn nur der Endwert abweicht (gleicher Betrag, gleiche MwSt,
    // nahtloser Anschluss), mit dem vorherigen Zeitraum zu EINEM Block zusammenführen.
    if (!priceEdit) {
      const prev = propPrices
        .filter((p) => p.kind === priceKind)
        .sort((a, b) => b.valid_to.localeCompare(a.valid_to))[0];
      const contiguous = prev != null && addDays(prev.valid_to, 1) === payload.valid_from;
      if (prev && contiguous && payload.amount === Number(prev.amount) && payload.vat_rate === Number(prev.vat_rate)) {
        prices.update.mutate(
          { id: prev.id, data: { ...payload, valid_from: prev.valid_from } },
          {
            onSuccess: () => {
              setPriceOpen(false);
              ok("Mit vorherigem Zeitraum zu einem Block zusammengeführt");
            },
            onError,
          },
        );
        return;
      }
    }
    if (priceEdit) prices.update.mutate({ id: priceEdit.id, data: payload }, { onSuccess: done, onError });
    else prices.create.mutate(payload, { onSuccess: done, onError });
  };

  const openReadNew = (role: string) => {
    setReadEdit(null);
    setReadRole(role);
    // Startwert vorbelegen: letzter bekannter Endwert desselben Zählers.
    // Gibt es noch keinen Stand, beginne mit dem 1.1.2025.
    const sameRole = propReadings
      .filter((r) => r.role === role)
      .sort((a, b) => a.reading_date.localeCompare(b.reading_date));
    const last = sameRole[sameRole.length - 1];
    setReadForm({
      reading_date: last ? "" : "2025-01-01",
      value: last ? String(Number(last.value)) : "",
      vor_zaehlerwechsel: false,
      neuer_zaehler_start: "",
    });
    setReadOpen(true);
  };
  const openReadEdit = (r: StromReading) => {
    setReadEdit(r);
    setReadRole(r.role);
    setReadForm({
      reading_date: r.reading_date,
      value: String(Number(r.value)),
      vor_zaehlerwechsel: Boolean(r.vor_zaehlerwechsel),
      neuer_zaehler_start: r.neuer_zaehler_start != null ? String(Number(r.neuer_zaehler_start)) : "",
    });
    setReadOpen(true);
  };
  const saveReading = () => {
    if (!propertyId) return;
    const payload = {
      property_id: propertyId,
      role: readRole,
      reading_date: readForm.reading_date,
      value: Number(readForm.value),
      vor_zaehlerwechsel: readForm.vor_zaehlerwechsel,
      neuer_zaehler_start: readForm.vor_zaehlerwechsel
        ? Number(readForm.neuer_zaehler_start === "" ? "0" : readForm.neuer_zaehler_start)
        : 0,
    };
    const done = () => {
      setReadOpen(false);
      ok("Gespeichert");
    };
    if (readEdit) readings.update.mutate({ id: readEdit.id, data: payload }, { onSuccess: done, onError: () => err() });
    else readings.create.mutate(payload, { onSuccess: done, onError: () => err() });
  };

  const canSavePrice =
    propertyId != null && priceForm.valid_from !== "" && priceForm.valid_to !== "" && priceForm.amount !== "";
  const canSaveReading = propertyId != null && readForm.reading_date !== "" && readForm.value !== "";

  return (
    <Stack>
      <Group>
        <Title order={2}>Strom</Title>
        <PageHelp content={stromHelp} />
      </Group>
      <Group>
        <Select
          label="Objekt"
          placeholder="Objekt wählen"
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyFilter}
          onChange={setPropertyFilter}
          w={280}
        />
      </Group>

      {propertyId != null && (
        <>
          <Card withBorder p="sm" mb="md">
            <Title order={4} mb="sm">
              Zuordnung zur Abrechnung
            </Title>
            <Group align="flex-end">
              <Select
                label="Stromkosten in der Abrechnung"
                data={[
                  { value: "none", label: "Nicht in Abrechnung" },
                  { value: "strom", label: "Eigene Zeile „Strom“" },
                  ...(costCats ?? []).map((c) => ({ value: String(c.id), label: c.name })),
                ]}
                value={stromCatValue}
                onChange={(v) => saveStromCategory(v ?? "none")}
                w={280}
              />
              <Text size="xs" c="dimmed" mb={8}>
                Wähle eine bestehende Kostenstelle (z. B. „Hausbeleuchtung“), in die die Stromkosten
                einfließen – es wird keine neue Kostenstelle angelegt.
              </Text>
            </Group>
          </Card>

          <Accordion multiple defaultValue={["tarif", "zaehler"]} mb="md">
            <Accordion.Item value="tarif">
              <Accordion.Control>Tarif</Accordion.Control>
              <Accordion.Panel>
                <Text size="sm" c="dimmed">
                  Zeiträume je Art müssen lückenlos aneinander anschließen (MwSt je Wert, Standard 19 %).
                </Text>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Gültig von</Table.Th>
                <Table.Th>Gültig bis</Table.Th>
                <Table.Th>Betrag</Table.Th>
                <Table.Th>MwSt</Table.Th>
                <Table.Th></Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {KINDS.map((kind) => {
                const rows = propPrices
                  .filter((p) => p.kind === kind.value)
                  .sort((a, b) => a.valid_from.localeCompare(b.valid_from));
                return (
                  <Fragment key={kind.value}>
                    <Table.Tr bg="var(--mantine-color-gray-1)">
                      <Table.Td colSpan={5}>
                        <Group justify="space-between" wrap="nowrap">
                          <Text size="sm" fw={600}>
                            {KIND_LABEL[kind.value]}
                          </Text>
                          <Button size="compact-xs" variant="light" onClick={() => openPriceNew(kind.value)}>
                            + Hinzufügen
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                    {rows.length === 0 ? (
                      <Table.Tr>
                        <Table.Td colSpan={5}>
                          <Text size="sm" c="dimmed">
                            noch kein Zeitraum erfasst
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    ) : (
                      rows.map((p) => (
                        <Table.Tr key={p.id}>
                          <Table.Td>{p.valid_from}</Table.Td>
                          <Table.Td>{p.valid_to}</Table.Td>
                          <Table.Td>{fmtBetrag(Number(p.amount), p.kind)} €</Table.Td>
                          <Table.Td>{fmt(p.vat_rate, 0)} %</Table.Td>
                          <Table.Td>
                            <Group gap="xs" justify="flex-end">
                              <Button size="compact-xs" variant="light" onClick={() => openPriceEdit(p)}>
                                Ändern
                              </Button>
                              <Button size="compact-xs" variant="light" color="red" onClick={() => setPriceDel(p)}>
                                Löschen
                              </Button>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      ))
                    )}
                  </Fragment>
                );
              })}
            </Table.Tbody>
          </Table>
              </Accordion.Panel>
            </Accordion.Item>
            <Accordion.Item value="zaehler">
              <Accordion.Control>Zählerstände</Accordion.Control>
              <Accordion.Panel>
                <Checkbox
                  mb="md"
                  label="Unterzähler berücksichtigen (optional)"
                  description="Wenn deaktiviert, fließen die Unterzähler-Werte (z. B. Heizstrom) nicht in die Berechnung ein."
                  checked={unterAktiv}
                  onChange={(e) => saveStromUnter(e.currentTarget.checked)}
                />
                <Group grow align="flex-start">
            <Card withBorder>
              <Group justify="space-between" mb="xs">
                <Text fw={600}>Hauptzähler</Text>
                <Button size="compact-xs" variant="light" onClick={() => openReadNew("HAUPTZAEHLER")}>
                  + Stand
                </Button>
              </Group>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Datum</Table.Th>
                    <Table.Th>Wert (kWh)</Table.Th>
                    <Table.Th></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {haupt.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={3}>
                        <Text size="sm" c="dimmed">
                          Keine Stände
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                  {haupt.map((r) => (
                    <Table.Tr key={r.id}>
                      <Table.Td>{r.reading_date}</Table.Td>
                      <Table.Td>
                        <ReadingWert r={r} />
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs" justify="flex-end">
                          <Button size="compact-xs" variant="light" onClick={() => openReadEdit(r)}>
                            Ändern
                          </Button>
                          <Button size="compact-xs" variant="light" color="red" onClick={() => setReadDel(r)}>
                            Löschen
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
            {unterAktiv && (
            <Card withBorder>
              <Group justify="space-between" mb="xs">
                <Text fw={600}>Unterzähler (optional)</Text>
                <Button size="compact-xs" variant="light" onClick={() => openReadNew("UNTERZAEHLER")}>
                  + Stand
                </Button>
              </Group>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Datum</Table.Th>
                    <Table.Th>Wert (kWh)</Table.Th>
                    <Table.Th></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {unter.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={3}>
                        <Text size="sm" c="dimmed">
                          Keine Stände
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                  {unter.map((r) => (
                    <Table.Tr key={r.id}>
                      <Table.Td>{r.reading_date}</Table.Td>
                      <Table.Td>
                        <ReadingWert r={r} />
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs" justify="flex-end">
                          <Button size="compact-xs" variant="light" onClick={() => openReadEdit(r)}>
                            Ändern
                          </Button>
                          <Button size="compact-xs" variant="light" color="red" onClick={() => setReadDel(r)}>
                            Löschen
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
            )}
          </Group>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </>
      )}

      <Modal
        opened={priceOpen}
        onClose={() => setPriceOpen(false)}
        title={priceEdit ? "Tarif ändern" : "Tarif hinzufügen"}
        size="md"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            {KIND_LABEL[priceKind]}
          </Text>
          <Group grow>
            <TextInput
              type="date"
              label="Gültig von (Startwert, fix)"
              value={priceForm.valid_from}
              readOnly
              onChange={(e) => setPriceForm({ ...priceForm, valid_from: e.currentTarget.value })}
            />
            <TextInput
              type="date"
              label="Gültig bis"
              value={priceForm.valid_to}
              onChange={(e) => setPriceForm({ ...priceForm, valid_to: e.currentTarget.value })}
            />
          </Group>
          <Group grow>
            <NumberInput
              label={priceKind === "GRUNDGEBUEHR" ? "Betrag (€/Jahr)" : "Betrag (€/kWh)"}
              value={priceForm.amount}
              onChange={(v) => setPriceForm({ ...priceForm, amount: String(v ?? "") })}
              decimalScale={priceKind === "GRUNDGEBUEHR" ? 2 : 5}
              min={0}
            />
            <NumberInput
              label="MwSt (%)"
              value={priceForm.vat_rate}
              onChange={(v) => setPriceForm({ ...priceForm, vat_rate: String(v ?? "19") })}
              decimalScale={1}
              min={0}
            />
          </Group>
          <Text size="xs" c="dimmed">
            Startwert schließt automatisch an den letzten Zeitraum an. Bei gleichem Betrag und gleicher MwSt wird der neue Endwert mit dem vorherigen Zeitraum zu einem Block zusammengeführt.
          </Text>
          <Group justify="flex-end">
            <Button onClick={savePrice} disabled={!canSavePrice}>
              Speichern
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={readOpen}
        onClose={() => setReadOpen(false)}
        title={readEdit ? "Zählerstand ändern" : "Zählerstand hinzufügen"}
        size="sm"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            {readRole === "HAUPTZAEHLER" ? "Hauptzähler" : "Unterzähler"}
          </Text>
          <TextInput
            type="date"
            label="Datum"
            value={readForm.reading_date}
            onChange={(e) => setReadForm({ ...readForm, reading_date: e.currentTarget.value })}
          />
          <NumberInput
            label="Wert (kWh)"
            value={readForm.value}
            onChange={(v) => setReadForm({ ...readForm, value: String(v ?? "") })}
            decimalScale={0}
            step={1}
            min={0}
          />
          <ZaehlerwechselFields
            vor={readForm.vor_zaehlerwechsel}
            start={readForm.neuer_zaehler_start}
            onVor={(v) => setReadForm({ ...readForm, vor_zaehlerwechsel: v })}
            onStart={(v) => setReadForm({ ...readForm, neuer_zaehler_start: v })}
          />
          <Group justify="flex-end">
            <Button onClick={saveReading} disabled={!canSaveReading}>
              Speichern
            </Button>
          </Group>
        </Stack>
      </Modal>

      <ConfirmDeleteModal
        opened={!!priceDel}
        message={`Tarif (${priceDel?.valid_from} – ${priceDel?.valid_to}) wird dauerhaft gelöscht.`}
        confirmText="LÖSCHEN"
        onClose={() => setPriceDel(null)}
        onConfirm={() => {
          if (priceDel) prices.remove.mutate(priceDel.id);
          setPriceDel(null);
        }}
      />
      <ConfirmDeleteModal
        opened={!!readDel}
        message={`Zählerstand (${readDel?.reading_date}) wird dauerhaft gelöscht.`}
        confirmText="LÖSCHEN"
        onClose={() => setReadDel(null)}
        onConfirm={() => {
          if (readDel) readings.remove.mutate(readDel.id);
          setReadDel(null);
        }}
      />
    </Stack>
  );
}
