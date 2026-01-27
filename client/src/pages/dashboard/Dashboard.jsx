import React, { useMemo, useRef, useState, useEffect } from "react";
import { LayoutDashboard } from "lucide-react";

import Loader from "../../components/loader/Loader.jsx";
import PieCard from "../../components/pieCard/PieCard.jsx";
import { useDashboard } from "../../context/DashboardContext";
import "./DashboardStyle.scss";

const COLORS = ["#3b82f6", "#fbbf24", "#c084fc", "#f87171", "#34d399"];

export default function Dashboard() {
  const { dashboardData: dashboard, loading: pageLoading, error: pageError } = useDashboard();

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const detailsRef = useRef(null);

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
        updated_at: s.updated_at || s.last_updated || null,
        created_at: s.created_at || s.date || null,
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

        return {
          t_id,
          name,
          nav1: q.q1,
          nav2: q.q2,
          nav3: q.q3,
          updated_at: q.updated_at || t?.updated_at || null,
          created_at: q.created_at || t?.created_at || null,
        };
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
              outerRadius="100%" // Maximize size
              stroke="var(--surface-main)"
              strokeWidth={0}
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
            <Loader />
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

                        <div className="dashboard-sort-date">
                          {sort.updated_at || sort.created_at ? (
                            <>
                              <span className="dashboard-sort-date-label">
                                {sort.updated_at ? "Yangilangan: " : "Qo'shilgan: "}
                              </span>
                              <span className="dashboard-sort-date-time">
                                {(() => {
                                  const dStr = sort.updated_at || sort.created_at;
                                  const d = new Date(dStr);
                                  if (isNaN(d.getTime())) return dStr;
                                  const day = String(d.getDate()).padStart(2, "0");
                                  const month = String(d.getMonth() + 1).padStart(2, "0");
                                  const year = d.getFullYear();
                                  const hours = String(d.getHours()).padStart(2, "0");
                                  const minutes = String(d.getMinutes()).padStart(2, "0");
                                  return `${hours}:${minutes} ${day}.${month}.${year}`;
                                })()}
                              </span>
                            </>
                          ) : (
                            <span className="dashboard-sort-date-label">Sana noaniq</span>
                          )}
                        </div>

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
                    outerRadius="100%" // Maximize size
                    stroke="var(--surface-main)"
                    strokeWidth={0}
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