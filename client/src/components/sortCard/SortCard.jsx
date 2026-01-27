import React from "react";
import "./SortCard.scss";

const FALLBACK =
  "https://images.unsplash.com/photo-1560806887-1e4cd0b6bcd6?w=400";

export default function SortCard({ sort, toWebImgUrl, onClick }) {
  const raw = sort?.images?.[0] || FALLBACK;
  const imgSrc = toWebImgUrl ? toWebImgUrl(raw) : raw;

  return (
    <div className="inv-sortCard" onClick={onClick} role="button" tabIndex={0}>
      <div className="inv-sortCard__media">
        <img src={imgSrc} alt={sort.name} />
      </div>

      <div className="inv-sortCard__body">
        <h3 className="inv-sortCard__title" title={sort.name}>
          {sort.name}
        </h3>

        <div className="inv-sortCard__rows">
          <div className="inv-sortCard__total">
            <span className="inv-sortCard__label">Jami soni</span>
            <span className="inv-sortCard__value">
              {(Number(sort.nav1 || 0) + Number(sort.nav2 || 0) + Number(sort.nav3 || 0)).toLocaleString()} ta
            </span>
          </div>

          <div className="inv-sortCard__date">
            <span className="inv-sortCard__label">
              {sort.updated_at ? "Yangilangan" : "Qo'shilgan"}
            </span>
            <span className="inv-sortCard__time">
              {(() => {
                const dStr = sort.updated_at || sort.created_at;
                if (!dStr) return "-";
                const d = new Date(dStr);
                if (isNaN(d.getTime())) return dStr;
                const day = String(d.getDate()).padStart(2, '0');
                const month = String(d.getMonth() + 1).padStart(2, '0');
                const year = d.getFullYear();
                const hours = String(d.getHours()).padStart(2, '0');
                const minutes = String(d.getMinutes()).padStart(2, '0');
                return `${hours}:${minutes} ${day}.${month}.${year}`;
              })()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}