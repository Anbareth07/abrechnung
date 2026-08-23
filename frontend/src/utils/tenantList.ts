import type { LeaseUnit, MonthlyCost, Property, Tenant } from "../api/types";

/** Ein Mieter gilt als „alt", wenn er ein Auszugsdatum hat. */
export const isOldTenant = (t: Tenant): boolean => Boolean(t.move_out);

/** Summe der zusätzlichen Monatskosten eines Mieters. */
export const monthlyCostsTotal = (costs: MonthlyCost[] | undefined): number =>
  (costs ?? []).reduce((sum, c) => sum + Number(c.amount), 0);

/** Monatskosten nach Wert absteigend sortiert (für die Tooltip-Aufschlüsselung). */
export const sortedMonthlyCosts = (costs: MonthlyCost[] | undefined): MonthlyCost[] =>
  (costs ?? []).slice().sort((a, b) => Number(b.amount) - Number(a.amount));

export interface MonthlyBreakdownItem {
  name: string;
  amount: number;
}

/**
 * Monatliche Gesamtbelastung eines Mieters: aktuelle Vorauszahlung
 * + zusätzliche Monatskosten (Kaltmiete, Heizkosten, …).
 */
export const monthlyTotalWithAdvance = (t: Tenant): number =>
  Number(t.monthly_advance) + monthlyCostsTotal(t.monthly_costs);

/**
 * Aufschlüsselung der monatlichen Belastung: Vorauszahlung + Monatskosten,
 * nach Wert absteigend sortiert (für die Tooltip-Anzeige).
 */
export const monthlyBreakdown = (t: Tenant): MonthlyBreakdownItem[] => {
  const items: MonthlyBreakdownItem[] = [
    { name: "Vorauszahlung", amount: Number(t.monthly_advance) },
    ...(t.monthly_costs ?? []).map((c) => ({ name: c.name, amount: Number(c.amount) })),
  ];
  return items.sort((a, b) => b.amount - a.amount);
};

export interface AdvanceHistoryItem {
  valid_from: string;
  amount: number;
}

/**
 * Vorauszahlungs-Historie als Zeiträume (gültig ab → Betrag), neueste zuerst.
 * Ohne hinterlegte Zeiträume wird die aktuelle Vorauszahlung ab Einzug gelistet.
 */
export const advanceHistory = (t: Tenant): AdvanceHistoryItem[] => {
  if (t.advances && t.advances.length) {
    return t.advances
      .map((a) => ({ valid_from: a.valid_from, amount: Number(a.amount) }))
      .sort((a, b) => b.valid_from.localeCompare(a.valid_from));
  }
  return [{ valid_from: t.move_in, amount: Number(t.monthly_advance) }];
};

/** Vorhandene Kontaktdaten eines Mieters (für den Tooltip am Namen). */
export const contactInfo = (
  t: Tenant,
): { email?: string; phone?: string } => ({
  email: t.email ?? undefined,
  phone: t.phone ?? undefined,
});

export interface UnitOption {
  value: string;
  label: string;
}

/**
 * Mieteinheiten-Auswahl für den Mieter-Dialog: sortiert nach Objekt (Name)
 * und dann nach Wohnungs-Bezeichnung.
 */
export const unitOptions = (units: LeaseUnit[], properties: Property[]): UnitOption[] =>
  [...units]
    .map((u) => {
      const p = properties.find((pp) => pp.id === u.property_id);
      return {
        value: String(u.id),
        label: p ? `${p.name} · ${u.designation}` : u.designation,
      };
    })
    .sort((a, b) => a.label.localeCompare(b.label, "de"));

/**
 * Sortiert Mieter: aktive (ohne Auszug) zuerst, dann ausgezogene,
 * innerhalb der Gruppe nach Einheit (Bezeichnung) und Name.
 */
export const sortTenants = (
  tenants: Tenant[],
  unitDesignation: (leaseUnitId: number) => string,
): Tenant[] =>
  [...tenants].sort((a, b) => {
    if (!!a.move_out !== !!b.move_out) return a.move_out ? 1 : -1;
    const byUnit = unitDesignation(a.lease_unit_id).localeCompare(
      unitDesignation(b.lease_unit_id),
      "de",
    );
    return byUnit !== 0 ? byUnit : a.name.localeCompare(b.name, "de");
  });

export interface TenantGroup {
  property: Property;
  tenants: Tenant[];
}

/**
 * Gruppiert Mieter nach Objekt, sortiert Objekte nach Name und Mieter
 * (aktive zuerst). Mit `hideOld=true` werden ausgezogene Mieter ausgeblendet.
 */
export const groupTenantsByProperty = (
  properties: Property[],
  tenants: Tenant[],
  units: LeaseUnit[],
  hideOld: boolean,
): TenantGroup[] => {
  const unitDesignation = (id: number) =>
    units.find((u) => u.id === id)?.designation ?? "";

  return [...properties]
    .sort((a, b) => a.name.localeCompare(b.name, "de"))
    .map((p) => {
      let group = tenants.filter(
        (t) => units.find((u) => u.id === t.lease_unit_id)?.property_id === p.id,
      );
      group = sortTenants(group, unitDesignation);
      if (hideOld) group = group.filter((t) => !isOldTenant(t));
      return { property: p, tenants: group };
    })
    .filter((g) => g.tenants.length > 0);
};
