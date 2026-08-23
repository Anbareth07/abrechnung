import { describe, expect, it } from "vitest";
import type { LeaseUnit, MonthlyCost, Property, Tenant } from "../api/types";
import {
  advanceHistory,
  groupTenantsByProperty,
  isOldTenant,
  monthlyBreakdown,
  monthlyCostsTotal,
  monthlyTotalWithAdvance,
  sortTenants,
  sortedMonthlyCosts,
  unitOptions,
} from "./tenantList";

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
): Tenant => ({
  id,
  lease_unit_id: unitId,
  name,
  move_in: "2020-01-01",
  move_out: moveOut,
  monthly_advance: 100,
});

const unitName = (units: LeaseUnit[]) => (unitId: number) =>
  units.find((u) => u.id === unitId)?.designation ?? "";

describe("isOldTenant", () => {
  it("ist alt, wenn ein Auszugsdatum gesetzt ist", () => {
    expect(isOldTenant(tenant(1, 1, "A", "2024-12-31"))).toBe(true);
  });

  it("ist aktiv, wenn kein Auszugsdatum gesetzt ist", () => {
    expect(isOldTenant(tenant(1, 1, "A"))).toBe(false);
    expect(isOldTenant(tenant(1, 1, "A", null))).toBe(false);
  });
});

describe("sortTenants", () => {
  it("sortiert aktive Mieter vor ausgezogenen", () => {
    const units = [unit(1, 1, "Wohnung 1"), unit(2, 1, "Wohnung 2")];
    const tenants = [
      tenant(1, 1, "Alt", "2024-12-31"),
      tenant(2, 2, "Neu"),
      tenant(3, 1, "Neu2"),
    ];
    const sorted = sortTenants(tenants, unitName(units));
    expect(sorted.map((t) => t.name)).toEqual(["Neu2", "Neu", "Alt"]);
  });

  it("sortiert innerhalb der Gruppe nach Einheit und Name", () => {
    const units = [unit(1, 1, "Wohnung 2"), unit(2, 1, "Wohnung 1")];
    const tenants = [
      tenant(1, 1, "Zeta"),
      tenant(2, 2, "Alpha"),
      tenant(3, 2, "Beta"),
    ];
    const sorted = sortTenants(tenants, unitName(units));
    // Wohnung 1 zuerst, darin Name; dann Wohnung 2
    expect(sorted.map((t) => t.name)).toEqual(["Alpha", "Beta", "Zeta"]);
  });

  it("lässt die Eingabe unverändert (neue Kopie)", () => {
    const units = [unit(1, 1, "Wohnung 1")];
    const tenants = [tenant(1, 1, "B"), tenant(2, 1, "A")];
    sortTenants(tenants, unitName(units));
    expect(tenants.map((t) => t.name)).toEqual(["B", "A"]);
  });
});

describe("monthlyCostsTotal", () => {
  it("summiert alle Monatskosten", () => {
    const costs: MonthlyCost[] = [
      { name: "Kaltmiete", amount: 620 },
      { name: "Heizkosten", amount: 90.5 },
      { name: "Warmwasser", amount: 35 },
    ];
    expect(monthlyCostsTotal(costs)).toBeCloseTo(745.5);
  });

  it("gibt 0 zurück, wenn keine Kosten vorhanden sind", () => {
    expect(monthlyCostsTotal(undefined)).toBe(0);
    expect(monthlyCostsTotal([])).toBe(0);
  });
});

describe("sortedMonthlyCosts", () => {
  it("sortiert nach Wert absteigend", () => {
    const costs: MonthlyCost[] = [
      { name: "Heizkosten", amount: 90 },
      { name: "Kaltmiete", amount: 620 },
      { name: "Warmwasser", amount: 35 },
    ];
    expect(sortedMonthlyCosts(costs).map((c) => c.name)).toEqual([
      "Kaltmiete",
      "Heizkosten",
      "Warmwasser",
    ]);
  });

  it("gibt eine leere Liste zurück, wenn keine Kosten vorhanden sind", () => {
    expect(sortedMonthlyCosts(undefined)).toEqual([]);
  });
});

describe("monthlyTotalWithAdvance", () => {
  it("summiert Vorauszahlung + Monatskosten", () => {
    const t: Tenant = {
      ...tenant(1, 1, "Mieter A"),
      monthly_advance: 200,
      monthly_costs: [
        { name: "Kaltmiete", amount: 620 },
        { name: "Heizkosten", amount: 90.5 },
      ],
    };
    expect(monthlyTotalWithAdvance(t)).toBeCloseTo(910.5);
  });

  it("liefert nur die Vorauszahlung, wenn keine Monatskosten existieren", () => {
    const t: Tenant = { ...tenant(1, 1, "Mieter A"), monthly_advance: 150 };
    expect(monthlyTotalWithAdvance(t)).toBeCloseTo(150);
  });

  it("liefert 0, wenn weder Vorauszahlung noch Monatskosten vorhanden sind", () => {
    const t: Tenant = { ...tenant(1, 1, "Mieter A"), monthly_advance: 0, monthly_costs: [] };
    expect(monthlyTotalWithAdvance(t)).toBe(0);
  });
});

