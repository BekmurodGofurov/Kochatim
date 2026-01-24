// src/pages/Dashboard/Dashboard.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { LayoutDashboard } from "lucide-react";

import Loader from "../../components/loader/Loader.jsx";
import PieCard from "../../components/pieCard/PieCard.jsx";
import "./DashboardStyle.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function getToken() {
  return localStorage.getItem("session_token");
}

async function apiGetDashboard() {
  const token = getToken();

  const res = await fetch(`${API_BASE}/api/me/dashboard`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  const json = await res.json().catch(() => null);

  if (!res.ok || !json || json.ok !== true) {
    const code = json?.error?.code;
    const msg = json?.error?.message || "Server bilan bog‘lanib bo‘lmadi";

    if (res.status === 401 || code === "UNAUTHORIZED") {
      localStorage.removeItem("session_token");
    }
    throw new Error(msg);
  }

  return json.data;
}

const COLORS = ["#3b82f6", "#fbbf24", "#c084fc", "#f87171", "#34d399"];

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const detailsRef = useRef(null);

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        setPageLoading(true);
        setPageError("");
        const data = await apiGetDashboard();
        if (!alive) return;
        setDashboard(data);
      } catch (e) {
        if (!alive) return;
        setPageError(e?.message || "Xatolik");
      } finally {
        if (!alive) return;
        setPageLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, []);

  const groups = useMemo(() => {
    if (!dashboard) return [];

    const cats = dashboard.categories || [];
    const types = dashboard.types || [];
    const seedlings = dashboard.seedlings || [];

    const seedMap = new Map();
    for (const s of seedlings) {
      seedMap.set(Number(s.t_id), {
        q1: Number(s.quality_1 || 0),
        q2: Number(s.quality_2 || 0),
        q3: Number(s.quality_3 || 0),
      });
    }

    return cats.map((c) => {
      const c_id = Number(c.c_id);
      const c_name = String(c.c_name || "");

      const myTypes = types.filter((t) => Number(t.c_id) === c_id);

      const sorts = myTypes.map((t) => {
        const t_id = Number(t.t_id);
        const name = String(t.t_name || "");
        const q = seedMap.get(t_id) || { q1: 0, q2: 0, q3: 0 };

        return { t_id, name, nav1: q.q1, nav2: q.q2, nav3: q.q3 };
      });

      const totalValue = sorts.reduce((sum, x) => sum + x.nav1 + x.nav2 + x.nav3, 0);

      return { id: c_id, groupName: c_name, totalValue, sorts };
    });
  }, [dashboard]);

  useEffect(() => {
    if (!groups.length) return;
    if (selectedGroup) return;
    setSelectedGroup(groups[0]);
  }, [groups, selectedGroup]);

  const grandTotal = useMemo(
    () => groups.reduce((sum, g) => sum + Number(g.totalValue || 0), 0),
    [groups]
  );

  const mainPieData = useMemo(
    () =>
      groups.map((item, index) => ({
        name: item.groupName,
        value: item.totalValue,
        color: COLORS[index % COLORS.length],
        original: item,
      })),
    [groups]
  );

  const handleGroupClick = (group) => {
    setDetailLoading(true);
    setSelectedGroup(null);

    setTimeout(() => {
      setSelectedGroup(group);
      setDetailLoading(false);
      if (detailsRef.current) detailsRef.current.scrollIntoView({ behavior: "smooth" });
    }, 400);
  };

  const selectedPieData = useMemo(() => {
    if (!selectedGroup) return [];
    return (selectedGroup.sorts || []).map((s) => ({
      name: s.name,
      value: (Number(s.nav1) || 0) + (Number(s.nav2) || 0) + (Number(s.nav3) || 0),
    }));
  }, [selectedGroup]);

  if (pageLoading) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-page-loader">
          <Loader />
        </div>
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-error">
          <div className="dashboard-error-title">Xatolik</div>
          <div className="dashboard-error-text">{pageError}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-card dashboard-main">
        <div className="dashboard-main-left">
          <h2 className="dashboard-title">
            <LayoutDashboard className="dashboard-title-icon" />
            <span>
              Sizda <b>{groups.length}</b> ta guruh bor
            </span>
          </h2>

          <div className="dashboard-group-list">
            {mainPieData.map((item, index) => {
              const active = selectedGroup?.id === item.original.id;

              return (
                <button
                  type="button"
                  key={`${item.name}-${index}`}
                  onClick={() => handleGroupClick(item.original)}
                  className={`dashboard-group-row ${active ? "is-active" : ""}`}
                >
                  <span className="dashboard-group-left">
                    <span className="dashboard-dot" style={{ backgroundColor: item.color }} />
                    <span className="dashboard-group-name">{item.name}</span>
                  </span>

                  <span className="dashboard-group-value">
                    {Number(item.value || 0).toLocaleString()} ta
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="dashboard-main-right">
          <div className="dashboard-pie-wrap">
            <PieCard
              data={mainPieData}
              colors={COLORS}
              outerRadius={160}
              stroke="#fff"
              strokeWidth={4}
              cellClassName="dashboard-pie-cell"
              onSliceClick={(entry) => {
                const group = entry?.original;
                if (group) handleGroupClick(group);
              }}
              tooltipFormatter={(value, name) => {
                const total = mainPieData.reduce((a, b) => a + (b.value || 0), 0);
                const pct = total ? ((Number(value) / total) * 100).toFixed(1) : "0.0";
                return [`${pct}%`, name];
              }}
            />
          </div>

          <div className="dashboard-total-card">
            <p className="dashboard-total-caption">BARCHA GURUHLAR BO'YICHA</p>
            <h3 className="dashboard-total-title">Jami ko'chat:</h3>
            <p className="dashboard-total-value">
              {Number(grandTotal || 0).toLocaleString()}
              <span className="dashboard-total-unit"> TA</span>
            </p>
          </div>
        </div>
      </div>

      <div ref={detailsRef} className="dashboard-details">
        {detailLoading && (
          <div className="dashboard-detail-loader">
            <Loader/>
          </div>
        )}

        {selectedGroup && !detailLoading && (
          <div className="dashboard-card dashboard-detail-card">
            <div className="dashboard-detail-layout">
              <div className="dashboard-detail-left">
                <h3 className="dashboard-detail-title">
                  {selectedGroup.groupName}
                  <span className="dashboard-detail-subtitle">
                    {" "}
                    / Sortlar soni - <b>{(selectedGroup.sorts || []).length}</b>
                  </span>
                </h3>

                <div className="dashboard-sort-grid">
                  {(selectedGroup.sorts || []).map((sort, idx) => {
                    const total =
                      (Number(sort.nav1) || 0) +
                      (Number(sort.nav2) || 0) +
                      (Number(sort.nav3) || 0);

                    return (
                      <div key={`${sort.t_id}-${idx}`} className="dashboard-sort-card">
                        <p
                          className="dashboard-sort-name"
                          style={{ color: COLORS[idx % COLORS.length] }}
                        >
                          {sort.name}
                        </p>

                        <div className="dashboard-sort-total">
                          {total.toLocaleString()}
                          <span className="dashboard-sort-total-suffix"> dona jami</span>
                        </div>

                        <div className="dashboard-sort-divider" />

                        <div className="dashboard-sort-qualities">
                          <div className="dashboard-sort-q">
                            <p className="dashboard-sort-q-label">1-NAV</p>
                            <p className="dashboard-sort-q-value">
                              {(Number(sort.nav1) || 0).toLocaleString()}
                            </p>
                          </div>

                          <div className="dashboard-sort-q">
                            <p className="dashboard-sort-q-label">2-NAV</p>
                            <p className="dashboard-sort-q-value muted-2">
                              {(Number(sort.nav2) || 0).toLocaleString()}
                            </p>
                          </div>

                          <div className="dashboard-sort-q">
                            <p className="dashboard-sort-q-label">3-NAV</p>
                            <p className="dashboard-sort-q-value muted-3">
                              {(Number(sort.nav3) || 0).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="dashboard-detail-right">
                <h4 className="dashboard-right-caption">
                  {selectedGroup.groupName} BO'YICHA ULUSH (%)
                </h4>

                <div className="dashboard-right-pie">
                  <PieCard
                    data={selectedPieData}
                    colors={COLORS}
                    outerRadius={80}
                    stroke="#fff"
                    strokeWidth={2}
                    tooltipFormatter={(value, name) => {
                      const total = Number(selectedGroup.totalValue || 0);
                      const pct = total ? ((Number(value) / total) * 100).toFixed(1) : "0.0";
                      return [`${pct}%`, name];
                    }}
                  />
                </div>

                <p className="dashboard-right-total">
                  {Number(selectedGroup.totalValue || 0).toLocaleString()}
                </p>
                <p className="dashboard-right-total-label">JAMI {selectedGroup.groupName}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}