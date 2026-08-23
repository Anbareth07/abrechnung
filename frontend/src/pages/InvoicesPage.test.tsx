import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AllocationConfig, CostCategory, Invoice, LeaseUnit, Property } from "../api/types";
import InvoicesPage from "./InvoicesPage";

// Mantine-Select/NumberInput durch native Elemente ersetzen (jsdom-unzuverlässig)
vi.mock("@mantine/core", async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    Select: (props: Record<string, unknown>) => {
      const data = (props.data as { value: string; label: string }[] | undefined) ?? [];
      const value = (props.value as string | null | undefined) ?? "";
      return (
        <select
          aria-label={props.label as string | undefined}
          value={value}
          onChange={(e) => (props.onChange as (v: string | null) => void)?.(e.target.value)}
        >
          {data.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      );
    },
    NumberInput: (props: Record<string, unknown>) => (
      <input
        aria-label={props.label as string | undefined}
        value={props.value as string | undefined}
        onChange={(e) => (props.onChange as (v: string | number | null) => void)?.(e.target.value)}
      />
    ),
  };
});

const state = vi.hoisted(() => ({
  properties: [] as Property[],
  cats: [] as CostCategory[],
  units: [] as LeaseUnit[],
  configs: [] as AllocationConfig[],
  invoices: [] as Invoice[],
}));

const crudMocks = vi.hoisted(() => ({
  create: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("../hooks/useCrud", () => ({
  useCrud: (path: string) => {
    const data =
      path === "/properties"
        ? state.properties
        : path === "/cost-categories"
          ? state.cats
          : path === "/lease-units"
            ? state.units
            : path === "/allocation-configs"
              ? state.configs
              : state.invoices;
    return {
      list: { data },
      create: {
        mutate: (payload: unknown, opts?: { onSuccess?: () => void }) => {
          crudMocks.create(payload);
          opts?.onSuccess?.();
        },
      },
      update: { mutate: crudMocks.update },
      remove: { mutate: crudMocks.remove },
    };
  },
}));

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <InvoicesPage />
      </MantineProvider>
    </QueryClientProvider>,
  );
};

const openNew = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getByRole("button", { name: "Neue Rechnung" }));
  await screen.findByRole("button", { name: "Speichern" });
};

