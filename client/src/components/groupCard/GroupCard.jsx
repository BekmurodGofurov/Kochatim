import React from "react";
import "./GroupCard.scss";

const FALLBACK =
  "https://images.unsplash.com/photo-1560806887-1e4cd0b6bcd6?w=600";

export default function GroupCard({
  group,
  index = 0,
  tick = 0,
  toWebImgUrl,
  onClick,
}) {
  const imgsRaw = group?.groupImages?.length ? group.groupImages : [FALLBACK];
  const imgIndex = imgsRaw.length ? (tick + index) % imgsRaw.length : 0;

  const raw = imgsRaw[imgIndex];
  const imgSrc = toWebImgUrl ? toWebImgUrl(raw) : raw;

  return (
    <div className="inv-groupCard" onClick={onClick} role="button" tabIndex={0}>
      <div className="inv-groupCard__media">
        <img src={imgSrc} alt={group.groupName} />
      </div>

      <div className="inv-groupCard__body">
        <h2 className="inv-groupCard__title">{group.groupName}</h2>
        <p className="inv-groupCard__count">
          {Number(group.totalValue || 0).toLocaleString()} dona
        </p>
      </div>
    </div>
  );
}