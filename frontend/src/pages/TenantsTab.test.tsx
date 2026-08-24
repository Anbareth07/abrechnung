import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LeaseUnit, MonthlyCost, Property, Tenant } from "../api/types";
import { TenantsTab } from "./StammdatenPage";

// Gemeinsamer Mock-State, der von der gemockten useCrud gelesen wird.
const state = vi.hoisted(() => ({
  properties: [] as Property[],
  units: [] as LeaseUnit[],
  tenants: [] as Tenant[],
}));

vi.mock("../hooks/useCrud", () => ({
  useCrud: (path: string) => {
    const data =
      path === "/properties"
        ? state.properties
        : path === "/lease-units"
          ? state.units
          : state.tenants;
    return {
      list: { data },
      create: { mutate: vi.fn() },
      update: { mutate: vi.fn() },
      remove: { mutate: vi.fn() },
    };
  },
}));

const prop = (id: number, name: string): Property => ({
  id,
  name,
  street: "",
  zip_code: "",
  city: "",
});

const unit = (id: number, propertyId: number, designation: string): LeaseUnit => ({
  id,
  property_id: propertyId,
  designation,
  living_area: 50,
  extra_area: 0,
});

const tenant = (
  id: number,
  unitId: number,
  name: string,
  moveOut: string | null = null,
  extra: Partial<Tenant> = {},
): Tenant => ({
  id,
  lease_unit_id: unitId,
  name,
  move_in: "2020-01-01",
  move_out: moveOut,
  monthly_advance: 100,
  phone: null,
  email: null,
  monthly_costs: [],
  ...extra,
});

const cost = (name: string, amount: number): MonthlyCost => ({ name, amount });

const renderTab = () =>
  render(
    <MantineProvider>
      <TenantsTab />
    </MantineProvider>,
  );

