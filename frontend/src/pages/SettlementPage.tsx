import { useEffect, useState } from "react";
import {
  Accordion,
  Alert,
  Button,
  Card,
  Group,
  Select,
  SegmentedControl,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_URL, api, fmt, num } from "../api/client";
import { useTestData } from "../context/TestDataContext";
import { useObject } from "../context/ObjectContext";
import { useCrud } from "../hooks/useCrud";
import { visibleProperties } from "../utils/testData";
import type { FinalizedResult, MissingItem, NoInvoiceFlag, Property, SettlementResult } from "../api/types";

// Zeigt Werte wie eingegeben/berechnet an – ohne Aufrundung auf 2 Stellen
const fmtNoRound = (v: unknown): string => {
  const n = num(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("de-DE", { maximumFractionDigits: 8 });
};

// Datum "2025-06-30" → "30.06." (ohne Jahr) bzw. "30.06.2025" (mit Jahr).
// Fehlt das Datum (z. B. veraltete Antwort), wird auf Jahresgrenzen zurückgefallen.
const fmtPeriod = (iso: string | null | undefined, year: number, withYear = false): string => {
  if (!iso) return withYear ? `31.12.${year}` : "01.01";
  const [y, m, d] = iso.split("-");
  return withYear ? `${d}.${m}.${y}` : `${d}.${m}`;
};

// Abrechnungsjahre dynamisch: von 2025 (Start) bis aktuelles Jahr + 3,
// damit Folgejahre (z. B. 2027, 2031) ohne Codeänderung verfügbar sind.
const CURRENT_YEAR = new Date().getFullYear();
// Abrechnung erfolgt immer für das Vorjahr → Standardjahr = aktuelles Jahr − 1
const DEFAULT_YEAR = CURRENT_YEAR - 1;
const YEARS = Array.from({ length: CURRENT_YEAR + 3 - 2025 + 1 }, (_, i) => String(2025 + i));

export default function SettlementPage() {
  const props = useCrud<Property>("/properties", "properties");
  const { hideTest } = useTestData();
  const { propertyFilter: propertyId, setPropertyFilter: setPropertyId } = useObject();
  const [year, setYear] = useState<string>(String(DEFAULT_YEAR));

  const result = useQuery({
    queryKey: ["settlement", propertyId, year],
    enabled: !!propertyId,
    queryFn: async () =>
      (await api.get<SettlementResult>(`/settlements/${propertyId}/${year}`)).data,
  });

  const completeness = useQuery({
    queryKey: ["completeness", propertyId, year],
    enabled: !!propertyId,
    queryFn: async () =>
      (await api.get<MissingItem[]>(`/settlements/${propertyId}/${year}/completeness`)).data,
  });

  // Kostenarten, die je Jahr als "keine Rechnung" markiert sind
  const noInvoices = useQuery({
    queryKey: ["no-invoices", propertyId, year],
    enabled: !!propertyId,
    queryFn: async () =>
      (await api.get<NoInvoiceFlag[]>(`/settlements/${propertyId}/${year}/no-invoices`)).data,
  });

  const markNoInvoice = async (categoryId: number) => {
    try {
      await api.post(`/settlements/${propertyId}/${year}/no-invoices`, { cost_category_id: categoryId });
      await Promise.all([completeness.refetch(), noInvoices.refetch()]);
    } catch {
      notifications.show({ message: "Fehler beim Markieren", color: "red" });
    }
  };
  const unmarkNoInvoice = async (flagId: number) => {
    try {
      await api.delete(`/settlements/${propertyId}/${year}/no-invoices/${flagId}`);
      await Promise.all([completeness.refetch(), noInvoices.refetch()]);
    } catch {
      notifications.show({ message: "Fehler beim Entfernen", color: "red" });
    }
  };

  // Umschalter: live berechnete Abrechnung vs. finalisierter Snapshot
  const [view, setView] = useState<"live" | "finalized">("live");
  const finalized = useQuery({
    queryKey: ["settlementFinalized", propertyId, year],
    enabled: !!propertyId && view === "finalized",
    retry: false,
    queryFn: async () =>
      (await api.get<FinalizedResult>(`/settlements/${propertyId}/${year}/finalized`)).data,
  });

  // Aufgeklappte Mieter-Karten – geteilt zwischen Live und Finalisiert,
  // damit der Zustand beim Umschalten erhalten bleibt.
  const [openTenants, setOpenTenants] = useState<string[]>([]);
  useEffect(() => {
    setOpenTenants([]);
  }, [propertyId, year]);
  useEffect(() => {
    const first = result.data?.tenant_lines[0];
    if (first) {
      setOpenTenants((prev) => (prev.length === 0 ? [String(first.tenant_id)] : prev));
    }
  }, [result.data]);

  if (!propertyId) {
    return (
      <Stack>
        <Title order={2}>Abrechnung</Title>
        <Select
          label="Objekt"
          placeholder="Objekt wählen"
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyId}
          onChange={setPropertyId}
          w={320}
        />
      </Stack>
    );
  }

  return (
    <Stack>
      <Title order={2}>Abrechnung</Title>
      <Group>
        <Select
          label="Objekt"
          data={visibleProperties(props.list.data ?? [], hideTest).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyId}
          onChange={setPropertyId}
          w={280}
        />
        <Select label="Jahr" data={YEARS} value={year} onChange={(v) => setYear(v ?? String(DEFAULT_YEAR))} w={120} />
        <Stack gap={5}>
          <Text size="sm" fw={500} style={{ lineHeight: 1.55 }}>
            Ansicht
          </Text>
          <SegmentedControl
            value={view}
            onChange={(v) => setView(v as "live" | "finalized")}
            data={[
              { value: "live", label: "Live" },
              { value: "finalized", label: "Finalisiert" },
            ]}
          />
        </Stack>
      </Group>

      {completeness.data && completeness.data.length > 0 && (
        <Alert color="yellow" title="Noch fehlende Daten">
          <Stack gap={4}>
            {completeness.data.map((m, i) => (
              <Group key={i} justify="space-between" gap="xs">
                <Text size="sm">
                  • {m.label} {m.detail ? `(${m.detail})` : ""}
                </Text>
                {m.kind === "INVOICE" && m.category_id && (
                  <Button
                    size="compact-xs"
                    variant="light"
                    onClick={() => markNoInvoice(m.category_id!)}
                  >
                    Keine Rechnung dieses Jahr
                  </Button>
                )}
              </Group>
            ))}
          </Stack>
        </Alert>
      )}

      {noInvoices.data && noInvoices.data.length > 0 && (
        <Card withBorder p="xs" mb="xs">
          <Stack gap={6}>
            <Text size="sm" fw={600}>
              Als „keine Rechnung“ markiert
            </Text>
            {noInvoices.data.map((f) => (
              <Group key={f.id} justify="space-between" gap="xs">
                <Text size="sm">
                  • {f.category_name} ({f.year})
                </Text>
                <Button
                  size="compact-xs"
                  variant="light"
                  color="gray"
                  onClick={() => unmarkNoInvoice(f.id)}
                >
                  Rückgängig
                </Button>
              </Group>
            ))}
          </Stack>
        </Card>
      )}

      {result.isLoading && <Text>Berechne …</Text>}
      {view === "live" && result.data && (
        <ResultView
          data={result.data}
          propertyId={Number(propertyId)}
          year={Number(year)}
          street={props.list.data?.find((p) => p.id === Number(propertyId))?.street ?? ""}
          open={openTenants}
          onOpenChange={setOpenTenants}
          onFinalized={() => {
            result.refetch();
            completeness.refetch();
          }}
        />
      )}
      {view === "finalized" &&
        (finalized.isLoading ? (
          <Text>Lade Snapshot …</Text>
        ) : finalized.isError ? (
          <Text c="dimmed">
            Noch nicht finalisiert – erst „Abrechnung finalisieren“ ausführen.
          </Text>
        ) : (
          finalized.data && (
            <FinalizedView
              data={finalized.data}
              street={props.list.data?.find((p) => p.id === Number(propertyId))?.street ?? ""}
              open={openTenants}
              onOpenChange={setOpenTenants}
            />
          )
        ))}
    </Stack>
  );
}

