// src/pages/Inventory/components/GroupCard.jsx
import React from "react";

const FALLBACK =
  "https://images.unsplash.com/photo-1560806887-1e4cd0b6bcd6?w=600";

export default function GroupCard({
  group,
  index = 0,
  tick = 0,
  toWebImgUrl, // function(raw) => final img url
  onClick,
}) {
  const imgsRaw =
    group?.groupImages?.length ? group.groupImages : [FALLBACK];

  const imgIndex = imgsRaw.length ? (tick + index) % imgsRaw.length : 0;
  const raw = imgsRaw[imgIndex];
  const imgSrc = toWebImgUrl ? toWebImgUrl(raw) : raw;

  return (
    <div
      onClick={onClick}
      className="group bg-white rounded-[35px] overflow-hidden shadow-sm hover:shadow-2xl hover:-translate-y-3 transition-all duration-500 cursor-pointer"
    >
      <div className="h-64 overflow-hidden">
        <img
          src={imgSrc}
          alt={group.groupName}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
        />
      </div>

      <div className="p-8 text-center bg-white">
        <h2 className="text-3xl font-black text-slate-800 uppercase italic tracking-tighter">
          {group.groupName}
        </h2>

        <p className="text-xl font-bold text-red-500 mt-2">
          {Number(group.totalValue || 0).toLocaleString()} dona
        </p>
      </div>
    </div>
  );
}