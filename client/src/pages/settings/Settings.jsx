// src/pages/Settings.jsx
import React, { useEffect, useMemo, useState } from "react";
import { User, Shield, Smartphone, Tablet, LogOut, Info, Moon, Sun, Link2, Trash2, ExternalLink, Plus, Monitor } from "lucide-react";

function getDeviceType(deviceName) {
  if (!deviceName) return "desktop";
  if (deviceName.includes("iPad") || deviceName.includes("Tablet")) return "tablet";
  if (deviceName.includes("iPhone") || deviceName.includes("Android")) return "mobile";
  return "desktop";
}

import Loader from "../../components/loader/Loader.jsx";
import { useDashboard } from "../../context/DashboardContext";
import { useTheme } from "../../context/ThemeContext";
import { apiFetch, getSessionToken, API_BASE } from "../../api/https";
import { useNavigate } from "react-router-dom";
import "./Settings.scss";

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
  const [copyToast, setCopyToast] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const inviteLink = useMemo(() => {
    if (!inviteToken) return "";
    const u = botUsername.trim();
    if (!u) return "";
    return `https://t.me/${u}?start=partner_${inviteToken}`;
  }, [inviteToken, botUsername]);

  useEffect(() => {
    if (!getSessionToken()) return;
    let cancelled = false;
    (async () => {
      setPartnersLoading(true);
      setSessionsLoading(true);
      try {
        const [p, tok, sess] = await Promise.all([
          apiFetch("/api/partners"),
          apiFetch("/api/partners/invite-token"),
          apiFetch("/api/sessions"),
        ]);
        if (cancelled) return;
        setPartners(Array.isArray(p) ? p : []);
        setInviteToken(tok?.token || "");
        setBotUsername((tok?.bot_username || "").replace(/^@/, ""));
        setSessions(Array.isArray(sess) ? sess : []);
      } catch (e) {
        if (!cancelled) {
          setPartners([]);
          setInviteToken("");
          setBotUsername("");
          setSessions([]);
        }
      } finally {
        if (!cancelled) {
          setPartnersLoading(false);
          setSessionsLoading(false);
        }
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
                          if (!confirm("Hamkorlikni to’xtatasizmi?")) return;
                          try {
                            await apiFetch("/api/partners/remove", { method: "POST", body: { p_id: p.u_id } });
                            setPartners((prev) => prev.filter((x) => x.u_id !== p.u_id));
                          } catch {
                            alert("Xatolik: o’chirib bo’lmadi.");
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
                    {inviteLoading
                      ? "Yuklanmoqda..."
                      : inviteLink
                        ? inviteLink
                        : !inviteToken
                          ? "Yuklanmoqda..."
                          : "Bot username sozlanmagan"}
                  </div>

                  {copyToast && (
                    <div className="copyToast">✅ Link nusxalandi!</div>
                  )}

                  <div className="addPartnerActions">
                    <button
                      type="button"
                      className="copyBtn"
                      onClick={async () => {
                        if (!inviteLink) {
                          try { await ensureInviteToken(); } catch {}
                        }
                        if (!inviteLink) return;
                        try {
                          await navigator.clipboard.writeText(inviteLink);
                          setCopyToast(true);
                          setTimeout(() => setCopyToast(false), 2500);
                        } catch {
                          alert("Nusxalab bo’lmadi. Linkni qo’lda belgilang.");
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
                              title: "Ko’chatim hamkorlik taklifi",
                              text: "Hamkor bo’lish uchun linkni bosing:",
                              url: inviteLink,
                            });
                            setShowAddPartner(false);
                            return;
                          } catch {
                            // foydalanuvchi bekor qildi yoki qo’llab-quvvatlanmaydi
                          }
                        }
                        try {
                          await navigator.clipboard.writeText(inviteLink);
                          setCopyToast(true);
                          setTimeout(() => setCopyToast(false), 2500);
                        } catch {
                          alert("Linkni qo’lda nusxalang.");
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

        <div className="card devicesCard">
          <div className="devicesHeader">
            <Smartphone className="devicesIcon" size={22} />
            <h3 className="devicesTitle">Qurilmalar</h3>
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

          <div className="devicesList">
            {sessionsLoading ? (
              <div className="muted">Yuklanmoqda...</div>
            ) : sessions.length === 0 ? (
              <div className="muted">Faol qurilmalar yo'q.</div>
            ) : (
              sessions.map((s) => {
                const label = [s.device_name || "Browser", s.city].filter(Boolean).join("  ");
                const dtype = getDeviceType(s.device_name);
                const DeviceIcon = dtype === "tablet" ? Tablet : dtype === "mobile" ? Smartphone : Monitor;
                return (
                  <div key={s.session_id} className="deviceRow">
                    <div className="deviceLeft">
                      <DeviceIcon size={18} className="deviceTypeIcon" />
                      <div className="deviceInfo">
                        <div className="deviceName">
                          {label}
                          {s.is_current && <span className="currentBadge">Joriy</span>}
                        </div>
                        <div className="deviceSub">
                          <span>{formatDate(s.created_at)}</span>
                          {s.ip_address && <span className="deviceIp">IP: {s.ip_address}</span>}
                        </div>
                      </div>
                    </div>
                    {!s.is_current && (
                      <button
                        className="iconBtn danger"
                        type="button"
                        title="Sessiyani tugatish"
                        onClick={async () => {
                          if (!confirm("Bu qurilmani o'chirasizmi?")) return;
                          try {
                            await apiFetch(`/api/sessions/${s.session_id}`, { method: "DELETE" });
                            setSessions((prev) => prev.filter((x) => x.session_id !== s.session_id));
                          } catch {
                            alert("Xatolik: o'chirib bo'lmadi.");
                          }
                        }}
                      >
                        <Trash2 size={18} />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        <button className="logoutButton" onClick={handleLogout}>
          <LogOut size={20} /> Tizimdan chiqish
        </button>
      </div>
    </div>
  );
}