import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import "./PieCard.scss";

export default function PieCard({
  data = [],
  colors = [],
  dataKey = "value",
  nameKey = "name",
  cx = "50%",
  cy = "50%",
  outerRadius = 160,
  innerRadius,
  stroke = "#fff",
  strokeWidth = 4,
  cellClassName,
  onSliceClick,
  tooltipFormatter,
  labelLine,
  label,
}) {
  const safeColors = Array.isArray(colors) && colors.length ? colors : ["#3b82f6"];

  return (
    <div className="pie-card">
      <div className="pie-card__chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey={dataKey}
              nameKey={nameKey}
              cx={cx}
              cy={cy}
              outerRadius={outerRadius}
              innerRadius={innerRadius}
              stroke={stroke}
              strokeWidth={strokeWidth}
              labelLine={labelLine}
              label={label}
            >
              {(data || []).map((entry, index) => (
                <Cell
                  key={`pc-${index}`}
                  fill={entry?.color || safeColors[index % safeColors.length]}
                  className={cellClassName}
                  onClick={onSliceClick ? () => onSliceClick(entry?.original ?? entry) : undefined}
                />
              ))}
            </Pie>

            <Tooltip formatter={tooltipFormatter} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}