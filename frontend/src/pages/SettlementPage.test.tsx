import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { FinalizedResult, Property, SettlementResult, TenantLine } from "../api/types";
import { TestDataProvider } from "../context/TestDataContext";
import { ObjectProvider } from "../context/ObjectContext";
import SettlementPage from "./SettlementPage";

// Mantine-Select durch natives <select> ersetzen (Dropdown in jsdom unzuverlässig)
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
  };
});

// Gemeinsamer API-Mock (axios-artige Antworten)
const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api,
  API_URL: "http://test.local",
  fmt: (v: unknown, digits = 2) =>
    Number(v).toLocaleString("de-DE", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
  num: (v: unknown) => Number(v),
}));

const state = vi.hoisted(() => ({
  properties: [] as Property[],
  settlement: null as SettlementResult | null,
  finalized: null as FinalizedResult | null,
}));

vi.mock("../hooks/useCrud", () => ({
  useCrud: () => ({
    list: { data: state.properties },
    create: { mutate: vi.fn() },
    update: { mutate: vi.fn() },
    remove: { mutate: vi.fn() },
  }),
}));

const tenantLine = (
  id: number,
  name: string,
  saldo: number,
  totalCosts: number,
  advanceTotal: number,
): TenantLine => ({
  tenant_id: id,
  name,
  lease_unit_id: id,
  designation: "Wohnung 1",
  living_area: 80,
  utility_area: 0,
  tenant_days: 365,
  time_factor: 1,
  advance_months: 12,
  period_start: "2025-01-01",
  period_end: "2025-12-31",
  breakdown: {},
  details: [],
  advance_breakdown: [
    { valid_from: "2025-01-01", valid_to: "2025-12-31", amount: 180, days: 365, months: 12 },
  ],
  total_costs: totalCosts,
  advance_total: advanceTotal,
  saldo,
});

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <TestDataProvider>
          <ObjectProvider>
            <SettlementPage />
          </ObjectProvider>
        </TestDataProvider>
      </MantineProvider>
    </QueryClientProvider>,
  );
};

describe("SettlementPage", () => {
  beforeEach(() => {
    localStorage.removeItem("abrechnung.selectedObject");
    vi.clearAllMocks();
    state.properties = [
      { id: 3, name: "Testobjekt", street: "", zip_code: "", city: "" },
    ];
    api.get.mockImplementation((url: string) => {
      if (url === "/properties") {
        return Promise.resolve({ data: state.properties });
      }
      if (url.endsWith("/completeness")) {
        return Promise.resolve({ data: [] });
      }
      if (url.endsWith("/finalized")) {
        if (state.finalized) {
          return Promise.resolve({ data: state.finalized });
        }
        return Promise.reject(new Error("Noch nicht finalisiert"));
      }
      return Promise.resolve({ data: state.settlement });
    });
  });

  it("zeigt bei Nachzahlung den Betrag ohne Minus", async () => {
    state.settlement = {
      property_id: 3,
      property_name: "Testobjekt",
      year: 2025,
      days_in_year: 365,
      total_wf: 200,
      total_nf: 0,
      category_lines: [],
      tenant_lines: [tenantLine(1, "Mieter Nachzahlung", 120.5, 2280.5, 2160)],
      water: null,
      water_total_cost: 0,
      water_price_per_m3: null,
      garden_water_cost: 0,
      unallocated_water: 0,
      warnings: [],
    };
    renderPage();

    fireEvent.change(screen.getByLabelText("Objekt"), { target: { value: "3" } });

    expect(await screen.findByText("Nachzahlung")).toBeInTheDocument();
    expect(screen.getByText("120,50 €")).toBeInTheDocument();
    expect(screen.queryByText("-120,50 €")).not.toBeInTheDocument();
  });

  it("zeigt bei Gutschrift den Betrag ohne Minus", async () => {
    state.settlement = {
      property_id: 3,
      property_name: "Testobjekt",
      year: 2025,
      days_in_year: 365,
      total_wf: 200,
      total_nf: 0,
      category_lines: [],
      tenant_lines: [tenantLine(1, "Mieter Gutschrift", -90.25, 2069.75, 2160)],
      water: null,
      water_total_cost: 0,
      water_price_per_m3: null,
      garden_water_cost: 0,
      unallocated_water: 0,
      warnings: [],
    };
    renderPage();

    fireEvent.change(screen.getByLabelText("Objekt"), { target: { value: "3" } });

    expect(await screen.findByText("Gutschrift")).toBeInTheDocument();
    expect(screen.getByText("90,25 €")).toBeInTheDocument();
    expect(screen.queryByText("-90,25 €")).not.toBeInTheDocument();
  });

  it("zeigt den finalisierten Snapshot in der Finalisiert-Ansicht", async () => {
    state.settlement = {
      property_id: 3,
      property_name: "Testobjekt",
      year: 2025,
      days_in_year: 365,
      total_wf: 200,
      total_nf: 0,
      category_lines: [],
      tenant_lines: [tenantLine(1, "Mieter Live", 100, 2200, 2100)],
      water: null,
      water_total_cost: 0,
      water_price_per_m3: null,
      garden_water_cost: 0,
      unallocated_water: 0,
      warnings: [],
    };
    state.finalized = {
      property_id: 3,
      property_name: "Testobjekt",
      year: 2025,
      status: "FINAL",
      computed_at: "2026-02-01T10:00:00",
      meta: {},
      category_names: { wohnungskosten: "Wohnungskosten" },
      tenant_lines: [
        {
          tenant_id: 1,
          name: "Mieter Snapshot",
          designation: "Wohnung 1",
          living_area: 80,
          utility_area: 0,
          tenant_days: 365,
          time_factor: 1,
          advance_months: 12,
          breakdown: { wohnungskosten: 2000 },
          total_costs: 2000,
          advance_total: 2100,
          saldo: -100,
        },
      ],
    };
    renderPage();

    fireEvent.change(screen.getByLabelText("Objekt"), { target: { value: "3" } });
    fireEvent.click(await screen.findByText("Finalisiert"));

    expect(await screen.findByText(/Mieter Snapshot/)).toBeInTheDocument();
    expect(screen.getByText("Wohnungskosten")).toBeInTheDocument();
    expect(screen.getAllByText("2.000,00 €").length).toBeGreaterThan(0);
    expect(screen.getByText("Gutschrift")).toBeInTheDocument();
    // Live-Mieter wird in der Finalisiert-Ansicht nicht angezeigt
    expect(screen.queryByText("Mieter Live")).not.toBeInTheDocument();
  });

  it("zeigt einen Hinweis, wenn noch nicht finalisiert", async () => {
    state.settlement = {
      property_id: 3,
      property_name: "Testobjekt",
      year: 2025,
      days_in_year: 365,
      total_wf: 200,
      total_nf: 0,
      category_lines: [],
      tenant_lines: [tenantLine(1, "Mieter Live", 100, 2200, 2100)],
      water: null,
      water_total_cost: 0,
      water_price_per_m3: null,
      garden_water_cost: 0,
      unallocated_water: 0,
      warnings: [],
    };
    state.finalized = null;
    renderPage();

    fireEvent.change(screen.getByLabelText("Objekt"), { target: { value: "3" } });
    fireEvent.click(await screen.findByText("Finalisiert"));

    expect(
      await screen.findByText(/Noch nicht finalisiert/),
    ).toBeInTheDocument();
  });
});
