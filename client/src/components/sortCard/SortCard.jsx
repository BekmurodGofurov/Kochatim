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
          <div className="inv-sortRow">
            <span className="inv-sortRow__label">1-NAV</span>
            <span className="inv-sortRow__value inv-sortRow__value--a">
              {sort.nav1}
            </span>
          </div>

          <div className="inv-sortRow">
            <span className="inv-sortRow__label">2-NAV</span>
            <span className="inv-sortRow__value inv-sortRow__value--b">
              {sort.nav2}
            </span>
          </div>

          <div className="inv-sortRow">
            <span className="inv-sortRow__label">3-NAV</span>
            <span className="inv-sortRow__value inv-sortRow__value--c">
              {sort.nav3}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}