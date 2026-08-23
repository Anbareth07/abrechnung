import type { LeaseUnit, Property, Tenant } from "../api/types";

export const isTestProperty = (p: Property): boolean => Boolean(p.is_test);

/** Nur sichtbare Objekte (Testobjekte bei hideTest=true ausgeblendet). */
export const visibleProperties = (props: Property[], hideTest: boolean): Property[] =>
  hideTest ? props.filter((p) => !isTestProperty(p)) : props;

/** IDs der Testobjekte (für die Filterung von Einheiten/Mietern/Zählern). */
export const testPropertyIds = (props: Property[]): Set<number> =>
  new Set(props.filter(isTestProperty).map((p) => p.id));

export const visibleUnits = (units: LeaseUnit[], testIds: Set<number>): LeaseUnit[] =>
  units.filter((u) => !testIds.has(u.property_id));

export const visibleTenants = (
  tenants: Tenant[],
  units: LeaseUnit[],
  testIds: Set<number>,
): Tenant[] => {
  const visibleUnitIds = new Set(
    units.filter((u) => !testIds.has(u.property_id)).map((u) => u.id),
  );
  return tenants.filter((t) => visibleUnitIds.has(t.lease_unit_id));
};
