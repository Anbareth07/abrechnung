import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { stammdatenSetupGuide, settlementGuide } from "../help/helpContent";
import HelpPage from "./HelpPage";

const renderPage = (content: Parameters<typeof HelpPage>[0]["content"]) =>
  render(
    <MantineProvider>
      <HelpPage content={content} />
    </MantineProvider>,
  );

describe("HelpPage", () => {
  it("rendert die Anleitung als Seite (Titel, Intro, Abschnitte)", () => {
    renderPage(stammdatenSetupGuide);

    expect(
      screen.getByRole("heading", { name: "Stammdaten – Erstkonfiguration" }),
    ).toBeInTheDocument();
    expect(screen.getByText("1. Objekt anlegen")).toBeInTheDocument();
    expect(screen.getByText(/Objekt mit Name und Adresse anlegen/)).toBeInTheDocument();
  });

  it("zeigt auch die wiederkehrenden Aufgaben der Abrechnung", () => {
    renderPage(settlementGuide);

    expect(
      screen.getByRole("heading", { name: "Abrechnung erstellen – wiederkehrende Aufgaben" }),
    ).toBeInTheDocument();
    expect(screen.getByText("2. Rechnungen eintragen (wiederkehrend)")).toBeInTheDocument();
  });
});
