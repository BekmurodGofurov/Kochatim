import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import "./PieCard.css";

/**
 * Bu component STYLE QO'SHMAYDI.
 * Siz Dashboard.jsx ichida o'zingizdagi wrapper div classlarini ishlatasiz:
 * - dashboard-pie-wrap
 * - dashboard-right-pie
 *
 * Shu sababli UI o'zgarmaydi.
 */
export default function PieCard({
  data = [],
  colors = [],
  dataKey = "value",
  cx = "50%",
  cy = "50%",
  outerRadius = 160,
  innerRadius,
  stroke = "#fff",
  strokeWidth = 4,
  cellClassName,
  onSliceClick, // (payload) => void
  tooltipFormatter, // (value, name) => [label, name]
  labelLine,
  label,
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx={cx}
          cy={cy}
          outerRadius={outerRadius}
          innerRadius={innerRadius}
          dataKey={dataKey}
          stroke={stroke}
          strokeWidth={strokeWidth}
          labelLine={labelLine}
          label={label}
        >
          {(data || []).map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry?.color || colors[index % (colors.length || 1)]}
              className={cellClassName}
              onClick={
                onSliceClick
                  ? () => {
                      // entry.original bo'lsa shuni yuboramiz, bo'lmasa entry
                      onSliceClick(entry?.original ?? entry);
                    }
                  : undefined
              }
            />
          ))}
        </Pie>

        <Tooltip formatter={tooltipFormatter} />
      </PieChart>
    </ResponsiveContainer>
  );
}