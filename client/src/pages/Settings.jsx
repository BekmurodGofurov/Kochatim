import React, { useEffect, useState } from "react";
import { User, Shield, Bot, Smartphone, LogOut, Info } from "lucide-react";

import "./Settings.css";      // sizning eski style
import "./SettingsLoader.css";    // yangi: faqat loading uchun

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString();
  } catch {
    return String(value);
  }
}

export default function Settings() {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      setErrMsg("Session token topilmadi. Iltimos login qiling.");
      setLoading(false);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        setErrMsg("");

        const res = await fetch(`${API_BASE}/api/me`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        const body = await res.json().catch(() => null);

        if (!res.ok || !body || body.ok !== true) {
          const code = body?.error?.code;
          const msg = body?.error?.message || "Server bilan bog‘lanib bo‘lmadi";

          if (res.status === 401 || code === "UNAUTHORIZED") {
            localStorage.removeItem("session_token");
          }

          throw new Error(msg);
        }

        if (!cancelled) setMe(body.data);
      } catch (e) {
        if (!cancelled) setErrMsg(e?.message || "Xatolik yuz berdi");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("session_token");
    window.location.href = "/login";
  };

  // ✅ DATA KELGUNCHA: butun page o‘rniga loader
  if (loading) {
    return (
      <div className="pageLoader">
        <div className="spinner" />
        <div className="loaderText">Loading...</div>
      </div>
    );
  }

  // ✅ Error bo‘lsa ham loader o‘rniga error chiqadi (page ochilmaydi)
  if (errMsg) {
    return (
      <div className="pageLoader">
        <div className="loaderText">{errMsg}</div>
      </div>
    );
  }

  // UI: sizdagi layout o‘zgarmaydi, faqat qiymatlar backenddan
  const name = me?.u_name || "-";
  const username = me?.u_username ? `@${me.u_username}` : "-";
  const phone = me?.u_phone || "-";
  const userId = me?.u_id != null ? String(me.u_id) : "-";
  const joinedAt = formatDate(me?.added_at);

  return (
    <div className="settingsPage">
      {/* LEFT: Profile info */}
      <div className="leftColumn">
        <div className="card profileCard">
          <div className="profileHeader">
            <div className="avatarCircle">
              <User size={40} />
            </div>

            <div>
              <h2 className="profileTitle">{name}</h2>
              <p className="profileSubtitle">{username}</p>
            </div>
          </div>

          <div className="profileGrid">
            <div>
              <label className="fieldLabel">Telefon raqam</label>
              <div className="readOnlyField">{phone}</div>
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
            <p>Shaxsiy ma'lumotlarni o'zgartirish uchun tizim administratoriga murojaat qiling.</p>
          </div>
        </div>

        {/* Security section */}
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

      {/* RIGHT: Telegram Bot info */}
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