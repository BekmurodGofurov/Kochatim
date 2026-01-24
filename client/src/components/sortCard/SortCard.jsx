// src/pages/Inventory/components/SortCard.jsx
import React from "react";

const FALLBACK =
  "https://images.unsplash.com/photo-1560806887-1e4cd0b6bcd6?w=400";

export default function SortCard({ sort, toWebImgUrl, onClick }) {
  const raw = sort?.images?.[0] || FALLBACK;
  const imgSrc = toWebImgUrl ? toWebImgUrl(raw) : raw;

  return (
    <div
      onClick={onClick}
      className="group bg-white rounded-[30px] overflow-hidden shadow-sm hover:shadow-2xl hover:-translate-y-3 transition-all duration-500 cursor-pointer border border-slate-50"
    >
      <div className="h-48 overflow-hidden bg-slate-100">
        <img
          src={imgSrc}
          alt={sort.name}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
        />
      </div>

      <div className="p-6">
        <h3 className="font-black text-slate-800 uppercase text-lg mb-4 truncate">
          {sort.name}
        </h3>

        <div className="space-y-2">
          <div className="flex justify-between items-center bg-slate-50 p-2 px-4 rounded-xl">
            <span className="text-[10px] font-black text-slate-400 uppercase">
              1-Nav
            </span>
            <span className="font-black text-green-600">{sort.nav1}</span>
          </div>

          <div className="flex justify-between items-center bg-slate-50 p-2 px-4 rounded-xl">
            <span className="text-[10px] font-black text-slate-400 uppercase">
              2-Nav
            </span>
            <span className="font-black text-orange-500">{sort.nav2}</span>
          </div>

          <div className="flex justify-between items-center bg-slate-50 p-2 px-4 rounded-xl">
            <span className="text-[10px] font-black text-slate-400 uppercase">
              3-Nav
            </span>
            <span className="font-black text-slate-500">{sort.nav3}</span>
          </div>
        </div>
      </div>
    </div>
  );
}