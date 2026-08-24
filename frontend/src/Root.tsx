import { useState } from "react";
import { AppShell, Burger, Checkbox, Divider, Group, NavLink, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useTestData } from "./context/TestDataContext";
import { ObjectProvider } from "./context/ObjectContext";
import HelpModal, { type HelpContent } from "./components/HelpModal";
import { mieterwechselGuide, settlementGuide, stammdatenSetupGuide } from "./help/helpContent";
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
  const [guide, setGuide] = useState<HelpContent | null>(null);
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
          label="Abrechnung erstellen"
          description="Wiederkehrende Aufgaben"
          onClick={() => setGuide(settlementGuide)}
        />
        <NavLink
          label="Stammdaten – Erstsetup"
          description="Neues Objekt einrichten"
          onClick={() => setGuide(stammdatenSetupGuide)}
        />
        <NavLink
          label="Mieterwechsel"
          description="Ein-/Auszug erfassen"
          onClick={() => setGuide(mieterwechselGuide)}
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
          </Routes>
        </ObjectProvider>
      </AppShell.Main>

      <HelpModal opened={guide != null} onClose={() => setGuide(null)} content={guide ?? settlementGuide} />
    </AppShell>
  );
}
