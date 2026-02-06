// src/pages/Settings.jsx
import React, { useEffect, useState } from "react";
import { User, Shield, Bot, Smartphone, LogOut, Info, Moon, Sun } from "lucide-react";

import Loader from "../../components/loader/Loader.jsx";
import { useDashboard } from "../../context/DashboardContext";
import { useTheme } from "../../context/ThemeContext";
import { getSessionToken } from "../../api/https";
import "./Settings.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);

    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");

    return `${hours}:${minutes} ${day}.${month}.${year}`;
  } catch {
    return String(value);
  }
}

export default function Settings() {
  const { dashboardData, loading: pageLoading, error: pageError } = useDashboard();
  const { theme, toggleTheme } = useTheme();

  const me = dashboardData?.user;

  // Agar contextdan error yoki loading kelsa
  if (pageLoading || (!dashboardData && getSessionToken())) return <Loader text="Yuklanmoqda..." />;
  if (pageError) return <Loader text={pageError} />;

  const handleLogout = () => {
    localStorage.removeItem("session_token");
    window.location.href = "/login";
  };


  const name = me?.u_name || "-";
  const username = me?.u_username ? `@${me.u_username}` : "-";
  const phone = me?.u_phone || "-";
  const userId = me?.u_id != null ? String(me.u_id) : "-";
  const joinedAt = formatDate(me?.added_at);

  return (
    <div className="settingsPage">
      <div className="leftColumn">
        <div className="card profileCard">
          <div className="profileHeader">
            <div className="avatarCircle">
              {me?.u_photo ? (
                <img
                  src={`${API_BASE}/api/img/${me.u_photo}`}
                  alt={name}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    borderRadius: "50%",
                  }}
                />
              ) : (
                <User size={40} />
              )}
            </div>

            <div>
              <h2 className="profileTitle">{name}</h2>
              <p className="profileSubtitle">{username}</p>
            </div>
          </div>

          <div className="profileGrid">
            <div>
              <label className="fieldLabel">Telefon raqam</label>
              <div className="readOnlyField">+{phone}</div>
            </div>

            <div>
              <label className="fieldLabel">Telegram ID</label>
              <div className="readOnlyField">{userId}</div>
            </div>

            <div>
              <label className="fieldLabel">Ro'yxatdan o'tilgan sana</label>
              <div className="readOnlyField">{joinedAt}</div>
            </div>
          </div>

          <div className="infoBox">
            <Info size={20} className="infoIcon" />
            <p>
              Shaxsiy ma'lumotlarni o'zgartirish uchun tizim administratoriga
              murojaat qiling.
            </p>
          </div>
        </div>

        <div className="card securityCard">
          <h3 className="sectionTitle">
            <Shield className="securityIcon" /> Tizim himoyasi
          </h3>

          <div className="statusRow">
            <span className="statusLabel">Hisob holati:</span>
            <span className="statusBadge">Faol</span>
          </div>
        </div>
      </div>

      <div className="rightColumn">
        <div className="card botCard">
          <div className="botHeader">
            <Bot className="botIcon" size={24} />
            <h3 className="botTitle">Bot Ma'lumotlari</h3>
          </div>

          <div className="botContent">
            <div>
              <p className="metaLabel">Telegram ID</p>
              <p className="monoBox">{userId}</p>
            </div>

            {/* Mobile Only Theme Toggle */}
            <div className="toggleRow mobileOnly" onClick={toggleTheme} style={{ cursor: "pointer" }}>
              <span className="toggleLabel" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
                Ilova Mavzusi
              </span>
              <span className="toggleState">
                {theme === "light" ? "KUNDUZGI" : "TUNGI"}
              </span>
            </div>

            <div className="toggleRow">
              <span className="toggleLabel">Sotuv xabarnomalari</span>
              <span className="toggleState">YOQILGAN</span>
            </div>

            <button className="disabledButton">
              <Smartphone size={18} /> Botni sozlash (Yopiq)
            </button>
          </div>
        </div>

        <button className="logoutButton" onClick={handleLogout}>
          <LogOut size={20} /> Tizimdan chiqish
        </button>
      </div>
    </div>
  );
}