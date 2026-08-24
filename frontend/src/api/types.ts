export type Money = number | string;

export interface Property {
  id: number;
  name: string;
  street: string;
  zip_code: string;
  city: string;
  is_test?: boolean;
  strom_allocation_category_id?: number | null;
  wasser_trinkwasser_category_id?: number | null;
  wasser_schmutzwasser_category_id?: number | null;
  wasser_niederschlag_category_id?: number | null;
  wasser_versiegelte_flaeche?: Money | null;
  strom_unterzaehler_aktiv?: boolean;
  wasser_waschmaschinen_aktiv?: boolean;
  created_at?: string;
}

export interface LeaseUnit {
  id: number;
  property_id: number;
  designation: string;
  living_area: Money;
  extra_area: Money;
  utility_area?: Money;
}

export interface TenantAdvance {
  id?: number;
  valid_from: string;
  amount: Money;
}

export interface MonthlyCost {
  id?: number;
  name: string;
  amount: Money;
}

export interface Tenant {
  id: number;
  lease_unit_id: number;
  name: string;
  move_in: string;
  move_out: string | null;
  monthly_advance: Money;
  phone?: string | null;
  email?: string | null;
  advances?: TenantAdvance[];
  monthly_costs?: MonthlyCost[];
}

export interface CostCategory {
  id: number;
  property_id: number;
  code: string;
  name: string;
  default_allocation_key: string;
  is_active: boolean;
}

export interface AllocationConfig {
  id: number;
  property_id: number;
  cost_category_id: number;
  allocation_key: string;
  sort_order: number;
  category_code?: string;
  category_name?: string;
}

export interface InvoiceItem {
  id?: number;
  invoice_id?: number;
  from_date: string;
  to_date: string;
  description?: string | null;
  quantity?: Money | null;
  unit?: string | null;
  unit_price?: Money | null;
  gross_amount: Money;
  meta?: Record<string, unknown>;
}

export interface Invoice {
  id: number;
  property_id: number;
  cost_category_id: number;
  kind?: string | null;
  valid_from?: string | null;
  annual_amount?: Money | null;
  lease_unit_id?: number | null;
  invoice_number?: string | null;
  supplier?: string | null;
  description?: string | null;
  issue_date?: string | null;
  period_start: string;
  period_end: string;
  gross_amount?: Money | null;
  anteil_zaehler?: number | null;
  anteil_nenner?: number | null;
  meta?: Record<string, unknown>;
  items: InvoiceItem[];
}

export interface Meter {
  id: number;
  property_id: number | null;
  lease_unit_id: number | null;
  name: string;
  meter_type: string;
  unit: string;
}

export interface MeterReading {
  id: number;
  meter_id: number;
  reading_date: string;
  value: Money;
  vor_zaehlerwechsel?: boolean;
  neuer_zaehler_start?: Money;
}

export interface TechemSheet {
  id?: number;
  property_id: number;
  von: string;
  bis: string;
  strom_kwh: Money;
  strom_netto: Money;
  strom_vat: Money;
  strom_brutto: Money;
  gas_kwh: Money;
  gas_cost: Money;
  maintenance_cost: Money;
  chimney_cost: Money;
  notes?: string | null;
}

export interface WasserPrice {
  id: number;
  property_id: number;
  kind: string;
  valid_from: string;
  valid_to: string;
  amount: Money;
  vat_rate: Money;
}

export interface WasserReading {
  id: number;
  property_id: number;
  reading_date: string;
  value: Money;
  vor_zaehlerwechsel?: boolean;
  neuer_zaehler_start?: Money;
}

export interface WasserPosition {
  art: string;
  von: string;
  bis: string;
  einheit?: string;
  satz_einheit?: string;
  menge: number;
  satz: number;
  vat_rate: number;
  netto: number;
  vat: number;
  brutto: number;
}

export interface WasserBerechnung {
  property_id: number;
  von: string;
  bis: string;
  plan?: "A" | "B";
  hauptzaehler: { start_reading: number; end_reading: number; consumption: number } | null;
  verbrauch: number;
  versiegelte_flaeche?: number | null;
  positionen: WasserPosition[];
  summen: { netto: number; vat: number; brutto: number };
}

