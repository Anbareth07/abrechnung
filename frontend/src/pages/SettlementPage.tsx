import { useState } from "react";
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_URL, api, fmt } from "../api/client";
import { useCrud } from "../hooks/useCrud";
import type { MissingItem, Property, SettlementResult } from "../api/types";

const KEY_LABEL: Record<string, string> = {
  WF: "Wohnfläche",
  NF: "Nutzfläche",
  CONSUMPTION: "Verbrauch",
  NONE: "—",
};

// Abrechnungsjahre dynamisch: von 2025 (Start) bis aktuelles Jahr + 3,
// damit Folgejahre (z. B. 2027, 2031) ohne Codeänderung verfügbar sind.
const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR + 3 - 2025 + 1 }, (_, i) => String(2025 + i));

export default function SettlementPage() {
  const props = useCrud<Property>("/properties", "properties");
  const [propertyId, setPropertyId] = useState<string | null>(null);
  const [year, setYear] = useState<string>(String(CURRENT_YEAR));

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

  if (!propertyId) {
    return (
      <Stack>
        <Title order={2}>Abrechnung</Title>
        <Select
          label="Objekt"
          placeholder="Objekt wählen"
          data={(props.list.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
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
          data={(props.list.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyId}
          onChange={setPropertyId}
          w={280}
        />
        <Select label="Jahr" data={YEARS} value={year} onChange={(v) => setYear(v ?? String(CURRENT_YEAR))} w={120} />
      </Group>

      {completeness.data && completeness.data.length > 0 && (
        <Alert color="yellow" title="Noch fehlende Daten">
          <Stack gap={4}>
            {completeness.data.map((m, i) => (
              <Text key={i} size="sm">
                • {m.label} {m.detail ? `(${m.detail})` : ""}
              </Text>
            ))}
          </Stack>
        </Alert>
      )}

      {result.isLoading && <Text>Berechne …</Text>}
      {result.data && (
        <ResultView
          data={result.data}
          propertyId={Number(propertyId)}
          year={Number(year)}
          onFinalized={() => {
            result.refetch();
            completeness.refetch();
          }}
        />
      )}
    </Stack>
  );
}

function ResultView({
  data,
  propertyId,
  year,
  onFinalized,
}: {
  data: SettlementResult;
  propertyId: number;
  year: number;
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
      <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }}>
        <Card withBorder>
          <Text size="xs" c="dimmed">Wohnfläche gesamt</Text>
          <Text fw={700}>{fmt(data.total_wf, 2)} m²</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed">Nutzfläche gesamt</Text>
          <Text fw={700}>{fmt(data.total_nf, 2)} m²</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed">Tage im Jahr</Text>
          <Text fw={700}>{data.days_in_year}</Text>
        </Card>
        {data.water_price_per_m3 != null && (
          <Card withBorder>
            <Text size="xs" c="dimmed">Wasserpreis</Text>
            <Text fw={700}>{fmt(data.water_price_per_m3, 4)} €/m³</Text>
          </Card>
        )}
        {data.water && (
          <Card withBorder>
            <Text size="xs" c="dimmed">Gesamtverbrauch Wasser</Text>
            <Text fw={700}>{fmt(data.water.total_consumption, 2)} m³</Text>
          </Card>
        )}
      </SimpleGrid>

      {data.warnings.length > 0 && (
        <Alert color="orange" title="Hinweise">
          {data.warnings.map((w, i) => (
            <Text key={i} size="sm">
              • {w}
            </Text>
          ))}
        </Alert>
      )}

      <Title order={4}>Kostenarten (Gesamtkosten des Hauses)</Title>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Kostenart</Table.Th>
            <Table.Th>Umlageschlüssel</Table.Th>
            <Table.Th>Gesamtkosten (Jahr)</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.category_lines.map((c) => (
            <Table.Tr key={c.code}>
              <Table.Td>{c.name}</Table.Td>
              <Table.Td>{KEY_LABEL[c.allocation_key] ?? c.allocation_key}</Table.Td>
              <Table.Td>{fmt(c.year_cost, 2)} €</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Title order={4}>Mieter</Title>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Mieter</Table.Th>
            <Table.Th>Einheit</Table.Th>
            <Table.Th>Tage</Table.Th>
            <Table.Th>Faktor</Table.Th>
            <Table.Th>Nebenkosten</Table.Th>
            <Table.Th>Vorauszahlung</Table.Th>
            <Table.Th>Saldo</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.tenant_lines.map((t) => (
            <Table.Tr key={t.tenant_id}>
              <Table.Td>{t.name}</Table.Td>
              <Table.Td>{t.designation}</Table.Td>
              <Table.Td>{t.tenant_days}</Table.Td>
              <Table.Td>{fmt(t.time_factor, 4)}</Table.Td>
              <Table.Td>{fmt(t.total_costs, 2)} €</Table.Td>
              <Table.Td>{fmt(t.advance_total, 2)} €</Table.Td>
              <Table.Td>
                <Badge color={t.saldo >= 0 ? "red" : "green"}>
                  {t.saldo >= 0 ? "Nachzahlung" : "Gutschrift"} {fmt(t.saldo, 2)} €
                </Badge>
              </Table.Td>
              <Table.Td>
                <Button
                  size="compact-xs"
                  variant="outline"
                  component="a"
                  href={`${API_URL}/settlements/${propertyId}/${year}/tenants/${t.tenant_id}/pdf`}
                  target="_blank"
                >
                  PDF
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Accordion>
        {data.tenant_lines.map((t) => (
          <Accordion.Item key={t.tenant_id} value={String(t.tenant_id)}>
            <Accordion.Control>{t.name} – Detail</Accordion.Control>
            <Accordion.Panel>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Kostenart</Table.Th>
                    <Table.Th>Betrag</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {Object.entries(t.breakdown).map(([code, amount]) => (
                    <Table.Tr key={code}>
                      <Table.Td>{code}</Table.Td>
                      <Table.Td>{fmt(amount, 2)} €</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
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
