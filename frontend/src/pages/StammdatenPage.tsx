import { useState } from "react";
import {
  Accordion,
  Badge,
  Button,
  Checkbox,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, fmt, num } from "../api/client";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import { InlineEdit } from "../components/InlineEdit";
import PageHelp from "../components/PageHelp";
import { stammdatenHelp } from "../help/helpContent";
import { useTestData } from "../context/TestDataContext";
import { useCrud } from "../hooks/useCrud";
import {
  testPropertyIds,
  visibleProperties,
  visibleTenants,
  visibleUnits,
} from "../utils/testData";
import {
  advanceHistory,
  contactInfo,
  groupTenantsByProperty,
  monthlyBreakdown,
  monthlyTotalWithAdvance,
  unitOptions,
} from "../utils/tenantList";
import type {
  AllocationConfig,
  LeaseUnit,
  Property,
  Tenant,
} from "../api/types";

const ALLOCATION_KEYS = [
  { value: "WF", label: "Wohnfläche (WF)" },
  { value: "NF", label: "Nutzfläche (NF)" },
  { value: "WOHNUNG", label: "Wohnung (1:1)" },
  { value: "CONSUMPTION", label: "Verbrauch" },
  { value: "NONE", label: "nicht umgelegt" },
];

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

// Vorauszahlungsänderungen nur zum Monatsanfang: Datum auf den 1. des Monats setzen
const monthStart = (iso: string): string => {
  if (!iso) return iso;
  const [y, m] = iso.split("-");
  return `${y}-${m}-01`;
};

