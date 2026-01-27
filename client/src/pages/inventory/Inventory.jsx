import React, { useMemo, useState, useEffect } from "react";
import { Plus, ArrowLeft, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import Loader from "../../components/loader/Loader";
import GroupCard from "../../components/groupCard/GroupCard";
import SortCard from "../../components/sortCard/SortCard";
import { useDashboard } from "../../context/DashboardContext";
import "./Inventory.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";


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

  const { dashboardData: dashboard, loading: pageLoading, error: pageError } = useDashboard();

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

        const images = pickImagesFromType(t);

        return {
          id: t_id,
          t_id,
          name,
          nav1: q.q1,
          nav2: q.q2,
          nav3: q.q3,
          images,
          images,
          description: t?.deff || t?.description || t?.t_desc || "",
          updated_at: q.updated_at || t?.updated_at || t?.last_updated || null,
          created_at: q.created_at || t?.created_at || t?.date || null,
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

          <button type="button" className="inv-btn inv-btn--primary">
            <Plus size={20} strokeWidth={3} />
            <span>Yangi nav qo'shish</span>
          </button>
        </header>

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
      <button
        type="button"
        className="inv-back"
        onClick={() => navigate(`/u/${uId}/inventory`)}
      >
        <ArrowLeft size={18} strokeWidth={3} />
        <span>Guruhlarga qaytish</span>
      </button>

      <div className="inv-detailHead">
        <h2 className="inv-detailTitle">
          {selectedGroup.groupName} <span>Navlari</span>
        </h2>
      </div>

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
        <div className="inv-modal" role="dialog" aria-modal="true">
          <div className="inv-modal__panel">
            <div className="inv-modal__media">
              <img src={toWebImgUrl(selectedSort.images?.[0])} alt={selectedSort.name} />
            </div>

            <div className="inv-modal__body">
              <div className="inv-modal__top">
                <h2 className="inv-modal__title">{selectedSort.name}</h2>
                <button
                  type="button"
                  className="inv-modal__close"
                  onClick={() => navigate(`/u/${uId}/inventory/group/${selectedGroup.id}`)}
                >
                  <X size={26} />
                </button>
              </div>

              <div className="inv-modal__accent" />

              <div className="inv-modal__block">
                <div className="inv-modal__kicker">Sifat bo'yicha zaxira</div>

                <div className="inv-modal__stats">
                  <div className="inv-stat inv-stat--a">
                    <div className="inv-stat__label">1-NAV</div>
                    <div className="inv-stat__value">{selectedSort.nav1} ta</div>
                  </div>

                  <div className="inv-stat inv-stat--b">
                    <div className="inv-stat__label">2-NAV</div>
                    <div className="inv-stat__value">{selectedSort.nav2} ta</div>
                  </div>

                  <div className="inv-stat inv-stat--c">
                    <div className="inv-stat__label">3-NAV</div>
                    <div className="inv-stat__value">{selectedSort.nav3} ta</div>
                  </div>
                </div>
              </div>

              <div className="inv-modal__block inv-modal__block--grow">
                <div className="inv-modal__kicker">Nav haqida ma'lumot</div>
                <p className="inv-modal__text">
                  {selectedSort.description || "Ushbu nav haqida qo'shimcha ma'lumot mavjud emas."}
                </p>
              </div>

              <div className="inv-modal__footer">
                <div className="inv-modal__total">
                  <div className="inv-modal__totalLabel">Umumiy soni</div>
                  <div className="inv-modal__totalValue">
                    {Number(selectedSort.nav1 || 0) +
                      Number(selectedSort.nav2 || 0) +
                      Number(selectedSort.nav3 || 0)}
                  </div>
                </div>

                <button type="button" className="inv-btn inv-btn--dark">
                  Tahrirlash
                </button>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="inv-modal__backdrop"
            onClick={() => navigate(`/u/${uId}/inventory/group/${selectedGroup.id}`)}
            aria-label="Close modal"
          />
        </div>
      )}
    </div>
  );
}