function ResultView({
  data,
  propertyId,
  year,
  street,
  open,
  onOpenChange,
  onFinalized,
}: {
  data: SettlementResult;
  propertyId: number;
  year: number;
  street: string;
  open: string[];
  onOpenChange: (value: string[]) => void;
  onFinalized: () => void;
}) {
  const qc = useQueryClient();
  const finalize = useMutation({
    mutationFn: () => api.post(`/settlements/${propertyId}/${year}/finalize`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settlements"] });
      notifications.show({ message: "Abrechnung finalisiert", color: "green" });
      onFinalized();
    },
    onError: () => notifications.show({ message: "Fehler beim Finalisieren", color: "red" }),
  });

  return (
    <Stack>
      {data.warnings.length > 0 && (
        <Alert color="orange" title="Hinweise">
          {data.warnings.map((w, i) => (
            <Text key={i} size="sm">
              • {w}
            </Text>
          ))}
        </Alert>
      )}

      <Title order={4}>Mieterabrechnungen</Title>
      <Accordion multiple value={open} onChange={onOpenChange}>
        {data.tenant_lines.map((t) => (
          <Accordion.Item key={t.tenant_id} value={String(t.tenant_id)}>
            <Accordion.Control>
              {t.name} – {street || data.property_name} – Abrechnung für den Zeitraum{" "}
              {fmtPeriod(t.period_start, year)} – {fmtPeriod(t.period_end, year, true)}
            </Accordion.Control>
            <Accordion.Panel>
              <Group justify="flex-end" mb="xs">
                <Button
                  size="compact-xs"
                  variant="outline"
                  component="a"
                  href={`${API_URL}/settlements/${propertyId}/${year}/tenants/${t.tenant_id}/pdf`}
                  target="_blank"
                >
                  PDF
                </Button>
              </Group>
              <Table withColumnBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Kostenart</Table.Th>
                    <Table.Th ta="right">Gesamtkosten</Table.Th>
                <Table.Th>verteilt nach</Table.Th>
                <Table.Th ta="right">Gesamt</Table.Th>
                <Table.Th ta="right">Ihr Anteil</Table.Th>
                <Table.Th>Tage</Table.Th>
                <Table.Th ta="right">Ihr Kostenanteil</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {t.details.map((d) => (
                <Table.Tr key={`${d.code}-${d.basis_label}`}>
                  <Table.Td>{d.name}</Table.Td>
                  <Table.Td ta="right">{fmt(d.year_cost)} €</Table.Td>
                  <Table.Td>{d.basis_label}</Table.Td>
                  <Table.Td ta="right">
                    {d.basis_total != null ? fmtNoRound(d.basis_total) : "—"}
                  </Table.Td>
                  <Table.Td ta="right">
                    {d.basis_share != null ? fmtNoRound(d.basis_share) : "—"}
                  </Table.Td>
                  <Table.Td>
                    {d.days} von {data.days_in_year}
                  </Table.Td>
                  <Table.Td ta="right">{fmt(d.amount)} €</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
            <Table.Tfoot>
              <Table.Tr style={{ background: "#f1f3f5" }}>
                <Table.Td fw={700} colSpan={6}>
                  Ihre Gesamtkosten
                </Table.Td>
                <Table.Td ta="right" fw={700}>
                  {fmt(t.total_costs)} €
                </Table.Td>
              </Table.Tr>
              <Table.Tr style={{ background: "#f1f3f5" }}>
                <Table.Td colSpan={6}>Ihre Nebenkosten Vorauszahlungen</Table.Td>
                <Table.Td ta="right">
                  <Tooltip
                    multiline
                    withArrow
                    w={300}
                    label={t.advance_breakdown
                      .map(
                        (s) =>
                          `${fmtPeriod(s.valid_from, year)} – ${fmtPeriod(s.valid_to, year, true)}: ` +
                          `${fmt(s.amount)} €/Monat (${fmtNoRound(s.months)} Monate)`,
                      )
                      .join("\n")}
                  >
                    <span style={{ cursor: "help", borderBottom: "1px dashed #868e96" }}>
                      {fmt(t.advance_total, 2)} €
                    </span>
                  </Tooltip>
                </Table.Td>
              </Table.Tr>
              <Table.Tr style={{ background: "#f1f3f5" }}>
                <Table.Td fw={700} colSpan={6}>
                  {t.saldo >= 0 ? "Nachzahlung" : "Gutschrift"}
                </Table.Td>
                <Table.Td ta="right" fw={700}>
                  {fmt(Math.abs(t.saldo))} €
                </Table.Td>
              </Table.Tr>
            </Table.Tfoot>
          </Table>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>

      {data.unallocated_water !== 0 && (
        <Text size="sm" c="dimmed">
          Nicht umgelegtes Restwasser (Leerstand): {fmt(data.unallocated_water, 2)} €
        </Text>
      )}

      <Group>
        <Button onClick={() => finalize.mutate()} loading={finalize.isPending}>
          Abrechnung finalisieren
        </Button>
      </Group>
    </Stack>
  );
}

// Kompakte Ansicht des finalisierten Snapshots (unveränderlicher Stand zum Zeitpunkt
// der Finalisierung) – zum Vergleich mit der live berechneten Abrechnung.
function FinalizedView({
  data,
  street,
  open,
  onOpenChange,
}: {
  data: FinalizedResult;
  street: string;
  open: string[];
  onOpenChange: (value: string[]) => void;
}) {
  const fmtDate = (iso: string | null): string => {
    if (!iso) return "–";
    const [y, m, d] = iso.slice(0, 10).split("-");
    return `${d}.${m}.${y}`;
  };

  return (
    <Stack>
      <Text size="sm" c="dimmed">
        Finalisiert am {fmtDate(data.computed_at)} – dieser Stand bleibt unverändert, auch
        wenn die Daten später angepasst werden. Zum Vergleich: Live-Ansicht aktivieren.
      </Text>
      <Accordion multiple value={open} onChange={onOpenChange}>
        {data.tenant_lines.map((t) => (
          <Accordion.Item key={t.tenant_id} value={String(t.tenant_id)}>
            <Accordion.Control>
              {t.name} – {street || data.property_name} – {t.tenant_days} Tage
            </Accordion.Control>
            <Accordion.Panel>
              <Table withColumnBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Kostenart</Table.Th>
                    <Table.Th ta="right">Ihr Kostenanteil</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {Object.entries(t.breakdown).map(([code, amount]) => (
                    <Table.Tr key={code}>
                      <Table.Td>{data.category_names[code] ?? code}</Table.Td>
                      <Table.Td ta="right">{fmt(amount)} €</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
                <Table.Tfoot>
                  <Table.Tr style={{ background: "#f1f3f5" }}>
                    <Table.Td fw={700}>Ihre Gesamtkosten</Table.Td>
                    <Table.Td ta="right" fw={700}>
                      {fmt(t.total_costs)} €
                    </Table.Td>
                  </Table.Tr>
                  <Table.Tr style={{ background: "#f1f3f5" }}>
                    <Table.Td>Ihre Nebenkosten Vorauszahlungen</Table.Td>
                    <Table.Td ta="right">{fmt(t.advance_total)} €</Table.Td>
                  </Table.Tr>
                  <Table.Tr style={{ background: "#f1f3f5" }}>
                    <Table.Td fw={700}>{t.saldo >= 0 ? "Nachzahlung" : "Gutschrift"}</Table.Td>
                    <Table.Td ta="right" fw={700}>
                      {fmt(Math.abs(t.saldo))} €
                    </Table.Td>
                  </Table.Tr>
                </Table.Tfoot>
              </Table>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
    </Stack>
  );
}