export default function StammdatenPage() {
  return (
    <Stack>
      <Group>
        <Title order={2}>Stammdaten</Title>
        <PageHelp content={stammdatenHelp} />
      </Group>
      <Tabs defaultValue="properties">
        <Tabs.List>
          <Tabs.Tab value="properties">Objekte</Tabs.Tab>
          <Tabs.Tab value="units">Mieteinheiten</Tabs.Tab>
          <Tabs.Tab value="tenants">Mieter</Tabs.Tab>
          <Tabs.Tab value="configs">Umlageschlüssel</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="properties" pt="md">
          <PropertiesTab />
        </Tabs.Panel>
        <Tabs.Panel value="units" pt="md">
          <UnitsTab />
        </Tabs.Panel>
        <Tabs.Panel value="tenants" pt="md">
          <TenantsTab />
        </Tabs.Panel>
        <Tabs.Panel value="configs" pt="md">
          <ConfigsTab />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

/* ---------- Objekte ---------- */
function PropertiesTab() {
  const { list, create, update, remove } = useCrud<Property>("/properties", "properties");
  const { hideTest } = useTestData();
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Property | null>(null);
  const [del, setDel] = useState<Property | null>(null);
  const [form, setForm] = useState({
    name: "",
    street: "",
    zip_code: "",
    city: "",
    is_test: false,
    wasser_versiegelte_flaeche: "",
  });

  const openCreate = () => {
    setEdit(null);
    setForm({ name: "", street: "", zip_code: "", city: "", is_test: false, wasser_versiegelte_flaeche: "" });
    setOpen(true);
  };
  const openEdit = (p: Property) => {
    setEdit(p);
    setForm({
      name: p.name,
      street: p.street,
      zip_code: p.zip_code,
      city: p.city,
      is_test: Boolean(p.is_test),
      wasser_versiegelte_flaeche: p.wasser_versiegelte_flaeche != null ? String(Number(p.wasser_versiegelte_flaeche)) : "",
    });
    setOpen(true);
  };
  const save = () => {
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    const payload = {
      ...form,
      wasser_versiegelte_flaeche:
        form.wasser_versiegelte_flaeche === "" ? null : Number(form.wasser_versiegelte_flaeche),
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };

  return (
    <>
      <Group mb="sm">
        <Button onClick={openCreate}>Neues Objekt</Button>
      </Group>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Adresse</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {visibleProperties(list.data ?? [], hideTest).map((p) => (
            <Table.Tr key={p.id}>
              <Table.Td>{p.name}</Table.Td>
              <Table.Td>
                {[p.street, p.zip_code, p.city].filter(Boolean).join(", ")}
                {p.wasser_versiegelte_flaeche != null && (
                  <Text size="xs" c="dimmed">
                    Versiegelte Fläche: {fmt(Number(p.wasser_versiegelte_flaeche), 2)} m²
                  </Text>
                )}
              </Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(p)}>
                    Ändern
                  </Button>
                  <Button
                    size="compact-xs"
                    variant="light"
                    color="red"
                    onClick={() => setDel(p)}
                  >
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <ConfirmDeleteModal
        opened={!!del}
        message={`Objekt „${del?.name}“ mit allen zugehörigen Daten (Mieteinheiten, Mieter, Kostenarten, Rechnungen, Zähler) wird dauerhaft gelöscht.`}
        confirmText={del?.name ?? ""}
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) remove.mutate(del.id);
          setDel(null);
        }}
      />

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Objekt ändern" : "Neues Objekt"}>
        <Stack>
          <TextInput
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <TextInput
            label="Straße"
            value={form.street}
            onChange={(e) => setForm({ ...form, street: e.currentTarget.value })}
          />
          <Group grow>
            <TextInput
              label="PLZ"
              value={form.zip_code}
              onChange={(e) => setForm({ ...form, zip_code: e.currentTarget.value })}
            />
            <TextInput
              label="Ort"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.currentTarget.value })}
            />
          </Group>
          <NumberInput
            label="Versiegelte Fläche (m²)"
            description="Berechnungsgrundlage für Niederschlagswasser (€/m²)"
            value={form.wasser_versiegelte_flaeche === "" ? "" : Number(form.wasser_versiegelte_flaeche)}
            onChange={(v) => setForm({ ...form, wasser_versiegelte_flaeche: String(v ?? "") })}
            decimalScale={2}
            min={0}
          />
          <Checkbox
            label="Testdaten (in Übersicht/Dropdowns ausblendbar)"
            checked={form.is_test}
            onChange={(e) => setForm({ ...form, is_test: e.currentTarget.checked })}
          />
          <Group justify="flex-end">
            <Button onClick={save}>Speichern</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

/* ---------- Mieteinheiten ---------- */
function UnitsTab() {
  const { list, create, update, remove } = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const props = useCrud<Property>("/properties", "properties");
  const { hideTest } = useTestData();
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<LeaseUnit | null>(null);
  const [del, setDel] = useState<LeaseUnit | null>(null);
  const [form, setForm] = useState({ property_id: "", designation: "", living_area: "", extra_area: "" });

  const openCreate = () => {
    setEdit(null);
    setForm({ property_id: "", designation: "", living_area: "", extra_area: "" });
    setOpen(true);
  };
  const openEdit = (u: LeaseUnit) => {
    setEdit(u);
    setForm({
      property_id: String(u.property_id),
      designation: u.designation,
      living_area: String(u.living_area),
      extra_area: String(u.extra_area),
    });
    setOpen(true);
  };
  const save = () => {
    const payload = {
      property_id: Number(form.property_id),
      designation: form.designation,
      living_area: form.living_area || "0",
      extra_area: form.extra_area || "0",
    };
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };
  const allProps = props.list.data ?? [];
  const visProps = visibleProperties(allProps, hideTest);
  const testIds = testPropertyIds(allProps);
  const grouped = visProps
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name, "de"))
    .map((p) => {
      const gUnits = visibleUnits(list.data ?? [], testIds)
        .filter((u) => u.property_id === p.id)
        .sort((a, b) => a.designation.localeCompare(b.designation, "de"));
      return {
        property: p,
        units: gUnits,
        wf: gUnits.reduce((s, u) => s + num(u.living_area), 0),
        nf: gUnits.reduce((s, u) => s + num(u.utility_area), 0),
      };
    })
    .filter((g) => g.units.length > 0);

  return (
    <>
      <Group mb="sm">
        <Button onClick={openCreate}>Neue Mieteinheit</Button>
      </Group>

      {grouped.length === 0 && <Text c="dimmed">Keine Mieteinheiten vorhanden.</Text>}

      {grouped.map(({ property, units: gUnits, wf, nf }) => (
        <Stack key={property.id} mb="lg">
          <Group>
            <Title order={5}>{property.name}</Title>
            <Text size="sm" c="dimmed">
              WF {fmt(wf, 2)} · NF {fmt(nf, 2)} m²
            </Text>
          </Group>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Bezeichnung</Table.Th>
                <Table.Th>WF (m²)</Table.Th>
                <Table.Th>Extra (m²)</Table.Th>
                <Table.Th>NF (m²)</Table.Th>
                <Table.Th></Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {gUnits.map((u) => (
                <Table.Tr key={u.id}>
                  <Table.Td>{u.designation}</Table.Td>
                  <Table.Td>{fmt(u.living_area, 2)}</Table.Td>
                  <Table.Td>{fmt(u.extra_area, 2)}</Table.Td>
                  <Table.Td>{fmt(u.utility_area, 2)}</Table.Td>
                  <Table.Td>
                    <Group gap="xs" justify="flex-end">
                      <Button size="compact-xs" variant="light" onClick={() => openEdit(u)}>
                        Ändern
                      </Button>
                      <Button size="compact-xs" variant="light" color="red" onClick={() => setDel(u)}>
                        Löschen
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Stack>
      ))}

      <ConfirmDeleteModal
        opened={!!del}
        message={`Mieteinheit „${del?.designation}“ samt zugehöriger Mieter und Zähler wird dauerhaft gelöscht.`}
        confirmText={del?.designation ?? ""}
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) remove.mutate(del.id);
          setDel(null);
        }}
      />

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Mieteinheit ändern" : "Neue Mieteinheit"}>
        <Stack>
          <Select
            label="Objekt"
            data={visProps.map((p) => ({ value: String(p.id), label: p.name }))}
            value={form.property_id || null}
            onChange={(v) => setForm({ ...form, property_id: v ?? "" })}
          />
          <TextInput
            label="Bezeichnung"
            value={form.designation}
            onChange={(e) => setForm({ ...form, designation: e.currentTarget.value })}
          />
          <Group grow>
            <NumberInput
              label="Wohnfläche (m²)"
              value={form.living_area}
              onChange={(v) => setForm({ ...form, living_area: String(v ?? "") })}
              decimalScale={3}
            />
            <NumberInput
              label="Extrafläche (m²)"
              value={form.extra_area}
              onChange={(v) => setForm({ ...form, extra_area: String(v ?? "") })}
              decimalScale={3}
            />
          </Group>
          <Group justify="flex-end">
            <Button onClick={save}>Speichern</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

/* ---------- Mieter ---------- */
export function TenantsTab() {
  const { list, create, update, remove } = useCrud<Tenant>("/tenants", "tenants");
  const units = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const props = useCrud<Property>("/properties", "properties");
  const { hideTest } = useTestData();
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Tenant | null>(null);
  const [del, setDel] = useState<Tenant | null>(null);
  const [hideOld, setHideOld] = useState(false);
  const [form, setForm] = useState({
    lease_unit_id: "",
    name: "",
    move_in: "",
    move_out: "",
    monthly_advance: "",
    phone: "",
    email: "",
    advances: [{ valid_from: "", amount: "" }],
    monthly_costs: [{ name: "", amount: "" }],
  });

  const openCreate = () => {
    setEdit(null);
    setForm({
      lease_unit_id: "",
      name: "",
      move_in: "",
      move_out: "",
      monthly_advance: "",
      phone: "",
      email: "",
      advances: [{ valid_from: "", amount: "" }],
      monthly_costs: [{ name: "", amount: "" }],
    });
    setOpen(true);
  };
  const openEdit = (t: Tenant) => {
    setEdit(t);
    const advances =
      t.advances && t.advances.length
        ? t.advances.map((a) => ({ valid_from: a.valid_from, amount: String(a.amount) }))
        : [{ valid_from: t.move_in, amount: String(t.monthly_advance) }];
    const costs =
      t.monthly_costs && t.monthly_costs.length
        ? t.monthly_costs.map((c) => ({ name: c.name, amount: String(c.amount) }))
        : [{ name: "", amount: "" }];
    setForm({
      lease_unit_id: String(t.lease_unit_id),
      name: t.name,
      move_in: t.move_in,
      move_out: t.move_out ?? "",
      monthly_advance: String(t.monthly_advance),
      phone: t.phone ?? "",
      email: t.email ?? "",
      advances,
      monthly_costs: costs,
    });
    setOpen(true);
  };
  const setAdvance = (idx: number, patch: Partial<{ valid_from: string; amount: string }>) => {
    // Änderungen der Vorauszahlung (weitere Zeiträume) nur zum Monatsanfang zulässig
    const next =
      patch.valid_from !== undefined && idx > 0
        ? { ...patch, valid_from: monthStart(patch.valid_from) }
        : patch;
    setForm((f) => ({ ...f, advances: f.advances.map((a, i) => (i === idx ? { ...a, ...next } : a)) }));
  };
  const addAdvance = () => setForm((f) => ({ ...f, advances: [...f.advances, { valid_from: "", amount: "" }] }));
  const removeAdvance = (idx: number) =>
    setForm((f) => ({ ...f, advances: f.advances.filter((_, i) => i !== idx) }));
  const setCost = (idx: number, patch: Partial<{ name: string; amount: string }>) =>
    setForm((f) => ({ ...f, monthly_costs: f.monthly_costs.map((c, i) => (i === idx ? { ...c, ...patch } : c)) }));
  const addCost = () => setForm((f) => ({ ...f, monthly_costs: [...f.monthly_costs, { name: "", amount: "" }] }));
  const removeCost = (idx: number) =>
    setForm((f) => ({ ...f, monthly_costs: f.monthly_costs.filter((_, i) => i !== idx) }));

  const save = () => {
    const validAdvances = form.advances
      .filter((a) => a.valid_from)
      .map((a) => ({ valid_from: a.valid_from, amount: a.amount || "0" }))
      .sort((a, b) => a.valid_from.localeCompare(b.valid_from));
    const validCosts = form.monthly_costs
      .filter((c) => c.name.trim())
      .map((c) => ({ name: c.name.trim(), amount: c.amount || "0" }));
    const payload = {
      lease_unit_id: Number(form.lease_unit_id),
      name: form.name,
      move_in: form.move_in,
      move_out: form.move_out || null,
      monthly_advance: form.monthly_advance || "0",
      phone: form.phone || null,
      email: form.email || null,
      advances: validAdvances.length
        ? validAdvances
        : [{ valid_from: form.move_in, amount: form.monthly_advance || "0" }],
      monthly_costs: validCosts,
    };
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };
  const unitDesignation = (id: number) => units.list.data?.find((x) => x.id === id)?.designation ?? "";
  const allProps = props.list.data ?? [];
  const testIds = testPropertyIds(allProps);
  const grouped = groupTenantsByProperty(
    visibleProperties(allProps, hideTest),
    visibleTenants(list.data ?? [], units.list.data ?? [], testIds),
    visibleUnits(units.list.data ?? [], testIds),
    hideOld,
  );

  return (
    <>
      <Group mb="sm">
        <Button onClick={openCreate}>Neuer Mieter</Button>
        <Checkbox
          label="Alte Mieter ausblenden"
          checked={hideOld}
          onChange={(e) => setHideOld(e.currentTarget.checked)}
        />
      </Group>
      {grouped.length === 0 && <Text c="dimmed">Keine Mieter vorhanden.</Text>}

      {grouped.map(({ property, tenants: gTenants }) => (
        <Stack key={property.id} mb="lg">
          <Group>
            <Title order={5}>{property.name}</Title>
          </Group>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Einheit</Table.Th>
                <Table.Th>Einzug</Table.Th>
                <Table.Th>Auszug</Table.Th>
                <Table.Th>Vorauszahlung €/Monat</Table.Th>
                <Table.Th>Monatskosten €/Monat</Table.Th>
                <Table.Th></Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {gTenants.map((t) => {
                const contact = contactInfo(t);
                return (
                  <Table.Tr key={t.id} style={t.move_out ? { opacity: 0.45 } : undefined}>
                    <Table.Td>
                      {contact.email || contact.phone ? (
                        <Tooltip
                          label={
                            <Stack gap={2}>
                              {contact.email && <Text size="sm">E-Mail: {contact.email}</Text>}
                              {contact.phone && <Text size="sm">Telefon: {contact.phone}</Text>}
                            </Stack>
                          }
                          withArrow
                        >
                          <span>{t.name}</span>
                        </Tooltip>
                      ) : (
                        t.name
                      )}
                    </Table.Td>
                    <Table.Td>{unitDesignation(t.lease_unit_id)}</Table.Td>
                    <Table.Td>{t.move_in}</Table.Td>
                    <Table.Td>{t.move_out ?? "—"}</Table.Td>
                    <Table.Td>
                      <Tooltip
                        label={
                          <Stack gap={4} miw={190}>
                            {advanceHistory(t).map((a, idx) => (
                              <Group key={idx} justify="space-between" gap="xl" wrap="nowrap">
                                <Text size="sm">ab {a.valid_from}</Text>
                                <Text size="sm" style={{ fontVariantNumeric: "tabular-nums" }}>
                                  {fmt(a.amount, 2)} €
                                </Text>
                              </Group>
                            ))}
                          </Stack>
                        }
                        withArrow
                      >
                        <span style={{ cursor: "help" }}>
                          {fmt(t.monthly_advance, 2)}
                          {t.advances && t.advances.length > 1 && (
                            <Badge variant="light" size="sm" ml={4}>
                              {t.advances.length} Zeiträume
                            </Badge>
                          )}
                        </span>
                      </Tooltip>
                    </Table.Td>
                    <Table.Td>
                      {monthlyTotalWithAdvance(t) > 0 ? (
                        <Tooltip
                          label={
                            <Stack gap={4} miw={190}>
                              {monthlyBreakdown(t).map((c) => (
                                <Group key={c.name} justify="space-between" gap="xl" wrap="nowrap">
                                  <Text size="sm">{c.name}</Text>
                                  <Text size="sm" style={{ fontVariantNumeric: "tabular-nums" }}>
                                    {fmt(c.amount, 2)} €
                                  </Text>
                                </Group>
                              ))}
                            </Stack>
                          }
                          withArrow
                        >
                          <Text style={{ cursor: "help" }}>
                            {fmt(monthlyTotalWithAdvance(t), 2)}
                          </Text>
                        </Tooltip>
                      ) : (
                        "—"
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs" justify="flex-end">
                        <Button size="compact-xs" variant="light" onClick={() => openEdit(t)}>
                          Ändern
                        </Button>
                        <Button size="compact-xs" variant="light" color="red" onClick={() => setDel(t)}>
                          Löschen
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Stack>
      ))}

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Mieter ändern" : "Neuer Mieter"}>
        <Stack>
          <Select
            label="Mieteinheit"
            data={unitOptions(
              visibleUnits(units.list.data ?? [], testIds),
              visibleProperties(props.list.data ?? [], hideTest),
            )}
            value={form.lease_unit_id || null}
            onChange={(v) => setForm({ ...form, lease_unit_id: v ?? "" })}
          />
          <TextInput
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Group grow>
            <TextInput
              type="date"
              label="Einzug"
              value={form.move_in}
              onChange={(e) => setForm({ ...form, move_in: e.currentTarget.value })}
            />
            <TextInput
              type="date"
              label="Auszug (leer = wohnt noch)"
              value={form.move_out}
              onChange={(e) => setForm({ ...form, move_out: e.currentTarget.value })}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Telefon"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.currentTarget.value })}
            />
            <TextInput
              label="E-Mail"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.currentTarget.value })}
            />
          </Group>

          <Title order={6}>Vorauszahlung (Zeiträume)</Title>
          {form.advances.map((a, idx) => (
            <Group key={idx} grow>
              <TextInput
                type="date"
                label="Gültig ab"
                value={a.valid_from}
                onChange={(e) => setAdvance(idx, { valid_from: e.currentTarget.value })}
              />
              <NumberInput
                label="Betrag €/Monat"
                value={a.amount}
                onChange={(v) => setAdvance(idx, { amount: String(v ?? "") })}
                decimalScale={2}
              />
              {form.advances.length > 1 && (
                <Button variant="light" color="red" mt="xl" onClick={() => removeAdvance(idx)}>
                  ✕
                </Button>
              )}
            </Group>
          ))}
          <Button variant="light" onClick={addAdvance}>
            + Zeitraum hinzufügen
          </Button>
          <Text size="xs" c="dimmed">
            Änderungen der Vorauszahlung (weitere Zeiträume) sind nur zum Monatsanfang (1. des
            Monats) möglich.
          </Text>

          <Title order={6}>Monatliche Kosten (z. B. Kaltmiete, Heizkosten – nicht umlagefähig)</Title>
          {form.monthly_costs.map((c, idx) => (
            <Group key={idx} grow>
              <TextInput
                label="Bezeichnung"
                placeholder="z. B. Kaltmiete"
                value={c.name}
                onChange={(e) => setCost(idx, { name: e.currentTarget.value })}
              />
              <NumberInput
                label="Betrag €/Monat"
                value={c.amount}
                onChange={(v) => setCost(idx, { amount: String(v ?? "") })}
                decimalScale={2}
              />
              {form.monthly_costs.length > 1 && (
                <Button variant="light" color="red" mt="xl" onClick={() => removeCost(idx)}>
                  ✕
                </Button>
              )}
            </Group>
          ))}
          <Button variant="light" onClick={addCost}>
            + Kosten hinzufügen
          </Button>

          <Group justify="flex-end">
            <Button onClick={save}>Speichern</Button>
          </Group>
        </Stack>
      </Modal>

      <ConfirmDeleteModal
        opened={!!del}
        message={`Mieter „${del?.name}“ mit Vorauszahlungs-Historie und Monatskosten wird dauerhaft gelöscht.`}
        confirmText={del?.name ?? ""}
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) remove.mutate(del.id);
          setDel(null);
        }}
      />
    </>
  );
}

/* ---------- Umlageschlüssel (je Objekt) ---------- */
export function ConfigsTab() {
  const qc = useQueryClient();
  const props = useCrud<Property>("/properties", "properties");
  const { hideTest } = useTestData();
  const [del, setDel] = useState<AllocationConfig | null>(null);
  // Pro Objekt eine eigene Eingabezeile für „Hinzufügen“
  const [adds, setAdds] = useState<Record<number, { name: string; key: string }>>({});

  const configs = useQuery({
    queryKey: ["allocation-configs"],
    queryFn: async () => (await api.get<AllocationConfig[]>("/allocation-configs")).data,
  });

  const createConfig = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/allocation-configs", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["allocation-configs"] });
      ok("Gespeichert");
    },
    onError: err,
  });
  const updateConfig = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.patch(`/allocation-configs/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["allocation-configs"] });
      ok("Gespeichert");
    },
    onError: err,
  });
  const renameCategory = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.patch(`/cost-categories/${id}`, { name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["allocation-configs"] });
      qc.invalidateQueries({ queryKey: ["cost-categories"] });
      ok("Gespeichert");
    },
    onError: err,
  });
  const deleteConfig = useMutation({
    mutationFn: (id: number) => api.delete(`/allocation-configs/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["allocation-configs"] }),
  });
  // Tauscht die Sortierung zweier benachbarter Zeilen (Hoch/Runter-Buttons).
  const reorderConfigs = useMutation({
    mutationFn: async ({ a, b }: { a: AllocationConfig; b: AllocationConfig }) => {
      await api.patch(`/allocation-configs/${a.id}`, { sort_order: b.sort_order });
      await api.patch(`/allocation-configs/${b.id}`, { sort_order: a.sort_order });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["allocation-configs"] }),
  });

  const add = (propertyId: number) => {
    const a = adds[propertyId];
    const name = (a?.name ?? "").trim();
    if (!name) return;
    const arr = (configs.data ?? []).filter((c) => c.property_id === propertyId);
    const nextOrder = arr.length ? Math.max(...arr.map((c) => c.sort_order)) + 1 : 1;
    createConfig.mutate({
      property_id: propertyId,
      cost_category_name: name,
      allocation_key: a?.key ?? "WF",
      sort_order: nextOrder,
    });
    setAdds((prev) => ({ ...prev, [propertyId]: { name: "", key: a?.key ?? "WF" } }));
  };

  const move = (propertyId: number, idx: number, dir: -1 | 1) => {
    const arr = (configs.data ?? []).filter((c) => c.property_id === propertyId);
    const j = idx + dir;
    if (j < 0 || j >= arr.length) return;
    reorderConfigs.mutate({ a: arr[idx], b: arr[j] });
  };

  const grouped = visibleProperties(props.list.data ?? [], hideTest)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name, "de"))
    .map((p) => {
      const gConfigs = (configs.data ?? [])
        .filter((c) => c.property_id === p.id)
        .sort((a, b) => a.sort_order - b.sort_order);
      return { property: p, configs: gConfigs };
    });

  return (
    <Stack>
      {grouped.map(({ property, configs: gConfigs }) => {
        const a = adds[property.id] ?? { name: "", key: "WF" };
        const total = gConfigs.length;
        return (
          <Accordion key={property.id} mb="lg" defaultValue={String(property.id)}>
            <Accordion.Item value={String(property.id)}>
              <Accordion.Control>
                <Title order={5}>{property.name}</Title>
              </Accordion.Control>
              <Accordion.Panel>
                <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Reihenfolge</Table.Th>
                  <Table.Th>Kostenart</Table.Th>
                  <Table.Th>Umlageschlüssel</Table.Th>
                  <Table.Th></Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {gConfigs.map((c, idx) => (
                  <Table.Tr key={c.id}>
                    <Table.Td>
                      <Group gap={10} wrap="nowrap">
                        <Text size="sm" w={24} ta="center">
                          {c.sort_order}
                        </Text>
                        <Group gap={4} wrap="nowrap">
                          <Button
                            size="compact-xs"
                            variant="light"
                            aria-label="nach oben"
                            disabled={idx === 0}
                            onClick={() => move(property.id, idx, -1)}
                          >
                            ▲
                          </Button>
                          <Button
                            size="compact-xs"
                            variant="light"
                            aria-label="nach unten"
                            disabled={idx === total - 1}
                            onClick={() => move(property.id, idx, 1)}
                          >
                            ▼
                          </Button>
                        </Group>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <InlineEdit
                        value={c.category_name ?? String(c.cost_category_id)}
                        onSave={(name) => renameCategory.mutate({ id: c.cost_category_id, name })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Select
                        size="xs"
                        w={220}
                        data={ALLOCATION_KEYS}
                        value={c.allocation_key}
                        onChange={(v) => v && updateConfig.mutate({ id: c.id, data: { allocation_key: v } })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Button
                        size="compact-xs"
                        variant="light"
                        color="red"
                        onClick={() => setDel(c)}
                      >
                        Entfernen
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>

            <Group align="flex-end">
              <TextInput
                label="Kostenart (Name)"
                placeholder="z. B. Grundsteuer"
                value={a.name}
                onChange={(e) => {
                  const name = e.currentTarget.value;
                  setAdds((prev) => ({ ...prev, [property.id]: { ...a, name } }));
                }}
                w={280}
              />
              <Select
                label="Umlageschlüssel"
                data={ALLOCATION_KEYS}
                value={a.key}
                onChange={(v) =>
                  setAdds((prev) => ({ ...prev, [property.id]: { ...a, key: v ?? "WF" } }))
                }
                w={220}
              />
              <Button onClick={() => add(property.id)} disabled={!a.name.trim()}>
                Hinzufügen
              </Button>
            </Group>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        );
      })}

      <ConfirmDeleteModal
        opened={!!del}
        title="Umlageschlüssel entfernen?"
        message={`Umlage-Konfiguration für Kostenart „${del?.category_name}“ wird entfernt (Kostenart bleibt erhalten).`}
        confirmText={del?.category_name ?? ""}
        confirmLabel="Entfernen"
        onClose={() => setDel(null)}
        onConfirm={() => {
          if (del) deleteConfig.mutate(del.id);
          setDel(null);
        }}
      />
    </Stack>
  );
}