describe("InvoicesPage generische Rechnung", () => {
  beforeEach(() => {
    state.properties = [{ id: 3, name: "Testobjekt", street: "", zip_code: "", city: "" }];
    state.cats = [
      { id: 10, property_id: 3, code: "grundsteuer", name: "Grundsteuer", default_allocation_key: "NF", is_active: true },
      { id: 11, property_id: 3, code: "wohnungskosten", name: "Wohnungskosten", default_allocation_key: "WOHNUNG", is_active: true },
    ];
    state.units = [{ id: 7, property_id: 3, designation: "Wohnung 1", living_area: 50, extra_area: 0 }];
    state.configs = [
      { id: 1, property_id: 3, cost_category_id: 10, allocation_key: "NF", sort_order: 1 },
      { id: 2, property_id: 3, cost_category_id: 11, allocation_key: "WOHNUNG", sort_order: 2 },
    ];
    state.invoices = [];
    crudMocks.create.mockReset();
  });

  it("erfasst eine generische Rechnung (Objekt, Jahr, Kostenstelle, Titel, Summe)", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    await user.selectOptions(screen.getByLabelText("Kostenstelle"), "10");
    await user.type(screen.getByLabelText("Titel"), "Grundsteuer 2025");
    await user.type(screen.getByLabelText("Summe (€)"), "1200");

    await user.click(screen.getByRole("button", { name: "Speichern" }));

    const year = String(new Date().getFullYear() - 1);
    expect(crudMocks.create).toHaveBeenCalledWith(
      expect.objectContaining({
        property_id: 3,
        cost_category_id: 10,
        period_start: `${year}-01-01`,
        period_end: `${year}-12-31`,
        description: "Grundsteuer 2025",
        items: [
          {
            from_date: `${year}-01-01`,
            to_date: `${year}-12-31`,
            description: "Grundsteuer 2025",
            gross_amount: "1200",
          },
        ],
      }),
    );
  });

  it("verlangt bei Kostenstelle 'Wohnung' die Wohnungsauswahl", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    // Grundsteuer (NF) → keine Wohnungsauswahl
    await user.selectOptions(screen.getByLabelText("Kostenstelle"), "10");
    expect(screen.queryByLabelText("Wohnung (je Wohnung)")).not.toBeInTheDocument();

    // Wohnungskosten (WOHNUNG) → Wohnungsauswahl erscheint und ist Pflicht
    await user.selectOptions(screen.getByLabelText("Kostenstelle"), "11");
    expect(screen.getByLabelText("Wohnung (je Wohnung)")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Wohnung 1" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Titel"), "Schornstein");
    await user.type(screen.getByLabelText("Summe (€)"), "120");
    // Ohne Wohnung → Speichern deaktiviert
    expect(screen.getByRole("button", { name: "Speichern" })).toBeDisabled();

    // Wohnung wählen → Speichern möglich
    await user.selectOptions(screen.getByLabelText("Wohnung (je Wohnung)"), "7");
    expect(screen.getByRole("button", { name: "Speichern" })).toBeEnabled();
  });

  it("verlangt Kostenstelle, Titel und Summe zum Speichern", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    // Ohne Auswahl/Felder → Speichern deaktiviert
    expect(screen.getByRole("button", { name: "Speichern" })).toBeDisabled();

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    await user.selectOptions(screen.getByLabelText("Kostenstelle"), "10");
    expect(screen.getByRole("button", { name: "Speichern" })).toBeDisabled();

    await user.type(screen.getByLabelText("Titel"), "Grundsteuer");
    await user.type(screen.getByLabelText("Summe (€)"), "1200");
    expect(screen.getByRole("button", { name: "Speichern" })).toBeEnabled();
  });

  it("lässt den Dialog mit 'offen lassen' geöffnet und setzt Titel/Summe/Kommentar zurück", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    await user.selectOptions(screen.getByLabelText("Kostenstelle"), "10");
    await user.type(screen.getByLabelText("Titel"), "Garten 1");
    await user.type(screen.getByLabelText("Summe (€)"), "150");
    await user.type(screen.getByLabelText("Kommentar (optional)"), "Notiz");

    await user.click(screen.getByRole("checkbox", { name: /Dialog offen lassen/ }));
    await user.click(screen.getByRole("button", { name: "Speichern" }));

    expect(crudMocks.create).toHaveBeenCalledTimes(1);
    // Dialog bleibt offen
    expect(screen.getByRole("button", { name: "Speichern" })).toBeInTheDocument();
    // Titel/Summe/Kommentar sind geleert
    expect(screen.getByLabelText("Titel")).toHaveValue("");
    expect(screen.getByLabelText("Summe (€)")).toHaveValue("");
    expect(screen.getByLabelText("Kommentar (optional)")).toHaveValue("");
    // Objekt und Kostenstelle bleiben vorbelegt
    expect(screen.getByLabelText("Objekt")).toHaveValue("3");
    expect(screen.getByLabelText("Kostenstelle")).toHaveValue("10");
  });

  it("klont eine Rechnung für das Folgejahr mit vorbelegten Feldern", async () => {
    const user = userEvent.setup();
    const year = String(new Date().getFullYear() - 1);
    const next = String(Number(year) + 1);
    state.invoices = [
      {
        id: 5,
        property_id: 3,
        cost_category_id: 10,
        period_start: `${year}-01-01`,
        period_end: `${year}-12-31`,
        description: "Grundsteuer 2025",
        gross_amount: "1200",
        items: [
          { from_date: `${year}-01-01`, to_date: `${year}-12-31`, gross_amount: "1200" },
        ],
        meta: { kommentar: "Notiz" },
      },
    ];
    renderPage();

    await user.click(screen.getByRole("button", { name: "Klonen" }));
    await screen.findByRole("button", { name: "Speichern" });

    // Felder vorbelegt, Jahr = Folgejahr
    expect(screen.getByLabelText("Objekt")).toHaveValue("3");
    expect(screen.getByLabelText("Jahr")).toHaveValue(next);
    expect(screen.getByLabelText("Kostenstelle")).toHaveValue("10");
    expect(screen.getByLabelText("Titel")).toHaveValue("Grundsteuer 2025");
    expect(screen.getByLabelText("Summe (€)")).toHaveValue("1200");
    expect(screen.getByLabelText("Kommentar (optional)")).toHaveValue("Notiz");
  });
});
