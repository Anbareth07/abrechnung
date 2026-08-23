import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AllocationConfig, CostCategory, Property } from "../api/types";
import { ConfigsTab } from "./StammdatenPage";

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
  fmt: (v: unknown) => String(v),
  num: (v: unknown) => Number(v),
}));

// useCrud für Objekte und Kostenarten mocken
const state = vi.hoisted(() => ({
  properties: [] as Property[],
  categories: [] as CostCategory[],
}));

vi.mock("../hooks/useCrud", () => ({
  useCrud: (path: string) => ({
    list: {
      data: path === "/properties" ? state.properties : state.categories,
    },
    create: { mutate: vi.fn() },
    update: { mutate: vi.fn() },
    remove: { mutate: vi.fn() },
  }),
}));

let configState: AllocationConfig[] = [];

const config = (
  id: number,
  sortOrder: number,
  categoryName: string,
): AllocationConfig => ({
  id,
  property_id: 3,
  cost_category_id: id,
  allocation_key: "WF",
  sort_order: sortOrder,
  category_name: categoryName,
});

const renderTab = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <ConfigsTab />
      </MantineProvider>
    </QueryClientProvider>,
  );
};

const readRows = () =>
  [...document.querySelectorAll("table tbody tr")].map((tr) => {
    const cell = tr.querySelectorAll("td")[1];
    const input = cell?.querySelector("input");
    return (input?.value ?? cell?.textContent?.trim() ?? "").trim();
  });

describe("ConfigsTab", () => {
  beforeEach(() => {
    state.properties = [
      { id: 3, name: "Testobjekt", street: "", zip_code: "", city: "" },
    ];
    state.categories = [];
    configState = [
      config(1, 1, "Grundsteuer"),
      config(2, 2, "Trinkwasser"),
      config(3, 3, "Abfall"),
    ];
    api.get.mockReset();
    api.patch.mockReset();
    api.get.mockImplementation(async (url: string) => {
      if (url === "/allocation-configs") {
        return { data: [...configState].sort((a, b) => a.sort_order - b.sort_order) };
      }
      return { data: [] };
    });
    api.patch.mockImplementation(async (url: string, body: { sort_order?: number }) => {
      const m = url.match(/\/allocation-configs\/(\d+)/);
      if (m) {
        const id = Number(m[1]);
        configState = configState.map((c) => (c.id === id ? { ...c, ...body } : c));
      }
      return { data: {} };
    });
  });

  it("zeigt Hoch/Runter-Buttons und tauscht die Reihenfolge per ▼", async () => {
    const user = userEvent.setup();
    renderTab();

    await waitForRows(["Grundsteuer", "Trinkwasser", "Abfall"]);

    // ▼ auf der ersten Zeile → Grundsteuer und Trinkwasser tauschen
    const firstRow = screen.getByRole("row", { name: /Grundsteuer/ });
    await user.click(within(firstRow).getByRole("button", { name: "nach unten" }));

    // Nach Invalidierung/Refetch: Trinkwasser zuerst
    await waitForRows(["Trinkwasser", "Grundsteuer", "Abfall"]);
  });

  it("deaktiviert ▲ in der ersten und ▼ in der letzten Zeile", async () => {
    renderTab();

    await waitForRows(["Grundsteuer", "Trinkwasser", "Abfall"]);

    const rows = screen.getAllByRole("row").slice(1); // ohne Kopfzeile
    expect(within(rows[0]).getByRole("button", { name: "nach oben" })).toBeDisabled();
    expect(within(rows[rows.length - 1]).getByRole("button", { name: "nach unten" })).toBeDisabled();
  });

  it("benennt die Kostenart inline um (PATCH /cost-categories/{id})", async () => {
    const user = userEvent.setup();
    renderTab();

    await waitForRows(["Grundsteuer", "Trinkwasser", "Abfall"]);

    const firstRow = screen.getByRole("row", { name: /Grundsteuer/ });
    const nameInput = within(firstRow).getByRole("textbox", { name: "Kostenart" });
    await user.clear(nameInput);
    await user.type(nameInput, "Hausgeld");
    await user.keyboard("{Enter}");

    await vi.waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith("/cost-categories/1", { name: "Hausgeld" });
    });
    expect(api.patch).toHaveBeenCalledTimes(1); // Enter soll nur einmal speichern
  });

  it("verwirft die Umbenennung per Escape ohne PATCH", async () => {
    const user = userEvent.setup();
    renderTab();

    await waitForRows(["Grundsteuer", "Trinkwasser", "Abfall"]);

    const firstRow = screen.getByRole("row", { name: /Grundsteuer/ });
    const nameInput = within(firstRow).getByRole("textbox", { name: "Kostenart" });
    await user.clear(nameInput);
    await user.type(nameInput, "Hausgeld");
    await user.keyboard("{Escape}");

    expect(api.patch).not.toHaveBeenCalled();
    expect(nameInput).toHaveValue("Grundsteuer");
  });

  it("zeigt alle Objekte ohne Dropdown gruppiert an", async () => {
    state.properties = [
      { id: 2, name: "Objekt B", street: "", zip_code: "", city: "" },
      { id: 3, name: "Testobjekt", street: "", zip_code: "", city: "" },
    ];
    configState = [
      config(1, 1, "Grundsteuer"),
      config(2, 2, "Trinkwasser"),
      config(3, 3, "Abfall"),
      { ...config(4, 1, "Hausgeld"), property_id: 2 },
    ];
    renderTab();

    // Objekt B kommt alphabetisch zuerst, danach Testobjekt
    await waitForRows(["Hausgeld", "Grundsteuer", "Trinkwasser", "Abfall"]);

    // Objekt-Titel erscheinen direkt, kein „Objekt“-Dropdown nötig
    expect(screen.getByRole("heading", { name: "Testobjekt" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Objekt B" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Objekt")).not.toBeInTheDocument();
  });

  it("lässt sich im „Hinzufügen“-Feld tippen ohne Absturz und aktiviert den Button", async () => {
    const user = userEvent.setup();
    renderTab();

    await waitForRows(["Grundsteuer", "Trinkwasser", "Abfall"]);

    // Tippen darf keinen Render-Absturz auslösen (e.currentTarget nicht im Updater nutzen)
    const addInput = screen.getByLabelText("Kostenart (Name)");
    await user.type(addInput, "Hausgeld");

    expect(screen.getByRole("button", { name: "Hinzufügen" })).toBeEnabled();
    expect(screen.getByRole("heading", { name: "Testobjekt" })).toBeInTheDocument();
  });
});

// Kleiner Helfer: wartet, bis die Tabellenzeilen der erwarteten Reihenfolge entsprechen
async function waitForRows(expected: string[]) {
  await vi.waitFor(() => {
    expect(readRows()).toEqual(expected);
  });
}
