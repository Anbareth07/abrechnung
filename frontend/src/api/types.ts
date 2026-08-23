export type Money = number | string;

export interface Property {
  id: number;
  name: string;
  street: string;
  zip_code: string;
  city: string;
  is_test?: boolean;
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
}

export interface TechemRecord {
  id: number;
  property_id: number;
  kind: string;
  invoice_date: string;
  quantity_kwh?: Money | null;
  gross_amount: Money;
  notes?: string | null;
  meta?: Record<string, unknown>;
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
