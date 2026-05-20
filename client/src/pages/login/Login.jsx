// src/pages/login/Login.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import { apiFetch } from "../../api/https";
import Header from "../../components/header/Header";
import "./Login.scss";

export default function Login() {
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { theme } = useTheme();

  const submit = async () => {
    setError("");

    if (!userId.trim()) {
      setError("Telegram ID kiriting");
      return;
    }

    setLoading(true);
    try {
      const data = await apiFetch("/auth/user-id-login", {
        method: "POST",
        body: { u_id: Number(userId) },
      });
      localStorage.setItem("session_token", data.session_token);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message || "Foydalanuvchi topilmadi. Botga /start bering.");
    } finally {
      setLoading(false);
    }
  };

  const isIdValid = userId.length >= 8 && userId.length <= 12;

  const handleChange = (e) => {
    const val = e.target.value.replace(/\D/g, ""); // Faqat raqamlarni qoldirish
    if (val.length <= 12) {
      setUserId(val);
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
            type="text"
            className="login__input"
            value={userId}
            onChange={handleChange}
            placeholder="Telegram ID kiriting..."
            inputMode="numeric"
            maxLength="12"
          />

          <p className="login__hint">
            Agar ro‘yxatdan o‘tmagan bo‘lsangiz, <b><a href="https://t.me/kochatim_bot" target="_blank" rel="noopener noreferrer">@Kochatim_Bot</a></b> telegram bot orqali royhatdan o'ting va <b>Telegram ID</b> ga ega bo'ling.
          </p>

          {error && <div className="login__error">{error}</div>}

          <button
            className="login__button"
            onClick={submit}
            disabled={loading || !isIdValid}
          >
            {loading ? "Tekshirilmoqda..." : "Kirish"}
          </button>
        </div>
      </div>
    </div>
  );
}