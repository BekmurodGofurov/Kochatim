// src/components/transaction-card/TransactionCard.jsx
import React from "react";
import { Calendar, Wallet, Clock } from "lucide-react";
import "./TransactionCard.scss";

const formatPrice = (p) => {
  if (p >= 1000000) return (p / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
  if (p >= 1000) return (p / 1000).toFixed(1).replace(/\.0$/, "") + "K";
  return p;
};

export default function TransactionCard({ item }) {
  const name = item?.name ?? "-";
  const category = item?.category ?? "-";
  const dateStr = item?.date ?? "-";
  const qty = Number(item?.qty || 0);
  const price = Number(item?.price || 0);

  // Split date into time and full date
  // Expected format: "HH:mm DD.MM.YYYY"
  const [time, fullDate] = dateStr.includes(" ") ? dateStr.split(" ") : [dateStr, ""];

  return (
    <div className="tx-card">
      <div className="tx-card__left">
        <div className="tx-card__badge">
          <Wallet size={18} />
        </div>

        <div className="tx-card__meta">
          <div className="tx-card__name" title={name}>
            {name}
          </div>

          <div className="tx-card__sub">
            <span className="tx-card__tag">{category}</span>

            <div className="tx-card__info">
              <span className="tx-card__time-count">
                <Clock size={12} />
                <span>
                  {time} • {qty.toLocaleString()} dona
                </span>
              </span>
              {fullDate && (
                <span className="tx-card__date-only">
                  <Calendar size={12} />
                  <span>{fullDate}</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="tx-card__right">
        <div className="tx-card__price">
          <span className="tx-card__price-full">+{price.toLocaleString()} so'm</span>
          <span className="tx-card__price-short">+{formatPrice(price)} so'm</span>
        </div>
      </div>
    </div>
  );
}