export interface CategoryLine {
  code: string;
  name: string;
  allocation_key: string;
  year_cost: number;
}

export interface WaterResult {
  total_consumption: number;
  garden_consumption: number;
  meter_consumptions: unknown[];
  warnings: string[];
}

export interface CategoryInfoLine {
  type: "head" | "row" | "total" | "hinweis";
  label: string;
  menge?: string | null;
  netto?: string | null; // Nettobetrag (ohne MwSt)
  vat?: string | null; // MwSt-Betrag
  vat_rate?: number | null; // MwSt-Satz in %
  betrag?: string | null; // Bruttobetrag (inkl. MwSt)
}

export interface CategoryShare {
  code: string;
  name: string;
  allocation_key: string;
  year_cost: number;
  basis_label: string;
  basis_total: number | null;
  basis_share: number | null;
  days: number;
  amount: number;
  info?: CategoryInfoLine[]; // strukturierte Hover-Info (Berechnung/Rechnungen)
}

export interface AdvanceSegment {
  valid_from: string;
  valid_to: string;
  amount: number;
  days: number;
  months: number;
}

export interface TenantLine {
  tenant_id: number;
  name: string;
  lease_unit_id: number;
  designation: string;
  living_area: number;
  utility_area: number;
  tenant_days: number;
  time_factor: number;
  advance_months: number;
  period_start: string;
  period_end: string;
  breakdown: Record<string, number>;
  details: CategoryShare[];
  advance_breakdown: AdvanceSegment[];
  total_costs: number;
  advance_total: number;
  saldo: number;
}

export interface SettlementResult {
  property_id: number;
  property_name: string;
  year: number;
  days_in_year: number;
  total_wf: number;
  total_nf: number;
  category_lines: CategoryLine[];
  tenant_lines: TenantLine[];
  water: WaterResult | null;
  water_total_cost: number;
  water_price_per_m3: number | null;
  garden_water_cost: number;
  unallocated_water: number;
  warnings: string[];
}

export interface MissingItem {
  kind: string;
  label: string;
  detail: string;
  category_id?: number | null;
}

export interface NoInvoiceFlag {
  id: number;
  property_id: number;
  cost_category_id: number;
  year: number;
  category_name?: string;
}

export interface FinalizedTenantLine {
  tenant_id: number;
  name: string;
  designation: string;
  living_area: number;
  utility_area: number;
  tenant_days: number;
  time_factor: number;
  advance_months: number;
  breakdown: Record<string, number>;
  total_costs: number;
  advance_total: number;
  saldo: number;
}

export interface FinalizedResult {
  property_id: number;
  property_name: string;
  year: number;
  status: string;
  computed_at: string | null;
  meta: Record<string, unknown>;
  category_names: Record<string, string>;
  tenant_lines: FinalizedTenantLine[];
}

export interface StromPrice {
  id: number;
  property_id: number;
  kind: string; // GRUNDGEBUEHR | ARBEITSPREIS | STROMSTEUER
  valid_from: string;
  valid_to: string;
  amount: number;
  vat_rate: number;
}

export interface StromReading {
  id: number;
  property_id: number;
  role: string; // HAUPTZAEHLER | UNTERZAEHLER
  reading_date: string;
  value: number;
  vor_zaehlerwechsel?: boolean;
  neuer_zaehler_start?: Money;
}

export interface StromMeterResult {
  start_reading: number;
  end_reading: number;
  consumption: number;
}

export interface StromPosition {
  art: string;
  von: string;
  bis: string;
  menge: number;
  satz: number;
  vat_rate: number;
  netto: number;
  vat: number;
  brutto: number;
}

export interface StromBerechnung {
  property_id: number;
  von: string;
  bis: string;
  hauptzaehler: StromMeterResult | null;
  unterzaehler: StromMeterResult | null;
  netto_verbrauch: number;
  positionen: StromPosition[];
  summen: { netto: number; vat: number; brutto: number };
}

