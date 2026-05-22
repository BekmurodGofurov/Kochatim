import {
  LayoutDashboard,
  Database,
  ShoppingCart,
  Settings,
  ChevronRight,
  Sun,
  Moon,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useMemo } from "react";
import { useTheme } from "../../context/ThemeContext";
import { useDashboard } from "../../context/DashboardContext";

import "./Sidebar.scss";

export default function Sidebar() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { dashboardData } = useDashboard();

  const uId = dashboardData?.user?.u_id != null ? String(dashboardData.user.u_id) : null;

  const menu = useMemo(() => {
    return [
      { name: "Boshqaruv paneli", path: "/dashboard", icon: LayoutDashboard },
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
        <Link to="/" className="sidebar__logo">
          <img src="/img1.png" alt="Ko'chatim" />
        </Link>
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
          <span>{theme === "light" ? "Tungi" : "Kunduzgi"} rejim</span>
        </button>
      </div>

      <div className="sidebar__footer">
        <p className="sidebar__plan">Premium Reja</p>
        <a href="https://t.me/kochatim_bot" target="_blank" rel="noopener noreferrer" className="sidebar__support">
          Murojaat uchun: @kochatim_bot
        </a>
        <p className="sidebar__version">V2.2.0 build</p>
      </div>
    </aside>
  );
}
