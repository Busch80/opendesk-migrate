import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.tsx";
import Dashboard from "./pages/Dashboard.tsx";
import Tenants from "./pages/Tenants.tsx";
import TenantDetail from "./pages/TenantDetail.tsx";
import Jobs from "./pages/Jobs.tsx";
import Audit from "./pages/Audit.tsx";
import Settings from "./pages/Settings.tsx";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="/tenants" element={<Tenants />} />
        <Route path="/tenants/:tenantId" element={<TenantDetail />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;
