// src/pages/login/Login.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import Header from "../../components/header/Header";
import "./Login.scss";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function Login() {
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { theme } = useTheme(); // Removed toggleTheme since it's in Header now

  useEffect(() => {
    const token = localStorage.getItem("session_token");
    if (token) {
      navigate("/dashboard", { replace: true });
    }
  }, [navigate]);

  const submit = async () => {
    setError("");

    if (!userId.trim()) {
      setError("Telegram user_id kiriting");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/user-id-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ u_id: userId }),
      });

      const data = await res.json().catch(() => null);

      if (!data?.ok) {
        setError(data?.error?.message || "User topilmadi. Botga /start bering.");
        return;
      }

      localStorage.setItem("session_token", data.data.session_token);
      navigate("/dashboard", { replace: true });
    } catch {
      setError("Server bilan bog‘lanib bo‘lmadi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`login-page ${theme}-mode`}>
      <Header />
      <div className="login">
        <div className="login__card">
          <h1 className="login__title">Ko‘chatim</h1>
          <p className="login__subtitle">Inventaringizni ko‘rish uchun tizimga kiring</p>

          <label className="login__label">Telegram ID orqali kiring</label>

          <input
            className="login__input"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Telegram ID kiriting..."
            inputMode="numeric"
          />

          <p className="login__hint">
            Agar ro‘yxatdan o‘tmagan bo‘lsangiz, Telegram botga kirib <b>/start</b> buyrug‘ini bering.
          </p>

          {error && <div className="login__error">{error}</div>}

          <button className="login__button" onClick={submit} disabled={loading}>
            {loading ? "Tekshirilmoqda..." : "Kirish"}
          </button>
        </div>
      </div>
    </div>
  );
}