import React, { useMemo, useState, useEffect } from "react";
import { Plus, ArrowLeft, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import Loader from "../../components/loader/Loader";
import GroupCard from "../../components/groupCard/GroupCard";
import SortCard from "../../components/sortCard/SortCard";
import AddGroupModal from "../../components/addGroupModal/AddGroupModal";
import AddTypeModal from "../../components/addTypeModal/AddTypeModal";
import { useDashboard } from "../../context/DashboardContext";
import "./Inventory.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://api.kochatim.uz";


function toWebImgUrl(raw) {
  if (!raw) return "";
  if (typeof raw === "string" && (raw.startsWith("http://") || raw.startsWith("https://"))) {
    return raw;
  }
  return `${API_BASE}/api/img/${encodeURIComponent(String(raw))}`;
}

function pickImagesFromType(t) {
  const one =
    t?.i_url ||
    t?.image ||
    t?.image_url ||
    t?.t_image ||
    t?.img ||
    t?.photo ||
    t?.photo_url;

  return one ? [one] : [];
}

export default function Inventory() {
  const navigate = useNavigate();
  const params = useParams();
  const uId = params.uId; // string
  const cIdParam = params.cId; // string | undefined
  const tIdParam = params.tId; // string | undefined

  const cId = cIdParam ? Number(cIdParam) : null;
  const tId = tIdParam ? Number(tIdParam) : null;

  const { dashboardData: dashboard, loading: pageLoading, error: pageError, refreshDashboard } = useDashboard();

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAddTypeModal, setShowAddTypeModal] = useState(false);

  // 10s aylanish (guruh card rasmlari)
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 10000);
    return () => clearInterval(id);
  }, []);

  // Backend -> Inventory UI format
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
        updated_at: s.updated_at || null,
        added_at: s.added_at || null,
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

        const images = pickImagesFromType(t);

        return {
          id: t_id,
          t_id,
          name,
          nav1: q.q1,
          nav2: q.q2,
          nav3: q.q3,
          images,
          description: t?.deff || t?.description || t?.t_desc || t?.t_deff || "",
          updated_at: q.updated_at || t?.updated_at || null,
          added_at: q.added_at || t?.added_at || null,
        };
      });

      const totalValue = sorts.reduce(
        (sum, x) => sum + (x.nav1 || 0) + (x.nav2 || 0) + (x.nav3 || 0),
        0
      );

      const groupImages = sorts
        .flatMap((s) => (Array.isArray(s.images) ? s.images : []))
        .filter(Boolean);

      return {
        id: c_id,
        groupName: c_name,
        totalValue,
        sorts,
        groupImages,
      };
    });
  }, [dashboard]);

  // URL params bo‘yicha tanlangan group/sort topish
  const selectedGroup = useMemo(() => {
    if (!cId) return null;
    return groups.find((g) => Number(g.id) === Number(cId)) || null;
  }, [groups, cId]);

  const selectedSort = useMemo(() => {
    if (!selectedGroup || !tId) return null;
    return (selectedGroup.sorts || []).find((s) => Number(s.id) === Number(tId)) || null;
  }, [selectedGroup, tId]);

  // Handle body blur when modal is open
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

  // ✅ 1) GROUPS VIEW (URL: /u/:uId/inventory)
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

        <div className="inv-grid inv-grid--groups">
          {groups.map((group, idx) => (
            <GroupCard
              key={group.id}
              group={group}
              index={idx}
              tick={tick}
              toWebImgUrl={toWebImgUrl}
              onClick={() => navigate(`/u/${uId}/inventory/group/${group.id}`)}
            />
          ))}
        </div>
      </div>
    );
  }

  // ✅ Agar URL’da cId bor, lekin group topilmasa
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

  // ✅ 2) SORTS VIEW (URL: /u/:uId/inventory/group/:cId)
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

      <div className="inv-grid inv-grid--sorts">
        {selectedGroup.sorts.map((sort) => (
          <SortCard
            key={sort.id}
            sort={sort}
            toWebImgUrl={toWebImgUrl}
            onClick={() => navigate(`/u/${uId}/inventory/group/${selectedGroup.id}/sort/${sort.id}`)}
          />
        ))}
      </div>

      {/* ✅ MODAL (URL: /u/:uId/inventory/group/:cId/sort/:tId) */}
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
  const [comment, setComment] = useState("");
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
          comment: comment,
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
              <div className="inv-modal__kicker">Izoh (majburiy)</div>
              <textarea
                className="inv-modal__textarea"
                placeholder="Nega ayrilayotganini yozing (masalan: buzilgan yoki sotilgan)..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
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
                disabled={saving || (isSubtracting && !comment.trim())}
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