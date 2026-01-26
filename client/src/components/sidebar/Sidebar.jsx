import {
  LayoutDashboard,
  Database,
  ShoppingCart,
  Settings,
  Leaf,
  ChevronRight,
  Sun,
  Moon,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useTheme } from "../../context/ThemeContext";

import "./Sidebar.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function apiGetMe() {
  const token = localStorage.getItem("session_token");
  if (!token) return null;

  const res = await fetch(`${API_BASE}/api/me`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json || json.ok !== true) return null;

  return json.data;
}

export default function Sidebar() {
  const location = useLocation();
  const [uId, setUId] = useState(null);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    let alive = true;

    (async () => {
      const me = await apiGetMe();
      if (!alive) return;
      setUId(me?.u_id != null ? String(me.u_id) : null);
    })();

    return () => {
      alive = false;
    };
  }, []);

  const menu = useMemo(() => {
    return [
      { name: "Dashboard", path: "/", icon: LayoutDashboard },
      { name: "Omborxona", path: `/u/${uId}/inventory`, icon: Database },
      { name: "Sotuvlar", path: "/sales", icon: ShoppingCart },
      { name: "Sozlamalar", path: "/settings", icon: Settings },
    ];
  }, [uId]);

  const isActive = (itemPath) => {
    if (itemPath.includes("/inventory")) {
      return location.pathname.includes("/inventory");
    }
    return location.pathname === itemPath;
  };

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">
          <Leaf size={24} />
        </div>
        <span className="sidebar__title">Ko'chatim</span>
      </div>

      <nav className="sidebar__menu">
        {menu.map((item) => {
          const active = isActive(item.path);
          const disabled = item.name === "Omborxona" && !uId;

          return (
            <Link
              key={item.name}
              to={disabled ? location.pathname : item.path}
              onClick={(e) => disabled && e.preventDefault()}
              className={[
                "sidebar__item",
                active && "is-active",
                disabled && "is-disabled",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div className="sidebar__item-left">
                <item.icon size={22} />
                <span>{item.name}</span>
              </div>

              {active && <ChevronRight size={18} />}
            </Link>
          );
        })}
      </nav>

      <div className="sidebar__theme-toggle">
        <button
          onClick={toggleTheme}
          className="sidebar__theme-btn"
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          {theme === "light" ? <Moon size={20} /> : <Sun size={20} />}
          <span>{theme === "light" ? "Tun" : "Kun"} mode</span>
        </button>
      </div>

      <div className="sidebar__footer">
        <p className="sidebar__plan">Premium Plan</p>
        <p className="sidebar__version">V1.2.3 build</p>
      </div>
    </aside>
  );
}