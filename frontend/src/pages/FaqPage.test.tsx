import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import FaqPage from "./FaqPage";

const renderPage = () =>
  render(
    <MemoryRouter>
      <MantineProvider>
        <FaqPage />
      </MantineProvider>
    </MemoryRouter>,
  );

describe("FaqPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });  it("zeigt die Fragen und klappt die Antwort per Klick auf", async () => {
    const user = userEvent.setup();
    renderPage();

    const question = screen.getByText("Ich habe eine neue Stromrechnung. Was ist zu tun?");
    expect(question).toBeInTheDocument();

    // Antwort ist anfangs eingeklappt (nicht im DOM)
    expect(screen.queryByText(/Die Stromrechnung wird NICHT über/)).not.toBeInTheDocument();

    await user.click(question);

    expect(await screen.findByText(/Die Stromrechnung wird NICHT über „Rechnungen“ erfasst/)).toBeInTheDocument();
  });

  it("enthält eine Frage zu Gutschriften/Rückerstattungen", () => {
    renderPage();
    expect(screen.getByText(/Rückerstattung\/Gutschrift/)).toBeInTheDocument();
  });

  it("öffnet immer nur eine Frage gleichzeitig", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Ich habe eine neue Stromrechnung. Was ist zu tun?"));
    expect(await screen.findByText(/Die Stromrechnung wird NICHT über „Rechnungen“ erfasst/)).toBeInTheDocument();

    // Zweite Frage öffnen → die erste wird geschlossen
    await user.click(screen.getByText(/z\. B\. Garten oder Versicherung/));
    expect(await screen.findByText(/Wähle die passende Kostenstelle \(z\. B\. Garten\/Pflege oder Versicherung\)/)).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.queryByText(/Die Stromrechnung wird NICHT über „Rechnungen“ erfasst/),
      ).not.toBeInTheDocument(),
    );
  });

  it("bietet einen direkten Link zur zugehörigen Seite", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Ich habe eine neue Stromrechnung. Was ist zu tun?"));

    const link = await screen.findByRole("link", { name: /Zur Strom-Seite/ });
    expect(link).toHaveAttribute("href", "/strom");
  });

  it("verlinkt eine normale Rechnung auf die Rechnungen-Seite", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText(/z\. B\. Garten oder Versicherung/));

    const link = await screen.findByRole("link", { name: /Zur Rechnungen-Seite/ });
    expect(link).toHaveAttribute("href", "/rechnungen");
  });

  it("verlinkt bei selbstabgelesenen Zählerständen Strom und Wasser", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText(/selbstabgelesene Zählerstände/));

    expect(await screen.findByRole("link", { name: /Zur Strom-Seite/ })).toHaveAttribute("href", "/strom");
    expect(screen.getByRole("link", { name: /Zur Wasser-Seite/ })).toHaveAttribute("href", "/wasser");
  });

  it("behält aufgeklappte Fragen beim erneuten Öffnen (Zurück-Navigation)", async () => {
    const user = userEvent.setup();
    const { unmount } = renderPage();

    await user.click(screen.getByText("Ich habe eine neue Stromrechnung. Was ist zu tun?"));
    expect(await screen.findByText(/Die Stromrechnung wird NICHT über „Rechnungen“ erfasst/)).toBeInTheDocument();

    // Weg navigieren (Seite wird unmountet) und zurückkehren (erneutes Mounten)
    unmount();
    renderPage();

    // Die vorher aufgeklappte Frage ist wieder geöffnet
    expect(await screen.findByText(/Die Stromrechnung wird NICHT über „Rechnungen“ erfasst/)).toBeInTheDocument();
  });
});
