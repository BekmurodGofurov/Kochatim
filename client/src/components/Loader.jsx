import React from "react";
import "./Loader.css";

export default function Loader({ text = "Yuklanmoqda..." }) {
  return (
    <div className="app-loader">
      <div className="app-loader-spinner"></div>
      <p className="app-loader-text">{text}</p>
    </div>
  );
}