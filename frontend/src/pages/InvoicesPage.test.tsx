import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CostCategory, Invoice, LeaseUnit, Property } from "../api/types";
import InvoicesPage from "./InvoicesPage";

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

const state = vi.hoisted(() => ({
  properties: [] as Property[],
  cats: [] as CostCategory[],
  units: [] as LeaseUnit[],
  invoices: [] as Invoice[],
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
            : state.invoices;
    return {
      list: { data },
      create: { mutate: vi.fn() },
      update: { mutate: vi.fn() },
      remove: { mutate: vi.fn() },
    };
  },
}));

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api,
  fmt: (v: unknown) => String(v),
  num: (v: unknown) => Number(v),
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

describe("InvoicesPage Rechnungsart", () => {
  beforeEach(() => {
    state.properties = [{ id: 3, name: "Testobjekt", street: "", zip_code: "", city: "" }];
    state.cats = [];
    state.units = [{ id: 7, property_id: 3, designation: "Wohnung 1", living_area: 50, extra_area: 0 }];
    state.invoices = [];
    api.post.mockReset();
    api.post.mockImplementation(async (url: string) => {
      if (url === "/cost-categories") {
        return { data: { id: 99, property_id: 3, code: "grundsteuer", name: "Grundsteuer" } };
      }
      return { data: {} };
    });
  });

  it("zeigt Grundsteuer-Layout mit gültig ab + Jahresbetrag und erzeugt Kostenart automatisch", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    await user.selectOptions(screen.getByLabelText("Rechnungsart"), "GRUNDSTEUER");

    await vi.waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/cost-categories", {
        property_id: 3,
        name: "Grundsteuer",
      });
    });

    // Grundsteuer-Layout statt Standard-Layout
    expect(screen.getByLabelText("Gültig ab (Bescheid)")).toBeInTheDocument();
    expect(screen.getByLabelText("Jahresbetrag (€)")).toBeInTheDocument();
    expect(screen.queryByLabelText("Leistung von")).not.toBeInTheDocument();
    expect(screen.queryByText("Positionen / Zeitabschnitte")).not.toBeInTheDocument();
  });

  it("zeigt bei Wasser das Standard-Layout mit Leistungszeitraum", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    await user.selectOptions(screen.getByLabelText("Rechnungsart"), "WASSER");

    await vi.waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/cost-categories", { property_id: 3, name: "Wasser" });
    });

    expect(screen.getByLabelText("Leistung von")).toBeInTheDocument();
    expect(screen.getByText("Positionen / Zeitabschnitte")).toBeInTheDocument();
    expect(screen.queryByLabelText("Gültig ab (Bescheid)")).not.toBeInTheDocument();
  });

  it("zeigt bei Schornsteinfeger den Geltungsbereich (Objekt/Wohneinheit)", async () => {
    const user = userEvent.setup();
    renderPage();
    await openNew(user);

    await user.selectOptions(screen.getByLabelText("Objekt"), "3");
    await user.selectOptions(screen.getByLabelText("Rechnungsart"), "SCHORNSTEINFEGER");

    await vi.waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/cost-categories", {
        property_id: 3,
        name: "Schornsteinfeger",
      });
    });

    expect(screen.getByLabelText("Geltungsbereich")).toBeInTheDocument();

    // Wohneinheit wählen → Einheiten-Auswahl erscheint
    await user.selectOptions(screen.getByLabelText("Geltungsbereich"), "WOHNEINHEIT");
    expect(screen.getByLabelText("Wohneinheit")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Wohnung 1" })).toBeInTheDocument();
  });
});
