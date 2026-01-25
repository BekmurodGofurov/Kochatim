// src/components/transaction-card/TransactionCard.jsx
import React from "react";
import { Calendar, Wallet } from "lucide-react";
import "./TransactionCard.scss";

export default function TransactionCard({ item }) {
  const name = item?.name ?? "-";
  const category = item?.category ?? "-";
  const date = item?.date ?? "-";
  const qty = Number(item?.qty || 0);
  const price = Number(item?.price || 0);

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

            <span className="tx-card__date">
              <Calendar size={12} />
              <span>
                {date} • {qty.toLocaleString()} dona
              </span>
            </span>
          </div>
        </div>
      </div>

      <div className="tx-card__right">
        <div className="tx-card__price">+{price.toLocaleString()} so&apos;m</div>
      </div>
    </div>
  );
}