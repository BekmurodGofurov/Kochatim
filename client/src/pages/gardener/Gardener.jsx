import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, User, X } from "lucide-react";

import Loader from "../../components/loader/Loader";
import GroupCard from "../../components/groupCard/GroupCard";
import SortCard from "../../components/sortCard/SortCard";
import { apiFetch } from "../../api/https";
import Header from "../../components/header/Header";
import "./Gardener.scss";

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

export default function Gardener() {
  const navigate = useNavigate();
  const { uId, cId: cIdParam, tId: tIdParam } = useParams();
  const cId = cIdParam ? Number(cIdParam) : null;
  const tId = tIdParam ? Number(tIdParam) : null;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const d = await apiFetch(`/api/users/${encodeURIComponent(String(uId))}/dashboard`);
        if (!cancelled) setData(d);
      } catch (e) {
        if (!cancelled) setError(e?.message || "Yuklab bo‘lmadi");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [uId]);

  const groups = useMemo(() => {
    if (!data) return [];
    const cats = data.categories || [];
    const types = data.types || [];
    const seedlings = data.seedlings || [];

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
        const q = seedMap.get(t_id) || { q1: 0, q2: 0, q3: 0 };
        const images = pickImagesFromType(t);
        return {
          id: t_id,
          t_id,
          name: String(t.t_name || ""),
          nav1: q.q1,
          nav2: q.q2,
          nav3: q.q3,
          images,
          description: t?.deff || t?.description || t?.t_desc || t?.t_deff || "",
          updated_at: q.updated_at || t?.updated_at || null,
          added_at: q.added_at || t?.added_at || null,
        };
      });

      const totalValue = sorts.reduce((sum, x) => sum + (x.nav1 || 0) + (x.nav2 || 0) + (x.nav3 || 0), 0);
      const groupImages = sorts.flatMap((s) => (Array.isArray(s.images) ? s.images : [])).filter(Boolean);

      return {
        id: c_id,
        groupName: c_name,
        totalValue,
        sorts,
        groupImages,
      };
    });
  }, [data]);

  const me = data?.user;

  const selectedGroup = useMemo(() => {
    if (!cId) return null;
    return groups.find((g) => Number(g.id) === Number(cId)) || null;
  }, [groups, cId]);

  const selectedSort = useMemo(() => {
    if (!selectedGroup || !tId) return null;
    return (selectedGroup.sorts || []).find((s) => Number(s.id) === Number(tId)) || null;
  }, [selectedGroup, tId]);

  return (
    <div className="gardenerPage">
      <Header />

      <div className="gardenerTop">
        <button type="button" className="gardenerBack" onClick={() => navigate(-1)}>
          <ArrowLeft size={18} strokeWidth={3} />
          <span>Orqaga</span>
        </button>

        {loading ? (
          <Loader text="Yuklanmoqda..." />
        ) : error ? (
          <Loader text={error} />
        ) : (
        <div className="gardenerHeader">
          <div className="gardenerAvatar">
            {me?.u_photo ? (
              <img src={`${API_BASE}/api/img/${me.u_photo}`} alt={me?.u_name || "Bog‘bon"} />
            ) : (
              <User size={28} />
            )}
          </div>
          <div className="gardenerMeta">
            <div className="gardenerName">{me?.u_name || me?.u_id}</div>
            <div className="gardenerSub">
              {me?.u_username ? `@${me.u_username}` : "—"} • {me?.u_phone ? `+${me.u_phone}` : "—"} • {me?.u_id}
            </div>
          </div>
        </div>
        )}
      </div>

      {loading || error ? null : (
        <>
      <div className="gardenerSection">
        <div className="gardenerSectionTitle">Omborxona (faqat ko‘rish)</div>
        <div className="gardenerSectionLine" />
      </div>

      {!cId && (
        <div className="gardenerGrid">
          {groups.map((group, idx) => (
            <GroupCard
              key={group.id}
              group={group}
              index={idx}
              tick={0}
              toWebImgUrl={toWebImgUrl}
              onClick={() => navigate(`/gardeners/${uId}/group/${group.id}`)}
            />
          ))}
        </div>
      )}

      {cId && !selectedGroup && (
        <div className="gardenerHint">Guruh topilmadi.</div>
      )}

      {cId && selectedGroup && (
        <div className="gardenerGrid">
          {selectedGroup.sorts.map((sort) => (
            <SortCard
              key={sort.id}
              sort={sort}
              toWebImgUrl={toWebImgUrl}
              onClick={() => navigate(`/gardeners/${uId}/group/${selectedGroup.id}/sort/${sort.id}`)}
            />
          ))}
        </div>
      )}

      {selectedSort && (
        <SortDetailModal
          selectedSort={selectedSort}
          onClose={() => navigate(`/gardeners/${uId}/group/${selectedGroup.id}`)}
        />
      )}
        </>
      )}
    </div>
  );
}

function SortDetailModal({ selectedSort, onClose }) {
  return (
    <div className="gardenerModal" role="dialog" aria-modal="true">
      <div className="gardenerModalPanel">
        <div className="gardenerModalMedia">
          <img src={toWebImgUrl(selectedSort.images?.[0])} alt={selectedSort.name} />
        </div>

        <div className="gardenerModalBody">
          <div className="gardenerModalTop">
            <h2 className="gardenerModalTitle">{selectedSort.name}</h2>
            <button type="button" className="gardenerModalClose" onClick={onClose}>
              <X size={26} />
            </button>
          </div>

          <div className="gardenerModalLine" />

          <div className="gardenerStats">
            <div className="gardenerStat">
              <div className="k">1-NAV</div>
              <div className="v">{selectedSort.nav1} ta</div>
            </div>
            <div className="gardenerStat">
              <div className="k">2-NAV</div>
              <div className="v">{selectedSort.nav2} ta</div>
            </div>
            <div className="gardenerStat">
              <div className="k">3-NAV</div>
              <div className="v">{selectedSort.nav3} ta</div>
            </div>
          </div>

          {selectedSort.description && (
            <div className="gardenerDesc">
              <div className="k">Nav haqida</div>
              <div className="t">{selectedSort.description}</div>
            </div>
          )}
        </div>
      </div>

      <button type="button" className="gardenerModalBackdrop" onClick={onClose} aria-label="Close modal" />
    </div>
  );
}

