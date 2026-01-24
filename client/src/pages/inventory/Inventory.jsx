// src/pages/Inventory/Inventory.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Plus, ArrowLeft, X } from "lucide-react";

import Loader from "../../components/loader/Loader";
import GroupCard from "../../components/groupCard/GroupCard";
import SortCard from "../../components/sortCard/SortCard";

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

function toWebImgUrl(raw) {
  if (!raw) return "";
  if (
    typeof raw === "string" &&
    (raw.startsWith("http://") || raw.startsWith("https://"))
  ) {
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
  const [dashboard, setDashboard] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [selectedSort, setSelectedSort] = useState(null);

  // 10s (siz aytgandek)
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 10000);
    return () => clearInterval(id);
  }, []);

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

        const images = pickImagesFromType(t);

        return {
          id: t_id,
          t_id,
          name,
          nav1: q.q1,
          nav2: q.q2,
          nav3: q.q3,
          images,
          description: t?.deff || t?.description || t?.t_desc || "",
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

  if (pageLoading) return <Loader text="Yuklanmoqda..." />;
  if (pageError) return <Loader text={pageError} />;

  // 1) Groups view
  if (!selectedGroup) {
    return (
      <div className="p-8 lg:p-12 max-w-[1400px] mx-auto animate-in fade-in duration-500">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <div className="inline-block px-3 py-1 bg-green-100 text-green-700 rounded-full text-[10px] font-black uppercase tracking-widest mb-3 italic">
              Zaxira Nazorati
            </div>
            <h1 className="text-5xl font-black text-slate-900 tracking-tighter">
              Omborxona
            </h1>
          </div>

          <button className="bg-[#43a047] text-white px-8 py-4 rounded-2xl font-black flex items-center gap-3 hover:shadow-xl hover:bg-green-700 transition-all active:scale-95 uppercase text-sm">
            <Plus size={20} strokeWidth={3} /> Yangi nav qo'shish
          </button>
        </header>

        <div className="flex items-center gap-2 mb-8">
          <h2 className="text-xl font-black text-slate-400 uppercase tracking-widest italic">
            Guruhlar
          </h2>
          <div className="h-[2px] flex-1 bg-slate-100" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
          {groups.map((group, idx) => (
            <GroupCard
              key={group.id}
              group={group}
              index={idx}
              tick={tick}
              toWebImgUrl={toWebImgUrl}
              onClick={() => setSelectedGroup(group)}
            />
          ))}
        </div>
      </div>
    );
  }

  // 2) Sorts view
  return (
    <div className="p-8 lg:p-12 max-w-[1400px] mx-auto animate-in slide-in-from-right duration-500">
      <button
        onClick={() => {
          setSelectedGroup(null);
          setSelectedSort(null);
        }}
        className="mb-10 flex items-center gap-3 font-black text-slate-400 hover:text-green-600 transition-colors uppercase text-xs tracking-widest"
      >
        <ArrowLeft size={18} strokeWidth={3} /> Guruhlarga qaytish
      </button>

      <div className="mb-12">
        <h2 className="text-4xl font-black text-slate-900 uppercase italic">
          {selectedGroup.groupName}{" "}
          <span className="text-green-600">Navlari</span>
        </h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {selectedGroup.sorts.map((sort) => (
          <SortCard
            key={sort.id}
            sort={sort}
            toWebImgUrl={toWebImgUrl}
            onClick={() => setSelectedSort(sort)}
          />
        ))}
      </div>

      {/* Modal (o'zgarmagan, faqat image url toWebImgUrl bilan) */}
      {selectedSort && (
        <div className="fixed inset-0 bg-slate-900/90 backdrop-blur-md z-50 flex items-center justify-center p-6">
          <div className="bg-white w-full max-w-6xl h-[85vh] rounded-[45px] overflow-hidden flex flex-col md:flex-row shadow-2xl animate-in zoom-in duration-300">
            <div className="w-full md:w-[60%] h-full bg-black relative">
              <img
                src={toWebImgUrl(selectedSort.images?.[0])}
                className="w-full h-full object-contain"
                alt="Sort"
              />
            </div>

            <div className="w-full md:w-[40%] p-12 overflow-y-auto flex flex-col bg-white">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-4xl font-black text-slate-900 uppercase italic tracking-tighter leading-none">
                  {selectedSort.name}
                </h2>
                <button
                  onClick={() => setSelectedSort(null)}
                  className="p-2 hover:bg-slate-100 rounded-full transition-colors"
                >
                  <X size={28} />
                </button>
              </div>

              <div className="h-1.5 w-20 bg-green-500 rounded-full mb-10" />

              <div className="space-y-4 mb-10">
                <h4 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em]">
                  Sifat bo'yicha zaxira
                </h4>

                <div className="grid grid-cols-1 gap-3">
                  <div className="p-4 bg-green-50 rounded-2xl flex justify-between items-center border border-green-100">
                    <span className="font-black text-green-700">1-NAV</span>
                    <span className="text-2xl font-black text-green-800">
                      {selectedSort.nav1} ta
                    </span>
                  </div>

                  <div className="p-4 bg-orange-50 rounded-2xl flex justify-between items-center border border-orange-100">
                    <span className="font-black text-orange-600">2-NAV</span>
                    <span className="text-2xl font-black text-orange-700">
                      {selectedSort.nav2} ta
                    </span>
                  </div>

                  <div className="p-4 bg-slate-50 rounded-2xl flex justify-between items-center border border-slate-200">
                    <span className="font-black text-slate-500">3-NAV</span>
                    <span className="text-2xl font-black text-slate-800">
                      {selectedSort.nav3} ta
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex-1">
                <h4 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4">
                  Nav haqida ma'lumot
                </h4>
                <p className="text-lg font-bold text-slate-600 leading-relaxed italic">
                  {selectedSort.description ||
                    "Ushbu nav haqida qo'shimcha ma'lumot mavjud emas."}
                </p>
              </div>

              <div className="mt-12 pt-8 border-t border-slate-100 flex justify-between items-center">
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    Umumiy soni
                  </p>
                  <p className="text-4xl font-black text-slate-900">
                    {Number(selectedSort.nav1 || 0) +
                      Number(selectedSort.nav2 || 0) +
                      Number(selectedSort.nav3 || 0)}
                  </p>
                </div>

                <button className="bg-slate-900 text-white px-8 py-4 rounded-2xl font-black hover:bg-green-600 transition-all uppercase text-xs tracking-widest">
                  Tahrirlash
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}