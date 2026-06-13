import React, { useMemo, useState, useEffect } from "react";
import { Plus, ArrowLeft, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import Loader from "../../components/loader/Loader";
import GroupsGrid from "../../components/groupsGrid/GroupsGrid";
import SortsGrid from "../../components/sortsGrid/SortsGrid";
import AddGroupModal from "../../components/addGroupModal/AddGroupModal";
import AddTypeModal from "../../components/addTypeModal/AddTypeModal";
import { useDashboard } from "../../context/DashboardContext";
import { API_BASE, getSessionToken } from "../../api/https";
import { toWebImgUrl } from "../../utils/imageUtils";
import { buildGroupsFromDashboard } from "../../utils/buildGroups";
import "./Inventory.scss";

export default function Inventory() {
  const navigate = useNavigate();
  const params = useParams();
  const uId = params.uId;
  const cIdParam = params.cId;
  const tIdParam = params.tId;

  const cId = cIdParam ? Number(cIdParam) : null;
  const tId = tIdParam ? Number(tIdParam) : null;

  const {
    dashboardData: dashboard, loading: pageLoading, error: pageError, refreshDashboard,
    partnerDashboardsData, partnerDashboardsLoading, fetchPartnerDashboards,
  } = useDashboard();

  const [showAddModal, setShowAddModal] = useState(false);
  const [showAddTypeModal, setShowAddTypeModal] = useState(false);
  const [searchQ, setSearchQ] = useState("");

  useEffect(() => {
    if (!cId && getSessionToken()) fetchPartnerDashboards();
  }, [cId]);

  const partnerDash = useMemo(() => {
    if (!partnerDashboardsData) return [];
    return partnerDashboardsData.map((item) => ({
      partner: item.partner,
      groups: buildGroupsFromDashboard({
        categories: item.categories,
        types:      item.types,
        seedlings:  item.seedlings,
      }),
    }));
  }, [partnerDashboardsData]);

  const partnersLoading = partnerDashboardsLoading;

  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 10000);
    return () => clearInterval(id);
  }, []);

  const groups = useMemo(() => buildGroupsFromDashboard(dashboard), [dashboard]);

  const normalizedQuery = searchQ.trim().toLowerCase();
  const filterGroups = (arr) => {
    if (!normalizedQuery) return arr;
    return (arr || []).filter((g) => {
      const gName = String(g.groupName || "").toLowerCase();
      if (gName.includes(normalizedQuery)) return true;
      return (g.sorts || []).some((s) => String(s.name || "").toLowerCase().includes(normalizedQuery));
    });
  };

  const groupsFiltered = useMemo(() => filterGroups(groups), [groups, normalizedQuery]);
  const partnerDashFiltered = useMemo(() => {
    if (!normalizedQuery) return partnerDash;
    return partnerDash
      .map((x) => ({
        ...x,
        groups: filterGroups(x.groups),
      }))
      .filter((x) => {
        const pName = String(x.partner?.u_name || "").toLowerCase();
        const pUser = String(x.partner?.u_username || "").toLowerCase();
        const pId = String(x.partner?.u_id || "");
        return (
          x.groups.length > 0 ||
          pName.includes(normalizedQuery) ||
          pUser.includes(normalizedQuery) ||
          pId.includes(normalizedQuery)
        );
      });
  }, [partnerDash, normalizedQuery]);

  const selectedGroup = useMemo(() => {
    if (!cId) return null;
    return groups.find((g) => Number(g.id) === Number(cId)) || null;
  }, [groups, cId]);

  const selectedSort = useMemo(() => {
    if (!selectedGroup || !tId) return null;
    return (selectedGroup.sorts || []).find((s) => Number(s.id) === Number(tId)) || null;
  }, [selectedGroup, tId]);

  useEffect(() => {
    const isAnyModalOpen = showAddModal || showAddTypeModal || !!selectedSort;
    if (isAnyModalOpen) {
      document.body.classList.add("has-modal");
    } else {
      document.body.classList.remove("has-modal");
    }
    return () => document.body.classList.remove("has-modal");
  }, [showAddModal, showAddTypeModal, selectedSort]);

  if (pageLoading) return <Loader text="Yuklanmoqda..." />;
  if (pageError) return <Loader text={pageError} />;

  // 1) GROUPS VIEW
  if (!cId) {
    return (
      <div className="inv-page">
        <header className="inv-header">
          <div className="inv-header__left">
            <div className="inv-badge">Zaxira Nazorati</div>
            <h1 className="inv-title">Omborxona</h1>
          </div>

          <button
            type="button"
            className="inv-btn inv-btn--primary"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={20} strokeWidth={3} />
            <span>Yangi Guruh qo'shish</span>
          </button>
        </header>

        {showAddModal && (
          <AddGroupModal
            onClose={() => setShowAddModal(false)}
            onSuccess={() => {
              setShowAddModal(false);
              refreshDashboard();
            }}
          />
        )}

        <div className="inv-section">
          <h2 className="inv-section__title">Guruhlar</h2>
          <div className="inv-section__line" />
        </div>

        <div className="inv-searchRow">
          <input
            className="inv-searchInput"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="Guruh, nav yoki hamkor ismi bo'yicha qidirish..."
          />
        </div>

        <GroupsGrid
          groups={groupsFiltered}
          tick={tick}
          className="inv-grid inv-grid--groups"
          onGroupClick={(group) => navigate(`/u/${uId}/inventory/group/${group.id}`)}
        />

        <div className="inv-partners">
          <div className="inv-section">
            <h2 className="inv-section__title">Hamkorlar</h2>
            <div className="inv-section__line" />
          </div>

          {partnersLoading ? (
            <div className="inv-partners__muted">Yuklanmoqda...</div>
          ) : partnerDashFiltered.length === 0 ? (
            <div className="inv-partners__muted">Hamkorlar topilmadi.</div>
          ) : (
            partnerDashFiltered.map((pd, pIdx) => (
              <div key={pd.partner.u_id} className="inv-partnerBlock">
                <div className="inv-partnerBlock__head">
                  <div className="inv-partnerBlock__name">
                    {pd.partner.u_name || pd.partner.u_id}
                  </div>
                  <button
                    type="button"
                    className="inv-partnerBlock__open"
                    onClick={() => navigate(`/gardeners/${pd.partner.u_id}`)}
                  >
                    Profil
                  </button>
                </div>
                <GroupsGrid
                  groups={pd.groups}
                  tick={tick}
                  className="inv-grid inv-grid--groups inv-grid--partners"
                  onGroupClick={(g) => navigate(`/gardeners/${pd.partner.u_id}/group/${g.id}`)}
                />
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  // Agar URL'da cId bor, lekin group topilmasa
  if (cId && !selectedGroup) {
    return (
      <div className="inv-page inv-page--detail">
        <button
          type="button"
          className="inv-back"
          onClick={() => navigate(`/u/${uId}/inventory`)}
        >
          <ArrowLeft size={18} strokeWidth={3} />
          <span>Guruhlarga qaytish</span>
        </button>

        <Loader text="Guruh topilmadi" />
      </div>
    );
  }

  // 2) SORTS VIEW
  return (
    <div className="inv-page inv-page--detail">
      <div className="inv-detailNav">
        <button
          type="button"
          className="inv-back"
          onClick={() => navigate(`/u/${uId}/inventory`)}
        >
          <ArrowLeft size={18} strokeWidth={3} />
          <span>Guruhlarga qaytish</span>
        </button>

        <button
          type="button"
          className="inv-btn inv-btn--primary inv-btn--small"
          onClick={() => setShowAddTypeModal(true)}
        >
          <Plus size={18} strokeWidth={3} />
          <span>Yangi Nav qo'shish</span>
        </button>
      </div>

      <div className="inv-detailHead">
        <h2 className="inv-detailTitle">
          {selectedGroup.groupName} <span>Navlari</span>
        </h2>
      </div>

      {showAddTypeModal && (
        <AddTypeModal
          cId={cId}
          onClose={() => setShowAddTypeModal(false)}
          onSuccess={() => {
            setShowAddTypeModal(false);
            refreshDashboard();
          }}
        />
      )}

      <SortsGrid
        sorts={selectedGroup.sorts}
        className="inv-grid inv-grid--sorts"
        onSortClick={(sort) => navigate(`/u/${uId}/inventory/group/${selectedGroup.id}/sort/${sort.id}`)}
      />

      {selectedSort && (
        <SortDetailModal
          selectedSort={selectedSort}
          selectedGroup={selectedGroup}
          uId={uId}
          onRefresh={refreshDashboard}
          onClose={() => navigate(`/u/${uId}/inventory/group/${selectedGroup.id}`)}
        />
      )}
    </div>
  );
}

function SortDetailModal({ selectedSort, selectedGroup, uId, onRefresh, onClose }) {
  const [deltas, setDeltas] = useState({ q1: 0, q2: 0, q3: 0 });
  const [price, setPrice] = useState("");
  const [saving, setSaving] = useState(false);

  const hasChanges = deltas.q1 !== 0 || deltas.q2 !== 0 || deltas.q3 !== 0;
  const isSubtracting = deltas.q1 < 0 || deltas.q2 < 0 || deltas.q3 < 0;

  const handleDelta = (field, amount) => {
    setDeltas((prev) => ({ ...prev, [field]: prev[field] + amount }));
  };

  const handleSave = async () => {
    if (!hasChanges) return;
    setSaving(true);
    try {
      const { apiFetch } = await import("../../api/https");
      await apiFetch("/api/seedlings/update", {
        method: "POST",
        body: {
          t_id: selectedSort.t_id,
          change_q1: deltas.q1,
          change_q2: deltas.q2,
          change_q3: deltas.q3,
          price: Number(price) || 0,
        },
      });
      onRefresh();
      onClose();
    } catch (err) {
      alert("Xatolik yuz berdi: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="inv-modal" role="dialog" aria-modal="true">
      <div className="inv-modal__panel">
        <div className="inv-modal__media">
          <img src={toWebImgUrl(selectedSort.images?.[0])} alt={selectedSort.name} />
        </div>

        <div className="inv-modal__body">
          <div className="inv-modal__top">
            <h2 className="inv-modal__title">{selectedSort.name}</h2>
            <button type="button" className="inv-modal__close" onClick={onClose}>
              <X size={26} />
            </button>
          </div>

          <div className="inv-modal__accent" />

          <div className="inv-modal__block">
            <div className="inv-modal__kicker">Sifat bo'yicha zaxira</div>

            <div className="inv-modal__stats">
              {[
                { label: "1-NAV", val: selectedSort.nav1, delta: deltas.q1, key: "q1", color: "a" },
                { label: "2-NAV", val: selectedSort.nav2, delta: deltas.q2, key: "q2", color: "b" },
                { label: "3-NAV", val: selectedSort.nav3, delta: deltas.q3, key: "q3", color: "c" },
              ].map((item) => (
                <div key={item.key} className={`inv-stat inv-stat--${item.color}`}>
                  <div className="inv-stat__info">
                    <div className="inv-stat__label">{item.label}</div>
                    <div className="inv-stat__value">
                      {item.val + item.delta} ta
                      {item.delta !== 0 && (
                        <span className="inv-stat__delta">
                          ({item.delta > 0 ? "+" : ""}{item.delta})
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="inv-stat__controls">
                    <QuantityButton onClick={() => handleDelta(item.key, -1)} type="minus" />
                    <QuantityButton onClick={() => handleDelta(item.key, 1)} type="plus" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {isSubtracting && (
            <div className="inv-modal__block inv-modal__block--grow">
              <div className="inv-modal__kicker">Sotuv summasi (majburiy)</div>
              <input
                type="number"
                className="inv-modal__input"
                placeholder="Necha pulga sotilganini yozing (masalan: 150000)..."
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                required
              />
            </div>
          )}

          {!isSubtracting && selectedSort.description && (
            <div className="inv-modal__block inv-modal__block--grow">
              <div className="inv-modal__kicker">Nav haqida ma'lumot</div>
              <p className="inv-modal__text">{selectedSort.description}</p>
            </div>
          )}

          <div className="inv-modal__footer">
            <div className="inv-modal__total">
              <div className="inv-modal__totalLabel">Umumiy soni</div>
              <div className="inv-modal__totalValue">
                {Number(selectedSort.nav1 || 0) +
                  Number(selectedSort.nav2 || 0) +
                  Number(selectedSort.nav3 || 0) +
                  deltas.q1 + deltas.q2 + deltas.q3}
              </div>
            </div>

            {hasChanges && (
              <button
                className={`inv-btn inv-btn--primary inv-btn--save ${saving ? "is-loading" : ""}`}
                onClick={handleSave}
                disabled={saving || (isSubtracting && (!price || Number(price) <= 0))}
              >
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            )}
          </div>
        </div>
      </div>

      <button
        type="button"
        className="inv-modal__backdrop"
        onClick={onClose}
        aria-label="Close modal"
      />
    </div>
  );
}

function QuantityButton({ onClick, type }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inv-qbtn inv-qbtn--${type}`}
      title={type === "plus" ? "Qo'shish" : "Ayirish"}
    >
      {type === "plus" ? "+" : "-"}
    </button>
  );
}
