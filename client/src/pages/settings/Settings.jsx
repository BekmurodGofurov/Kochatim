// src/pages/Settings.jsx
import React, { useEffect, useMemo, useState } from "react";
import { User, Shield, Bot, Smartphone, LogOut, Info, Moon, Sun, Link2, Trash2, ExternalLink, Plus } from "lucide-react";

import Loader from "../../components/loader/Loader.jsx";
import { useDashboard } from "../../context/DashboardContext";
import { useTheme } from "../../context/ThemeContext";
import { apiFetch, getSessionToken } from "../../api/https";
import { useNavigate } from "react-router-dom";
import "./Settings.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const BOT_USERNAME_FALLBACK = (import.meta.env.VITE_TG_BOT_USERNAME || "").replace(/^@/, "");

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
  const navigate = useNavigate();

  const me = dashboardData?.user;

  const [partners, setPartners] = useState([]);
  const [inviteToken, setInviteToken] = useState("");
  const [botUsername, setBotUsername] = useState("");
  const [partnersLoading, setPartnersLoading] = useState(false);
  const [showAddPartner, setShowAddPartner] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);

  const inviteLink = useMemo(() => {
    if (!inviteToken) return "";
    const u = (botUsername || BOT_USERNAME_FALLBACK || "").trim();
    if (!u) return "";
    return `https://t.me/${u}?start=partner_${inviteToken}`;
  }, [inviteToken, botUsername]);

  useEffect(() => {
    if (!getSessionToken()) return;
    let cancelled = false;
    (async () => {
      setPartnersLoading(true);
      try {
        const [p, tok] = await Promise.all([
          apiFetch("/api/partners"),
          apiFetch("/api/partners/invite-token"),
        ]);
        if (cancelled) return;
        setPartners(Array.isArray(p) ? p : []);
        setInviteToken(tok?.token || "");
        setBotUsername((tok?.bot_username || "").replace(/^@/, ""));
      } catch (e) {
        if (!cancelled) {
          setPartners([]);
          setInviteToken("");
          setBotUsername("");
        }
      } finally {
        if (!cancelled) setPartnersLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const ensureInviteToken = async () => {
    if (inviteToken) return inviteToken;
    setInviteLoading(true);
    try {
      const tok = await apiFetch("/api/partners/invite-token");
      const t = tok?.token || "";
      setInviteToken(t);
      setBotUsername((tok?.bot_username || "").replace(/^@/, ""));
      return t;
    } finally {
      setInviteLoading(false);
    }
  };

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
              murojaat qiling: <a href="https://t.me/Bekmurod_Gofurov" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>@Bekmurod_Gofurov</a>
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
        <div className="card partnersCard">
          <div className="partnersHeader">
            <Link2 className="partnersIcon" size={22} />
            <h3 className="partnersTitle">Hamkorlar</h3>
          </div>

          <div className="partnersBody">
            <div className="partnersList">
              {partnersLoading ? (
                <div className="muted">Yuklanmoqda...</div>
              ) : partners.length === 0 ? (
                <div className="muted">Hozircha hamkorlar yo‘q.</div>
              ) : (
                partners.map((p) => (
                  <div key={p.u_id} className="partnerRow">
                    <div className="partnerLeft">
                      <div className="partnerName">{p.u_name || p.u_id}</div>
                      <div className="partnerSub">
                        {p.u_username ? `@${p.u_username}` : "—"} • {p.u_id}
                      </div>
                    </div>
                    <div className="partnerActions">
                      <button
                        className="iconBtn"
                        type="button"
                        title="Profil"
                        onClick={() => navigate(`/gardeners/${p.u_id}`)}
                      >
                        <ExternalLink size={18} />
                      </button>
                      <button
                        className="iconBtn danger"
                        type="button"
                        title="Hamkorlikni to‘xtatish"
                        onClick={async () => {
                          if (!confirm("Hamkorlikni to‘xtatasizmi?")) return;
                          try {
                            await apiFetch("/api/partners/remove", { method: "POST", body: { p_id: p.u_id } });
                            setPartners((prev) => prev.filter((x) => x.u_id !== p.u_id));
                            alert("Hamkor o‘chirildi ✅");
                          } catch (e) {
                            alert("Xatolik: " + (e?.message || "O‘chirib bo‘lmadi"));
                          }
                        }}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <button
              type="button"
              className="addPartnerBtn"
              onClick={async () => {
                setShowAddPartner(true);
                try {
                  await ensureInviteToken();
                } catch (e) {
                  alert("Xatolik: linkni olib bo‘lmadi. Login bo‘lganingizni tekshiring.");
                }
              }}
              title="Hamkor qo‘shish"
            >
              <Plus size={18} /> Hamkor qo‘shish
            </button>

            {showAddPartner && (
              <div className="addPartnerModal" role="dialog" aria-modal="true">
                <button
                  type="button"
                  className="addPartnerBackdrop"
                  onClick={() => setShowAddPartner(false)}
                  aria-label="Close"
                />
                <div className="addPartnerPanel">
                  <div className="addPartnerTitle">Hamkor qo‘shish</div>
                  <div className="addPartnerText">
                    Quyidagi linkni Telegram’da hamkorga yuboring. U linkni bosib, botda “Qabul qilaman” desa hamkor bo‘ladi.
                  </div>
                  <div className="monoBox">
                    {inviteLoading ? "Yuklanmoqda..." : (inviteLink || "Bot username sozlanmagan (TG_BOT_USERNAME)")}
                  </div>

                  <div className="addPartnerActions">
                    <button
                      type="button"
                      className="copyBtn"
                      onClick={async () => {
                        if (!inviteLink) {
                          try {
                            await ensureInviteToken();
                          } catch {}
                        }
                        if (!inviteLink) return;
                        try {
                          await navigator.clipboard.writeText(inviteLink);
                          alert("Link nusxalandi ✅");
                        } catch {
                          alert("Nusxalab bo‘lmadi. Linkni qo‘lda belgilang.");
                        }
                      }}
                      disabled={inviteLoading || !inviteLink}
                    >
                      Nusxalash
                    </button>

                    <button
                      type="button"
                      className="shareBtn"
                      onClick={async () => {
                        if (!inviteLink) return;
                        if (navigator.share) {
                          try {
                            await navigator.share({
                              title: "Ko‘chatim hamkorlik taklifi",
                              text: "Hamkor bo‘lish uchun linkni bosing:",
                              url: inviteLink,
                            });
                            return;
                          } catch {
                            // user cancelled or unsupported; fallback below
                          }
                        }
                        try {
                          await navigator.clipboard.writeText(inviteLink);
                          alert("Share qo‘llab-quvvatlanmadi. Link nusxalandi ✅");
                        } catch {
                          alert("Share ham, nusxalash ham ishlamadi. Linkni qo‘lda belgilang.");
                        }
                      }}
                      disabled={inviteLoading || !inviteLink}
                      title="Ulashish"
                    >
                      Share
                    </button>

                    <button type="button" className="closeBtn" onClick={() => setShowAddPartner(false)}>
                      Yopish
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

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