describe("monthlyBreakdown", () => {
  it("enthält die Vorauszahlung und die Monatskosten, absteigend nach Wert", () => {
    const t: Tenant = {
      ...tenant(1, 1, "Mieter A"),
      monthly_advance: 100,
      monthly_costs: [
        { name: "Heizkosten", amount: 90.5 },
        { name: "Kaltmiete", amount: 620 },
        { name: "Warmwasser", amount: 35 },
      ],
    };
    expect(monthlyBreakdown(t)).toEqual([
      { name: "Kaltmiete", amount: 620 },
      { name: "Vorauszahlung", amount: 100 },
      { name: "Heizkosten", amount: 90.5 },
      { name: "Warmwasser", amount: 35 },
    ]);
  });

  it("liefert nur die Vorauszahlung, wenn keine Monatskosten existieren", () => {
    const t: Tenant = { ...tenant(1, 1, "Mieter A"), monthly_advance: 150 };
    expect(monthlyBreakdown(t)).toEqual([{ name: "Vorauszahlung", amount: 150 }]);
  });
});

describe("unitOptions", () => {
  const props = [prop(2, "Ulrichstraße 8"), prop(1, "Schermarweg 5")];
  const units = [
    unit(1, 2, "Wohnung 2"),
    unit(2, 2, "Wohnung 1"),
    unit(3, 1, "Wohnung 1"),
  ];

  it("sortiert nach Objekt (de) und dann nach Wohnung", () => {
    const options = unitOptions(units, props);
    expect(options.map((o) => o.label)).toEqual([
      "Schermarweg 5 · Wohnung 1",
      "Ulrichstraße 8 · Wohnung 1",
      "Ulrichstraße 8 · Wohnung 2",
    ]);
  });

  it("verwendet ohne Objekt nur die Bezeichnung", () => {
    const options = unitOptions([unit(1, 999, "Wohnung 1")], []);
    expect(options).toEqual([{ value: "1", label: "Wohnung 1" }]);
  });
});

describe("advanceHistory", () => {
  it("listet die Zeiträume neueste zuerst", () => {
    const t: Tenant = {
      ...tenant(1, 1, "Mieter A"),
      monthly_advance: 180,
      advances: [
        { valid_from: "2020-01-01", amount: 100 },
        { valid_from: "2025-07-01", amount: 180 },
      ],
    };
    expect(advanceHistory(t)).toEqual([
      { valid_from: "2025-07-01", amount: 180 },
      { valid_from: "2020-01-01", amount: 100 },
    ]);
  });

  it("fällt ohne Zeiträume auf Einzug + aktuelle Vorauszahlung zurück", () => {
    const t: Tenant = { ...tenant(1, 1, "Mieter A"), monthly_advance: 150 };
    expect(advanceHistory(t)).toEqual([{ valid_from: "2020-01-01", amount: 150 }]);
  });
});

describe("groupTenantsByProperty", () => {
  const props = [prop(1, "Objekt B"), prop(2, "Objekt A")];
  const units = [unit(1, 1, "Wohnung 1"), unit(2, 2, "Wohnung 1")];
  const tenants = [
    tenant(1, 1, "B-Alt", "2024-12-31"),
    tenant(2, 1, "B-Neu"),
    tenant(3, 2, "A-Neu"),
  ];

  it("gruppiert nach Objekt und sortiert Objekte alphabetisch", () => {
    const groups = groupTenantsByProperty(props, tenants, units, false);
    expect(groups.map((g) => g.property.name)).toEqual(["Objekt A", "Objekt B"]);
    expect(groups[0].tenants.map((t) => t.name)).toEqual(["A-Neu"]);
  });

  it("ignoriert Mieter ohne zugeordnete Einheit", () => {
    const stray = tenant(9, 999, "Verwaist");
    const groups = groupTenantsByProperty(props, [...tenants, stray], units, false);
    const names = groups.flatMap((g) => g.tenants.map((t) => t.name));
    expect(names).not.toContain("Verwaist");
  });

  it("blendet Objekte ohne Mieter aus", () => {
    const emptyProp = prop(3, "Objekt Leer");
    const groups = groupTenantsByProperty([...props, emptyProp], tenants, units, false);
    expect(groups.map((g) => g.property.name)).toEqual(["Objekt A", "Objekt B"]);
  });

  it("blendet mit hideOld=true ausgezogene Mieter aus, behält Reihenfolge", () => {
    const groups = groupTenantsByProperty(props, tenants, units, true);
    expect(groups[1].tenants.map((t) => t.name)).toEqual(["B-Neu"]);
  });

  it("zeigt mit hideOld=false auch ausgezogene Mieter (aktiv zuerst)", () => {
    const groups = groupTenantsByProperty(props, tenants, units, false);
    expect(groups[1].tenants.map((t) => t.name)).toEqual(["B-Neu", "B-Alt"]);
  });
});
