import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ArrowLeft, User, X } from "lucide-react";

import Loader from "../../components/loader/Loader";
import GroupsGrid from "../../components/groupsGrid/GroupsGrid";
import SortsGrid from "../../components/sortsGrid/SortsGrid";
import { apiFetch, API_BASE } from "../../api/https";
import { toWebImgUrl } from "../../utils/imageUtils";
import { buildGroupsFromDashboard } from "../../utils/buildGroups";
import Header from "../../components/header/Header";
import "./Gardener.scss";

export default function Gardener() {
  const navigate = useNavigate();
  const location = useLocation();
  const { uId, cId: cIdParam, tId: tIdParam } = useParams();
  const cId = cIdParam ? Number(cIdParam) : null;
  const tId = tIdParam ? Number(tIdParam) : null;

  const isPartnerView = location.pathname.startsWith("/partners/");
  const basePath = isPartnerView ? "/partners" : "/gardeners";

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
        if (!cancelled) setError(e?.message || "Yuklab bo'lmadi");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [uId]);

  const groups = useMemo(() => buildGroupsFromDashboard(data), [data]);

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
      {!isPartnerView && <Header />}

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
              <img src={`${API_BASE}/api/img/${me.u_photo}`} alt={me?.u_name || "Bog'bon"} />
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
        <div className="gardenerSectionTitle">Omborxona (faqat ko'rish)</div>
        <div className="gardenerSectionLine" />
      </div>

      {!cId && (
        <GroupsGrid
          groups={groups}
          className="gardenerGrid"
          onGroupClick={(group) => navigate(`${basePath}/${uId}/group/${group.id}`)}
        />
      )}

      {cId && !selectedGroup && (
        <div className="gardenerHint">Guruh topilmadi.</div>
      )}

      {cId && selectedGroup && (
        <SortsGrid
          sorts={selectedGroup.sorts}
          className="gardenerGrid"
          onSortClick={(sort) => navigate(`${basePath}/${uId}/group/${selectedGroup.id}/sort/${sort.id}`)}
        />
      )}

      {selectedSort && (
        <SortDetailModal
          selectedSort={selectedSort}
          onClose={() => navigate(`${basePath}/${uId}/group/${selectedGroup.id}`)}
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
