import { Fragment, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Accordion,
  Alert,
  Button,
  Card,
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
import WasserWohnungszaehler from "../components/WasserWohnungszaehler";
import ZaehlerwechselFields from "../components/ZaehlerwechselFields";
import { useTestData } from "../context/TestDataContext";
import { useObject } from "../context/ObjectContext";
import { useCrud } from "../hooks/useCrud";
import { visibleProperties } from "../utils/testData";
import type { CostCategory, Property, WasserPrice, WasserReading } from "../api/types";

const KINDS = [
  { value: "GRUNDGEBUEHR", label: "Grundgebühr (€/Jahr)" },
  { value: "TRINKWASSER", label: "Trinkwasser (€/m³)" },
  { value: "SCHMUTZWASSER", label: "Schmutzwasser (€/m³)" },
  { value: "NIEDERSCHLAGSWASSER", label: "Niederschlagswasser (€/m²/Jahr)" },
];
const KIND_LABEL = Object.fromEntries(KINDS.map((k) => [k.value, k.label]));

/** Standard-MwSt je Art: Trinkwasser/Grundgebühr 7 %, Schmutz/Niederschlag 0 %. */
const DEFAULT_VAT: Record<string, string> = {
  GRUNDGEBUEHR: "7",
  TRINKWASSER: "7",
  SCHMUTZWASSER: "0",
  NIEDERSCHLAGSWASSER: "0",
};

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = (msg = "Fehler beim Speichern") => notifications.show({ message: msg, color: "red" });
const fmt = (v: number | undefined | null, digits = 2) =>
  v == null ? "—" : v.toLocaleString("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });

/** Betrag je Art: Grundgebühr 2 Nachkommastellen, €/m³ wie eingegeben (max. 5). */
const fmtBetrag = (v: number | undefined | null, kind: string) => {
  if (v == null) return "—";
  return v.toLocaleString("de-DE", {
    minimumFractionDigits: kind === "GRUNDGEBUEHR" ? 2 : 0,
    maximumFractionDigits: kind === "GRUNDGEBUEHR" ? 2 : 5,
  });
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

export default function WasserPage() {
  const qc = useQueryClient();
  const props = useCrud<Property>("/properties", "properties");
  const prices = useCrud<WasserPrice>("/wasser/prices", "wasser-prices");
  const readings = useCrud<WasserReading>("/wasser/readings", "wasser-readings");
  const { hideTest } = useTestData();
  const { propertyFilter, setPropertyFilter } = useObject();
  const propertyId = propertyFilter ? Number(propertyFilter) : null;

  const [priceOpen, setPriceOpen] = useState(false);
  const [priceEdit, setPriceEdit] = useState<WasserPrice | null>(null);
  const [priceKind, setPriceKind] = useState("TRINKWASSER");
  const [priceForm, setPriceForm] = useState({ valid_from: "", valid_to: "", amount: "", vat_rate: "7" });
  const [priceDel, setPriceDel] = useState<WasserPrice | null>(null);

  const [readOpen, setReadOpen] = useState(false);
  const [readEdit, setReadEdit] = useState<WasserReading | null>(null);
  const [readForm, setReadForm] = useState({
    reading_date: "",
    value: "",
    vor_zaehlerwechsel: false,
    neuer_zaehler_start: "",
  });
  const [readDel, setReadDel] = useState<WasserReading | null>(null);

  // Plan A (Verbrauch je Wohnung) oder Plan B (Hauptzähler)
  const { data: planData } = useQuery({
    queryKey: ["wasser-plan", propertyId],
    queryFn: async () => (await api.get<{ plan: string }>(`/wasser/${propertyId}/plan`)).data,
    enabled: propertyId != null,
  });
  const isPlanA = planData?.plan === "A";

  // Zuordnung Wasser → Abrechnung: bestehende Kostenstellen (Trinkwasser/Schmutzwasser/Niederschlagswasser)
  const currentProp = (props.list.data ?? []).find((p) => p.id === propertyId);
  // Zählerinfos erst relevant, wenn eine Wasser-Zuordnung getroffen wurde (sonst unklar ob Plan A/B)
  const hasZuordnung = !!(
    currentProp &&
    (currentProp.wasser_trinkwasser_category_id != null ||
      currentProp.wasser_schmutzwasser_category_id != null ||
      currentProp.wasser_niederschlag_category_id != null)
  );

  // Waschmaschinen-Zähler (Plan A) optional: wenn deaktiviert, zählen nur Wohnungs-Wasserzähler
  const waschAktiv = currentProp?.wasser_waschmaschinen_aktiv !== false;
  const saveWaschAktiv = async (v: boolean) => {
    if (!propertyId) return;
    try {
      await api.patch(`/properties/${propertyId}`, { wasser_waschmaschinen_aktiv: v });
      await props.list.refetch();
      ok(
        v
          ? "Waschmaschinen-Zähler werden berücksichtigt"
          : "Waschmaschinen-Zähler deaktiviert – nur Wohnungs-Wasserzähler zählen",
      );
    } catch {
      err();
    }
  };
  const { data: costCats } = useQuery({
    queryKey: ["wasser-cost-categories", propertyId],
    queryFn: async () =>
      (await api.get<CostCategory[]>("/cost-categories", { params: { property_id: propertyId } })).data,
    enabled: propertyId != null,
  });
  const catOptions = [
    { value: "", label: "– nicht zugeordnet –" },
    ...(costCats ?? []).map((c) => ({ value: String(c.id), label: c.name })),
  ];
  const saveMapping = async (
    field: "wasser_trinkwasser_category_id" | "wasser_schmutzwasser_category_id" | "wasser_niederschlag_category_id",
    v: string | null,
  ) => {
    if (!propertyId) return;
    const payload: Record<string, number | null> = {};
    payload[field] = v ? Number(v) : null;
    try {
      await api.patch(`/properties/${propertyId}`, payload);
      await props.list.refetch();
      // Zuordnung bestimmt Plan A/B → Plan-Query sofort aktualisieren
      qc.invalidateQueries({ queryKey: ["wasser-plan", propertyId] });
      ok("Zuordnung gespeichert");
    } catch {
      err("Speichern fehlgeschlagen");
    }
  };

  const propPrices = (prices.list.data ?? []).filter((p) => p.property_id === propertyId);
  const propReadings = (readings.list.data ?? []).filter((r) => r.property_id === propertyId);

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
      // Gebührenfelder mit dem letzten bekannten Wert vorbelegen (MwSt sonst artabhängiger Standard)
      amount: last ? String(Number(last.amount)) : "",
      vat_rate: last ? String(last.vat_rate) : DEFAULT_VAT[kind],
    });
    setPriceOpen(true);
  };
  const openPriceEdit = (p: WasserPrice) => {
    setPriceEdit(p);
    setPriceKind(p.kind);
    setPriceForm({
      valid_from: p.valid_from,
      valid_to: p.valid_to,
      amount: String(Number(p.amount)),
      vat_rate: String(p.vat_rate),
    });
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
      vat_rate: Number(priceForm.vat_rate === "" ? DEFAULT_VAT[priceKind] : priceForm.vat_rate),
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

  const openReadNew = () => {
    setReadEdit(null);
    // Startwert vorbelegen: letzter bekannter Endwert (ganze m³); ohne Stand → 1.1.2025
    const sorted = [...propReadings].sort((a, b) => a.reading_date.localeCompare(b.reading_date));
    const last = sorted[sorted.length - 1];
    setReadForm({
      reading_date: last ? "" : "2025-01-01",
      value: last ? String(Number(last.value)) : "",
      vor_zaehlerwechsel: false,
      neuer_zaehler_start: "",
    });
    setReadOpen(true);
  };
  const openReadEdit = (r: WasserReading) => {
    setReadEdit(r);
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
      <Title order={2}>Wasser</Title>
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
            <Text size="xs" c="dimmed" mb="xs">
              Wähle für Trinkwasser, Schmutzwasser und Niederschlagswasser die bestehende Kostenstelle in der
              Abrechnung.
            </Text>
            <Group grow>
              <Select
                label="Trinkwasser"
                clearable
                data={catOptions}
                value={currentProp?.wasser_trinkwasser_category_id ? String(currentProp.wasser_trinkwasser_category_id) : ""}
                onChange={(v) => saveMapping("wasser_trinkwasser_category_id", v)}
              />
              <Select
                label="Schmutzwasser"
                clearable
                data={catOptions}
                value={currentProp?.wasser_schmutzwasser_category_id ? String(currentProp.wasser_schmutzwasser_category_id) : ""}
                onChange={(v) => saveMapping("wasser_schmutzwasser_category_id", v)}
              />
              <Select
                label="Niederschlagswasser"
                clearable
                data={catOptions}
                value={currentProp?.wasser_niederschlag_category_id ? String(currentProp.wasser_niederschlag_category_id) : ""}
                onChange={(v) => saveMapping("wasser_niederschlag_category_id", v)}
              />
            </Group>
          </Card>

          <Accordion multiple defaultValue={["tarif", "zaehler"]} mb="md">
            <Accordion.Item value="tarif">
              <Accordion.Control>Tarif</Accordion.Control>
              <Accordion.Panel>
                <Text size="sm" c="dimmed">
                  Zeiträume je Art müssen lückenlos aneinander anschließen. MwSt-Standard je Art: Trinkwasser/Grundgebühr 7 %,
                  Schmutz-/Niederschlagswasser 0 %.
                </Text>
                {currentProp?.wasser_versiegelte_flaeche != null ? (
            <Text size="sm" c="dimmed">
              Versiegelte Fläche (Niederschlagswasser): <b>{fmt(Number(currentProp.wasser_versiegelte_flaeche), 2)} m²</b>{" "}
              (hinterlegt unter Stammdaten → Objekte)
            </Text>
          ) : (
            <Alert color="yellow" py="xs">
              Bitte hinterlege die versiegelte Fläche (m²) für Niederschlagswasser unter Stammdaten → Objekte.
            </Alert>
          )}
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
                          <Table.Td>{fmt(Number(p.vat_rate), 0)} %</Table.Td>
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
            {hasZuordnung && (
              <Accordion.Item value="zaehler">
                <Accordion.Control>Zähler</Accordion.Control>
                <Accordion.Panel>
                  {!isPlanA && (
                    <Card withBorder p="sm">
                <Group justify="space-between" mb="xs">
                  <Text fw={600}>Hauptzähler</Text>
                  <Button size="compact-xs" variant="light" onClick={openReadNew}>
                    + Stand
                  </Button>
                </Group>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Datum</Table.Th>
                      <Table.Th>Wert (m³)</Table.Th>
                      <Table.Th></Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {propReadings.length === 0 && (
                      <Table.Tr>
                        <Table.Td colSpan={3}>
                          <Text size="sm" c="dimmed">
                            Keine Stände
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    )}
                    {[...propReadings]
                      .sort((a, b) => a.reading_date.localeCompare(b.reading_date))
                      .map((r) => (
                        <Table.Tr key={r.id}>
                          <Table.Td>{r.reading_date}</Table.Td>
                          <Table.Td>{fmt(Number(r.value), 0)}</Table.Td>
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
                  {isPlanA && (
                    <WasserWohnungszaehler
                      propertyId={propertyId}
                      waschAktiv={waschAktiv}
                      onToggleWasch={saveWaschAktiv}
                    />
                  )}
                </Accordion.Panel>
              </Accordion.Item>
            )}
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
              label={
                priceKind === "GRUNDGEBUEHR"
                  ? "Betrag (€/Jahr)"
                  : priceKind === "NIEDERSCHLAGSWASSER"
                    ? "Betrag (€/m²/Jahr)"
                    : "Betrag (€/m³)"
              }
              value={Number(priceForm.amount)}
              onChange={(v) => setPriceForm({ ...priceForm, amount: String(v ?? "") })}
              decimalScale={priceKind === "GRUNDGEBUEHR" ? 2 : 5}
              fixedDecimalScale={priceKind === "GRUNDGEBUEHR"}
              min={0}
            />
            <NumberInput
              label="MwSt (%)"
              value={Number(priceForm.vat_rate === "" ? DEFAULT_VAT[priceKind] : priceForm.vat_rate)}
              onChange={(v) =>
                setPriceForm({ ...priceForm, vat_rate: String(v ?? DEFAULT_VAT[priceKind]) })
              }
              decimalScale={1}
              fixedDecimalScale
              min={0}
            />
          </Group>
          <Text size="xs" c="dimmed">
            Startwert schließt automatisch an den letzten Zeitraum an. Bei gleichem Betrag und gleicher MwSt wird der
            neue Endwert mit dem vorherigen Zeitraum zu einem Block zusammengeführt.
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
            decimalScale={0}
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
