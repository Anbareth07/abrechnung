import { AppShell, Burger, Checkbox, Divider, Group, NavLink, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useTestData } from "./context/TestDataContext";
import { ObjectProvider } from "./context/ObjectContext";
import { mieterwechselGuide, settlementGuide, stammdatenSetupGuide } from "./help/helpContent";
import FaqPage from "./pages/FaqPage";
import HelpPage from "./pages/HelpPage";
import StammdatenPage from "./pages/StammdatenPage";
import InvoicesPage from "./pages/InvoicesPage";
import SettlementPage from "./pages/SettlementPage";
import StromPage from "./pages/StromPage";
import TechemPage from "./pages/TechemPage";
import WasserPage from "./pages/WasserPage";

const links = [
  { path: "/stammdaten", label: "Stammdaten" },
  { path: "/rechnungen", label: "Rechnungen" },
  { path: "/strom", label: "Strom" },
  { path: "/wasser", label: "Wasser" },
  { path: "/abrechnung", label: "Abrechnung" },
  { path: "/techem", label: "Techem" },
];

export default function Root() {
  const [opened, { toggle }] = useDisclosure();
  const navigate = useNavigate();
  const location = useLocation();
  const { hideTest, setHideTest } = useTestData();

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={3}>Nebenkostenabrechnung</Title>
          </Group>
          <Checkbox
            label="Testdaten ausblenden"
            checked={hideTest}
            onChange={(e) => setHideTest(e.currentTarget.checked)}
          />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        {links.map((l) => (
          <NavLink
            key={l.path}
            label={l.label}
            active={location.pathname.startsWith(l.path)}
            onClick={() => navigate(l.path)}
          />
        ))}
        <Divider my="sm" label="Anleitung" labelPosition="left" />
        <NavLink
          label="Häufige Fragen (FAQ)"
          description="Frage & Antwort"
          active={location.pathname.startsWith("/anleitung/faq")}
          onClick={() => navigate("/anleitung/faq")}
        />
        <NavLink
          label="Abrechnung erstellen"
          description="Wiederkehrende Aufgaben"
          active={location.pathname.startsWith("/anleitung/abrechnung")}
          onClick={() => navigate("/anleitung/abrechnung")}
        />
        <NavLink
          label="Stammdaten – Erstsetup"
          description="Neues Objekt einrichten"
          active={location.pathname.startsWith("/anleitung/stammdaten")}
          onClick={() => navigate("/anleitung/stammdaten")}
        />
        <NavLink
          label="Mieterwechsel"
          description="Ein-/Auszug erfassen"
          active={location.pathname.startsWith("/anleitung/mieterwechsel")}
          onClick={() => navigate("/anleitung/mieterwechsel")}
        />
      </AppShell.Navbar>

      <AppShell.Main>
        <ObjectProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/stammdaten" replace />} />
            <Route path="/stammdaten" element={<StammdatenPage />} />
            <Route path="/rechnungen" element={<InvoicesPage />} />
            <Route path="/strom" element={<StromPage />} />
            <Route path="/wasser" element={<WasserPage />} />
            <Route path="/abrechnung" element={<SettlementPage />} />
            <Route path="/techem" element={<TechemPage />} />
            <Route path="/anleitung/faq" element={<FaqPage />} />
            <Route path="/anleitung/abrechnung" element={<HelpPage content={settlementGuide} />} />
            <Route path="/anleitung/stammdaten" element={<HelpPage content={stammdatenSetupGuide} />} />
            <Route path="/anleitung/mieterwechsel" element={<HelpPage content={mieterwechselGuide} />} />
          </Routes>
        </ObjectProvider>
      </AppShell.Main>
    </AppShell>
  );
}
