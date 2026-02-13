import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  Outlet,
} from "react-router-dom";

import Sidebar from "./components/sidebar/Sidebar.jsx";
import Dashboard from "./pages/dashboard/Dashboard";
import Inventory from "./pages/inventory/Inventory";
import Sales from "./pages/sales/Sales.jsx";
import Settings from "./pages/settings/Settings.jsx";
import Login from "./pages/login/Login.jsx";
import Home from "./pages/home/Home.jsx";
import RequireAuth from "./auth/RequireAuth";
import { DashboardProvider } from "./context/DashboardContext";
import { ThemeProvider } from "./context/ThemeContext";

import "./App.scss";

function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-layout__content">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <Router>
        <DashboardProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route path="/" element={<Home />} />

            <Route element={<RequireAuth />}>
              <Route element={<AppLayout />}>
                <Route path="/dashboard" element={<Dashboard />} />

                <Route path="/u/:uId/inventory" element={<Inventory />} />
                <Route path="/u/:uId/inventory/group/:cId" element={<Inventory />} />
                <Route
                  path="/u/:uId/inventory/group/:cId/sort/:tId"
                  element={<Inventory />}
                />

                <Route path="/sales" element={<Sales />} />
                <Route path="/settings" element={<Settings />} />

                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Route>
          </Routes>
        </DashboardProvider>
      </Router>
    </ThemeProvider>
  );
}