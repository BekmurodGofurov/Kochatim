import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx' // Nuqta va slashga e'tibor bering
import "./style/global.scss";

// Telegram WebApp ichki postEvent loglarini konsolda tozalash
if (typeof window !== "undefined") {
  const _origLog = console.log;
  console.log = (...args) => {
    if (typeof args[0] === "string" && args[0].startsWith("[Telegram.WebView]")) return;
    _origLog.apply(console, args);
  };
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)