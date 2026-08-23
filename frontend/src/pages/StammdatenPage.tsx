import { useState } from "react";
import {
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
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, fmt } from "../api/client";
import { useCrud } from "../hooks/useCrud";
import type {
  AllocationConfig,
  CostCategory,
  LeaseUnit,
  Property,
  Tenant,
} from "../api/types";

const ALLOCATION_KEYS = [
  { value: "WF", label: "Wohnfläche (WF)" },
  { value: "NF", label: "Nutzfläche (NF)" },
  { value: "CONSUMPTION", label: "Verbrauch" },
  { value: "NONE", label: "nicht umgelegt" },
];

const KEY_LABEL: Record<string, string> = Object.fromEntries(
  ALLOCATION_KEYS.map((k) => [k.value, k.label]),
);

const ok = (msg: string) => notifications.show({ message: msg, color: "green" });
const err = () => notifications.show({ message: "Fehler beim Speichern", color: "red" });

export default function StammdatenPage() {
  return (
    <Stack>
      <Title order={2}>Stammdaten</Title>
      <Tabs defaultValue="properties">
        <Tabs.List>
          <Tabs.Tab value="properties">Objekte</Tabs.Tab>
          <Tabs.Tab value="units">Mieteinheiten</Tabs.Tab>
          <Tabs.Tab value="tenants">Mieter</Tabs.Tab>
          <Tabs.Tab value="categories">Kostenarten</Tabs.Tab>
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
        <Tabs.Panel value="categories" pt="md">
          <CategoriesTab />
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
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Property | null>(null);
  const [form, setForm] = useState({ name: "", street: "", zip_code: "", city: "" });

  const openCreate = () => {
    setEdit(null);
    setForm({ name: "", street: "", zip_code: "", city: "" });
    setOpen(true);
  };
  const openEdit = (p: Property) => {
    setEdit(p);
    setForm({ name: p.name, street: p.street, zip_code: p.zip_code, city: p.city });
    setOpen(true);
  };
  const save = () => {
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: form }, { onSuccess: done, onError: err });
    else create.mutate(form, { onSuccess: done, onError: err });
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
          {(list.data ?? []).map((p) => (
            <Table.Tr key={p.id}>
              <Table.Td>{p.name}</Table.Td>
              <Table.Td>
                {[p.street, p.zip_code, p.city].filter(Boolean).join(", ")}
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
                    onClick={() => remove.mutate(p.id)}
                  >
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

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
          <Button onClick={save}>Speichern</Button>
        </Stack>
      </Modal>
    </>
  );
}

/* ---------- Mieteinheiten ---------- */
function UnitsTab() {
  const { list, create, update, remove } = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const props = useCrud<Property>("/properties", "properties");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<LeaseUnit | null>(null);
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
  const propName = (id: number) => props.list.data?.find((p) => p.id === id)?.name ?? "";

  return (
    <>
      <Group mb="sm">
        <Button onClick={openCreate}>Neue Mieteinheit</Button>
      </Group>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Objekt</Table.Th>
            <Table.Th>Bezeichnung</Table.Th>
            <Table.Th>WF (m²)</Table.Th>
            <Table.Th>Extra (m²)</Table.Th>
            <Table.Th>NF (m²)</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((u) => (
            <Table.Tr key={u.id}>
              <Table.Td>{propName(u.property_id)}</Table.Td>
              <Table.Td>{u.designation}</Table.Td>
              <Table.Td>{fmt(u.living_area, 2)}</Table.Td>
              <Table.Td>{fmt(u.extra_area, 2)}</Table.Td>
              <Table.Td>{fmt(u.utility_area, 2)}</Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(u)}>
                    Ändern
                  </Button>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => remove.mutate(u.id)}>
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Mieteinheit ändern" : "Neue Mieteinheit"}>
        <Stack>
          <Select
            label="Objekt"
            data={(props.list.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
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
          <Button onClick={save}>Speichern</Button>
        </Stack>
      </Modal>
    </>
  );
}

/* ---------- Mieter ---------- */
function TenantsTab() {
  const { list, create, update, remove } = useCrud<Tenant>("/tenants", "tenants");
  const units = useCrud<LeaseUnit>("/lease-units", "lease-units");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Tenant | null>(null);
  const [form, setForm] = useState({
    lease_unit_id: "",
    name: "",
    move_in: "",
    move_out: "",
    monthly_advance: "",
  });

  const openCreate = () => {
    setEdit(null);
    setForm({ lease_unit_id: "", name: "", move_in: "", move_out: "", monthly_advance: "" });
    setOpen(true);
  };
  const openEdit = (t: Tenant) => {
    setEdit(t);
    setForm({
      lease_unit_id: String(t.lease_unit_id),
      name: t.name,
      move_in: t.move_in,
      move_out: t.move_out ?? "",
      monthly_advance: String(t.monthly_advance),
    });
    setOpen(true);
  };
  const save = () => {
    const payload = {
      lease_unit_id: Number(form.lease_unit_id),
      name: form.name,
      move_in: form.move_in,
      move_out: form.move_out || null,
      monthly_advance: form.monthly_advance || "0",
    };
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit) update.mutate({ id: edit.id, data: payload }, { onSuccess: done, onError: err });
    else create.mutate(payload, { onSuccess: done, onError: err });
  };
  const unitLabel = (id: number) => {
    const u = units.list.data?.find((x) => x.id === id);
    return u ? u.designation : "";
  };

  return (
    <>
      <Group mb="sm">
        <Button onClick={openCreate}>Neuer Mieter</Button>
      </Group>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Einheit</Table.Th>
            <Table.Th>Einzug</Table.Th>
            <Table.Th>Auszug</Table.Th>
            <Table.Th>Vorauszahlung €/Monat</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((t) => (
            <Table.Tr key={t.id}>
              <Table.Td>{t.name}</Table.Td>
              <Table.Td>{unitLabel(t.lease_unit_id)}</Table.Td>
              <Table.Td>{t.move_in}</Table.Td>
              <Table.Td>{t.move_out ?? "—"}</Table.Td>
              <Table.Td>{fmt(t.monthly_advance, 2)}</Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(t)}>
                    Ändern
                  </Button>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => remove.mutate(t.id)}>
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Mieter ändern" : "Neuer Mieter"}>
        <Stack>
          <Select
            label="Mieteinheit"
            data={(units.list.data ?? []).map((u) => ({ value: String(u.id), label: u.designation }))}
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
          <NumberInput
            label="Vorauszahlung (€/Monat)"
            value={form.monthly_advance}
            onChange={(v) => setForm({ ...form, monthly_advance: String(v ?? "") })}
            decimalScale={2}
          />
          <Button onClick={save}>Speichern</Button>
        </Stack>
      </Modal>
    </>
  );
}

/* ---------- Kostenarten ---------- */
function CategoriesTab() {
  const { list, create, update, remove } = useCrud<CostCategory>("/cost-categories", "cost-categories");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<CostCategory | null>(null);
  const [form, setForm] = useState({ code: "", name: "", default_allocation_key: "NONE", is_active: true });

  const openCreate = () => {
    setEdit(null);
    setForm({ code: "", name: "", default_allocation_key: "NONE", is_active: true });
    setOpen(true);
  };
  const openEdit = (c: CostCategory) => {
    setEdit(c);
    setForm({
      code: c.code,
      name: c.name,
      default_allocation_key: c.default_allocation_key,
      is_active: c.is_active,
    });
    setOpen(true);
  };
  const save = () => {
    const done = () => {
      setOpen(false);
      ok("Gespeichert");
    };
    if (edit)
      update.mutate({ id: edit.id, data: { ...form, code: undefined } }, { onSuccess: done, onError: err });
    else create.mutate(form, { onSuccess: done, onError: err });
  };

  return (
    <>
      <Group mb="sm">
        <Button onClick={openCreate}>Neue Kostenart</Button>
      </Group>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Code</Table.Th>
            <Table.Th>Name</Table.Th>
            <Table.Th>Default-Umlage</Table.Th>
            <Table.Th>Aktiv</Table.Th>
            <Table.Th></Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((c) => (
            <Table.Tr key={c.id}>
              <Table.Td>{c.code}</Table.Td>
              <Table.Td>{c.name}</Table.Td>
              <Table.Td>
                <Badge variant="light">{KEY_LABEL[c.default_allocation_key] ?? c.default_allocation_key}</Badge>
              </Table.Td>
              <Table.Td>{c.is_active ? "ja" : "nein"}</Table.Td>
              <Table.Td>
                <Group gap="xs" justify="flex-end">
                  <Button size="compact-xs" variant="light" onClick={() => openEdit(c)}>
                    Ändern
                  </Button>
                  <Button size="compact-xs" variant="light" color="red" onClick={() => remove.mutate(c.id)}>
                    Löschen
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={open} onClose={() => setOpen(false)} title={edit ? "Kostenart ändern" : "Neue Kostenart"}>
        <Stack>
          <TextInput
            label="Code (eindeutig, z. B. grundsteuer)"
            value={form.code}
            disabled={!!edit}
            onChange={(e) => setForm({ ...form, code: e.currentTarget.value })}
          />
          <TextInput
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Select
            label="Default-Umlageschlüssel"
            data={ALLOCATION_KEYS}
            value={form.default_allocation_key}
            onChange={(v) => setForm({ ...form, default_allocation_key: v ?? "NONE" })}
          />
          <Checkbox
            label="Aktiv"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.currentTarget.checked })}
          />
          <Button onClick={save}>Speichern</Button>
        </Stack>
      </Modal>
    </>
  );
}

/* ---------- Umlageschlüssel (je Objekt) ---------- */
function ConfigsTab() {
  const qc = useQueryClient();
  const props = useCrud<Property>("/properties", "properties");
  const cats = useCrud<CostCategory>("/cost-categories", "cost-categories");
  const [propertyId, setPropertyId] = useState<string | null>(null);
  const [key, setKey] = useState<string>("WF");
  const [catId, setCatId] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<string>("");

  const configs = useQuery({
    queryKey: ["allocation-configs", propertyId],
    enabled: !!propertyId,
    queryFn: async () =>
      (await api.get<AllocationConfig[]>("/allocation-configs", { params: { property_id: Number(propertyId) } }))
        .data,
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
  const deleteConfig = useMutation({
    mutationFn: (id: number) => api.delete(`/allocation-configs/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["allocation-configs"] }),
  });

  const configuredIds = new Set((configs.data ?? []).map((c) => c.cost_category_id));
  const availableCats = (cats.list.data ?? []).filter((c) => !configuredIds.has(c.id));

  const add = () => {
    if (!propertyId || !catId) return;
    createConfig.mutate({
      property_id: Number(propertyId),
      cost_category_id: Number(catId),
      allocation_key: key,
      sort_order: Number(sortOrder || 0),
    });
    setCatId(null);
  };

  return (
    <Stack>
      <Group>
        <Select
          label="Objekt"
          placeholder="Objekt wählen"
          data={(props.list.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
          value={propertyId}
          onChange={setPropertyId}
          w={280}
        />
      </Group>

      {propertyId && (
        <>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Kostenart</Table.Th>
                <Table.Th>Umlageschlüssel</Table.Th>
                <Table.Th>Sortierung</Table.Th>
                <Table.Th></Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(configs.data ?? []).map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>{c.category_name ?? c.cost_category_id}</Table.Td>
                  <Table.Td>
                    <Select
                      size="xs"
                      w={220}
                      data={ALLOCATION_KEYS}
                      value={c.allocation_key}
                      onChange={(v) => v && updateConfig.mutate({ id: c.id, data: { allocation_key: v } })}
                    />
                  </Table.Td>
                  <Table.Td>{c.sort_order}</Table.Td>
                  <Table.Td>
                    <Button
                      size="compact-xs"
                      variant="light"
                      color="red"
                      onClick={() => deleteConfig.mutate(c.id)}
                    >
                      Entfernen
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>

          <Group align="flex-end">
            <Select
              label="Kostenart hinzufügen"
              placeholder="Kostenart"
              data={availableCats.map((c) => ({ value: String(c.id), label: c.name }))}
              value={catId}
              onChange={setCatId}
              w={280}
            />
            <Select
              label="Umlageschlüssel"
              data={ALLOCATION_KEYS}
              value={key}
              onChange={(v) => setKey(v ?? "WF")}
              w={220}
            />
            <NumberInput
              label="Sortierung"
              value={sortOrder}
              onChange={(v) => setSortOrder(String(v ?? ""))}
              w={120}
            />
            <Button onClick={add} disabled={!catId}>
              Hinzufügen
            </Button>
          </Group>
        </>
      )}
    </Stack>
  );
}
