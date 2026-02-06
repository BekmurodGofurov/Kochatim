// src/pages/sales/Sales.jsx
import React, { useEffect, useMemo, useState } from "react";
import { History, TrendingUp } from "lucide-react";
import { useDashboard } from "../../context/DashboardContext";
import { getSessionToken } from "../../api/https";

import Loader from "../../components/loader/Loader";
import PieCard from "../../components/pieCard/PieCard";
import TransactionCard from "../../components/transaction-card/TransactionCard";

import "./Sales.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const PIE_COLORS = ["#16a34a", "#2563eb", "#f59e0b", "#db2777", "#8b5cf6", "#06b6d4"];


export default function Sales() {
  const [visibleCount, setVisibleCount] = useState(10);
  const [history, setHistory] = useState([]);
  const [pie, setPie] = useState([]);

  const {
    salesData: data,
    salesLoading: loading,
    salesError: errMsg,
    fetchSales,
  } = useDashboard();

  useEffect(() => {
    fetchSales();
  }, [fetchSales]);

  useEffect(() => {
    if (!data) return;

    const rawHistory = Array.isArray(data?.history)
      ? data.history
      : Array.isArray(data?.sales_history)
        ? data.sales_history
        : Array.isArray(data?.sales)
          ? data.sales
          : [];

    const normalizedHistory = rawHistory.map((x, idx) => ({
      id: x?.id ?? x?.sale_id ?? idx,
      name: x?.name ?? x?.t_name ?? x?.sort_name ?? "-",
      category: x?.category ?? x?.c_name ?? x?.group_name ?? "-",
      date: (() => {
        const dStr = x?.date ?? x?.created_at ?? x?.sold_at;
        if (!dStr) return "-";
        const d = new Date(dStr);
        if (isNaN(d.getTime())) return dStr;

        const day = String(d.getDate()).padStart(2, "0");
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const year = d.getFullYear();
        const hours = String(d.getHours()).padStart(2, "0");
        const minutes = String(d.getMinutes()).padStart(2, "0");

        return `${hours}:${minutes} ${day}.${month}.${year}`;
      })(),
      qty:
        Number(
          x?.qty ??
          x?.quantity ??
          x?.count ??
          (Number(x?.q1_sold || 0) + Number(x?.q2_sold || 0) + Number(x?.q3_sold || 0))
        ) || 0,
      price: Number(x?.price ?? x?.total_price ?? x?.sum ?? 0) || 0,
    }));

    const rawPie = Array.isArray(data?.pie)
      ? data.pie
      : Array.isArray(data?.monthly_pie)
        ? data.monthly_pie
        : Array.isArray(data?.groups)
          ? data.groups
          : [];

    const normalizedPie = rawPie.map((x, idx) => ({
      name: x?.name ?? x?.c_name ?? x?.groupName ?? `Guruh ${idx + 1}`,
      value: Number(x?.value ?? x?.sum ?? x?.total ?? 0) || 0,
      color: x?.color ?? x?.hex ?? PIE_COLORS[idx % PIE_COLORS.length],
    }));

    setHistory(normalizedHistory);
    setPie(normalizedPie);
  }, [data]);

  const totalRevenue = useMemo(
    () => pie.reduce((sum, item) => sum + Number(item.value || 0), 0),
    [pie]
  );

  const shownHistory = useMemo(() => history.slice(0, visibleCount), [history, visibleCount]);

  const loadMore = () => setVisibleCount((p) => p + 10);

  const tooltipFormatter = (value, _name, props) => {
    const v = Number(value || 0);
    const pct = totalRevenue ? ((v / totalRevenue) * 100).toFixed(1) : "0.0";
    return [`${v.toLocaleString()} so'm (${pct}%)`, props?.payload?.name || "Guruh"];
  };

  if (loading || (!data && getSessionToken())) return <Loader text="Yuklanmoqda..." />;
  if (errMsg) return <Loader text={errMsg} />;

  return (
    <div className="sales-page">
      {/* LEFT */}
      <div className="sales-card">
        <div className="sales-head">
          <div className="sales-head__icon sales-head__icon--green">
            <History size={22} />
          </div>
          <h2 className="sales-head__title">Sotuvlar tarixi</h2>
        </div>

        <div className="sales-list">
          {shownHistory.map((item) => (
            <TransactionCard key={item.id} item={item} />
          ))}
        </div>

        {visibleCount < history.length && (
          <button type="button" onClick={loadMore} className="sales-more">
            Yana yuklash (+10)
          </button>
        )}
      </div>

      {/* RIGHT */}
      <div className="sales-card">
        <div className="sales-head sales-head--spaced">
          <div className="sales-head__left">
            <div className="sales-head__icon sales-head__icon--blue">
              <TrendingUp size={22} />
            </div>
            <div>
              <h2 className="sales-head__title">Daromad tahlili</h2>
              <div className="sales-head__subtitle">Oylik hisobot (%)</div>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="sales-pieWrap">
          <div className="sales-pieOuter">
            <div className="sales-pieChart">
              <PieCard
                data={pie}
                colors={PIE_COLORS}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius="80%"
                stroke="#fff"
                strokeWidth={0}
                tooltipFormatter={tooltipFormatter}
              />
            </div>
          </div>

          {/* Total pastda */}
          <div className="sales-total">
            <div className="sales-total__kicker">Jami tushum</div>
            <div className="sales-total__value">{Number(totalRevenue || 0).toLocaleString()}</div>
            <div className="sales-total__unit">so&apos;m</div>
          </div>
        </div>

        {/* Breakdown */}
        <div className="sales-breakdown">
          <div className="sales-breakdown__title">Guruhlar bo&apos;yicha tushum:</div>

          <div className="sales-breakdown__list">
            {pie.map((item, i) => {
              const v = Number(item.value || 0);
              const pct = totalRevenue ? (v / totalRevenue) * 100 : 0;

              return (
                <div className="sales-breakRow" key={i}>
                  <div className="sales-breakRow__top">
                    <div className="sales-breakRow__name">
                      <span className="sales-dot" style={{ backgroundColor: item.color }} />
                      <span className="sales-breakRow__label" title={item.name}>
                        {item.name}
                      </span>
                    </div>

                    <div className="sales-breakRow__sum">{v.toLocaleString()} so&apos;m</div>
                  </div>

                  <div className="sales-bar">
                    <div
                      className="sales-bar__fill"
                      style={{ width: `${pct}%`, backgroundColor: item.color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}