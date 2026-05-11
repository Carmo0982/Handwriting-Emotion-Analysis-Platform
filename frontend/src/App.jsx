import { useMemo, useState } from "react";

import Dashboard from "./components/dashboard/Dashboard.jsx";
import AppShell from "./components/layout/AppShell.jsx";
import { initialHistory, tenants } from "./data/mockData.js";
import { useThemeMode } from "./hooks/useThemeMode.js";

export default function App() {
  const { mode, toggleMode } = useThemeMode();
  const [tenantId, setTenantId] = useState(tenants[0].id);
  const [history, setHistory] = useState(initialHistory);

  const tenant = useMemo(
    () => tenants.find((item) => item.id === tenantId) ?? tenants[0],
    [tenantId],
  );

  const tenantHistory = useMemo(
    () => history.filter((item) => item.tenantId === tenant.id),
    [history, tenant.id],
  );

  function handleAnalysisComplete(result) {
    setHistory((items) => [result, ...items].slice(0, 10));
  }

  return (
    <AppShell
      mode={mode}
      tenant={tenant}
      tenants={tenants}
      onTenantChange={setTenantId}
      onToggleMode={toggleMode}
    >
      <Dashboard
        history={tenantHistory}
        tenant={tenant}
        onAnalysisComplete={handleAnalysisComplete}
      />
    </AppShell>
  );
}
