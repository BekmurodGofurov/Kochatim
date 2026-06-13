import React from "react";
import SortCard from "../sortCard/SortCard";
import { toWebImgUrl } from "../../utils/imageUtils";

export default function SortsGrid({ sorts, className = "", onSortClick }) {
  return (
    <div className={className}>
      {sorts.map((sort) => (
        <SortCard
          key={sort.id}
          sort={sort}
          toWebImgUrl={toWebImgUrl}
          onClick={() => onSortClick(sort)}
        />
      ))}
    </div>
  );
}
