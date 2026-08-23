import { AppShell, Burger, Checkbox, Group, NavLink, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useTestData } from "./context/TestDataContext";
import StammdatenPage from "./pages/StammdatenPage";
import InvoicesPage from "./pages/InvoicesPage";
import MetersPage from "./pages/MetersPage";
import SettlementPage from "./pages/SettlementPage";
import TechemPage from "./pages/TechemPage";

const links = [
  { path: "/stammdaten", label: "Stammdaten" },
  { path: "/rechnungen", label: "Rechnungen" },
  { path: "/zaehler", label: "Zähler & Stände" },
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
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Navigate to="/stammdaten" replace />} />
          <Route path="/stammdaten" element={<StammdatenPage />} />
          <Route path="/rechnungen" element={<InvoicesPage />} />
          <Route path="/zaehler" element={<MetersPage />} />
          <Route path="/abrechnung" element={<SettlementPage />} />
          <Route path="/techem" element={<TechemPage />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
