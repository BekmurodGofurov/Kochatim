import React from "react";
import "./Loader.scss";

export default function Loader({ text = "Loading..." }) {
  return (
    <div className="app-loader">
      <div className="app-loader-spinner"></div>
      <p className="app-loader-text">{text}</p>
    </div>
  );
}