describe("TenantsTab", () => {
  beforeEach(() => {
    state.properties = [];
    state.units = [];
    state.tenants = [];
  });

  it("zeigt einen Hinweis, wenn keine Mieter existieren", () => {
    renderTab();
    expect(screen.getByText("Keine Mieter vorhanden.")).toBeInTheDocument();
  });

  it("gruppiert Mieter nach Objekt mit Überschrift", () => {
    state.properties = [prop(2, "Ulrichstraße 8"), prop(1, "Schermarweg 5")];
    state.units = [
      unit(1, 2, "Wohnung 1"),
      unit(2, 1, "Wohnung 1"),
      unit(3, 1, "Wohnung 2"),
    ];
    state.tenants = [
      tenant(1, 1, "Bauer"),
      tenant(2, 2, "Gronau"),
      tenant(3, 3, "Baumann"),
    ];
    renderTab();

    // Objekte alphabetisch (de) sortiert: Schermarweg vor Ulrichstraße
    const headings = screen.getAllByRole("heading", { level: 5 }).map((h) => h.textContent);
    expect(headings).toEqual(["Schermarweg 5", "Ulrichstraße 8"]);
    expect(screen.getByText("Bauer")).toBeInTheDocument();
    expect(screen.getByText("Gronau")).toBeInTheDocument();
    expect(screen.getByText("Baumann")).toBeInTheDocument();
  });

  it("zeigt ausgezogene Mieter ausgegraut (opacity 0.45)", () => {
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [tenant(1, 1, "Aktiv"), tenant(2, 1, "Alt", "2024-12-31")];
    renderTab();

    const oldRow = screen.getByRole("row", { name: /Alt/ });
    expect(oldRow).toHaveStyle({ opacity: "0.45" });

    const activeRow = screen.getByRole("row", { name: /Aktiv/ });
    expect(activeRow.style.opacity).toBe("");
  });

  it("sortiert aktive Mieter vor ausgezogenen", () => {
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    // "Alt" würde alphabetisch vor "Neu" stehen, ist aber ausgezogen
    state.tenants = [tenant(1, 1, "Alt", "2024-12-31"), tenant(2, 1, "Neu")];
    renderTab();

    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Neu");
    expect(rows[1]).toHaveTextContent("Alt");
  });

  it("setzt Vorauszahlungsänderungen automatisch auf den Monatsanfang", async () => {
    const user = userEvent.setup();
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [tenant(1, 1, "Bauer")];
    renderTab();

    await user.click(screen.getByRole("button", { name: "Ändern" }));
    await screen.findByRole("button", { name: "Speichern" });

    // 2. Vorauszahlungs-Zeitraum hinzufügen
    await user.click(screen.getByRole("button", { name: "+ Zeitraum hinzufügen" }));
    const inputs = screen.getAllByLabelText("Gültig ab");
    expect(inputs.length).toBe(2);

    // Mitte des Monats eintragen → wird auf den 1. des Monats gesetzt
    fireEvent.change(inputs[1], { target: { value: "2025-10-15" } });
    expect(inputs[1]).toHaveValue("2025-10-01");
  });

  it("blendet ausgezogene Mieter per Checkbox aus", async () => {
    const user = userEvent.setup();
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1"), unit(2, 1, "Wohnung 2")];
    state.tenants = [
      tenant(1, 1, "Aktiv"),
      tenant(2, 2, "Alt", "2024-12-31"),
    ];
    renderTab();

    // Vorher: beide sichtbar
    expect(screen.getByText("Alt")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Alte Mieter ausblenden"));

    // Nachher: ausgezogen ausgeblendet
    expect(screen.queryByText("Alt")).not.toBeInTheDocument();
    expect(screen.getByText("Aktiv")).toBeInTheDocument();
  });

  it("zeigt die Monatskosten-Summe inkl. Vorauszahlung", () => {
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [
      tenant(1, 1, "Mieter A", null, {
        monthly_advance: 100,
        monthly_costs: [cost("Heizkosten", 90.5), cost("Kaltmiete", 620)],
      }),
    ];
    renderTab();

    // Vorauszahlung 100 + Kaltmiete 620 + Heizkosten 90,5 = 810,50 (deutsches Format)
    expect(screen.getByText("810,50")).toBeInTheDocument();
    // Telefon/E-Mail erscheinen NICHT in der Übersicht
    expect(screen.queryByText("0170 123456")).not.toBeInTheDocument();
    expect(screen.queryByText("a@example.de")).not.toBeInTheDocument();
  });

  it("zeigt ohne Monatskosten mindestens die Vorauszahlung", () => {
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [tenant(1, 1, "Mieter A")]; // monthly_advance = 100
    renderTab();

    const row = screen.getByRole("row", { name: /Mieter A/ });
    // Nur Auszug zeigt „—"
    expect(within(row).getAllByText("—").length).toBe(1);
    // Monatskosten-Spalte (6. Zelle) zeigt die Vorauszahlung als Gesamtsumme
    const cells = within(row).getAllByRole("cell");
    expect(cells[5]).toHaveTextContent("100,00");
  });

  it("zeigt beim Hover auf die Monatskosten die Einzelposten inkl. Vorauszahlung absteigend sortiert", async () => {
    const user = userEvent.setup();
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [
      tenant(1, 1, "Mieter A", null, {
        monthly_advance: 100,
        monthly_costs: [
          cost("Warmwasser", 35),
          cost("Heizkosten", 90.5),
          cost("Kaltmiete", 620),
        ],
      }),
    ];
    renderTab();

    const sum = screen.getByText("845,50"); // 100 + 620 + 90,5 + 35
    await user.hover(sum);

    // Tooltip-Inhalt wird ans Ende des <body> gehängt (Name links, Betrag rechts)
    await screen.findByText("620,00 €");
    const body = document.body;
    expect(body.textContent).toContain("Kaltmiete");
    expect(body.textContent).toContain("Vorauszahlung");
    expect(body.textContent).toContain("Heizkosten");
    expect(body.textContent).toContain("Warmwasser");
    expect(body.textContent).toContain("620,00 €");
    expect(body.textContent).toContain("100,00 €");
    expect(body.textContent).toContain("90,50 €");
    expect(body.textContent).toContain("35,00 €");
    // Absteigend sortiert: Kaltmiete > Vorauszahlung > Heizkosten > Warmwasser
    const idx = (s: string) => body.textContent.indexOf(s);
    expect(idx("Kaltmiete")).toBeGreaterThan(-1);
    expect(idx("Kaltmiete")).toBeLessThan(idx("Vorauszahlung"));
    expect(idx("Vorauszahlung")).toBeLessThan(idx("Heizkosten"));
    expect(idx("Heizkosten")).toBeLessThan(idx("Warmwasser"));
  });

  it("zeigt beim Hover auf den Namen E-Mail und Telefon", async () => {
    const user = userEvent.setup();
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [
      tenant(1, 1, "Mieter A", null, { phone: "0170 123", email: "a@example.de" }),
    ];
    renderTab();

    await user.hover(screen.getByText("Mieter A"));

    // Tooltip öffnet asynchron → warten
    await screen.findByText(/E-Mail: a@example.de/);
    const body = document.body;
    expect(body.textContent).toContain("E-Mail: a@example.de");
    expect(body.textContent).toContain("Telefon: 0170 123");
  });

  it("zeigt beim Hover auf die Vorauszahlung die Historie der Zeiträume", async () => {
    const user = userEvent.setup();
    state.properties = [prop(1, "Objekt 1")];
    state.units = [unit(1, 1, "Wohnung 1")];
    state.tenants = [
      tenant(1, 1, "Mieter A", null, {
        monthly_advance: 180,
        advances: [
          { valid_from: "2020-01-01", amount: 100 },
          { valid_from: "2025-07-01", amount: 180 },
        ],
      }),
    ];
    renderTab();

    const row = screen.getByRole("row", { name: /Mieter A/ });
    const cells = within(row).getAllByRole("cell");
    // Innerhalb der Vorauszahlungs-Zelle (5. Spalte) den Wert hoveren
    await user.hover(within(cells[4]).getByText("180,00"));

    // Tooltip öffnet asynchron → warten
    await screen.findByText("180,00 €");
    const body = document.body;
    expect(body.textContent).toContain("ab 2025-07-01");
    expect(body.textContent).toContain("ab 2020-01-01");
    expect(body.textContent).toContain("180,00 €");
    expect(body.textContent).toContain("100,00 €");
    expect(screen.getByText("2 Zeiträume")).toBeInTheDocument();
  });
});
