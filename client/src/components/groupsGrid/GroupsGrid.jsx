import React from "react";
import GroupCard from "../groupCard/GroupCard";
import { toWebImgUrl } from "../../utils/imageUtils";

export default function GroupsGrid({ groups, tick = 0, className = "", onGroupClick }) {
  return (
    <div className={className}>
      {groups.map((group, idx) => (
        <GroupCard
          key={group.id}
          group={group}
          index={idx}
          tick={tick}
          toWebImgUrl={toWebImgUrl}
          onClick={() => onGroupClick(group)}
        />
      ))}
    </div>
  );
}
