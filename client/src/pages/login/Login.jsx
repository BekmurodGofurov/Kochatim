import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Login.css";

export default function Login() {
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async () => {
    setError("");

    if (!userId.trim()) {
      setError("Telegram user_id kiriting");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/auth/user-id-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ u_id: userId }),
      });

      const data = await res.json();

      if (!data.ok) {
        setError(
          data.error?.message ||
          "User topilmadi. Botga /start bering."
        );
        return;
      }

      localStorage.setItem("session_token", data.data.session_token);
      navigate("/", { replace: true });
    } catch {
      setError("Server bilan bog‘lanib bo‘lmadi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">Ko‘chatim</h1>
        <p className="login-subtitle">
          Inventaringizni ko‘rish uchun tizimga kiring
        </p>

        <label className="login-label">Telegram ID orqli kirting</label>
        <input
          className="login-input"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Telegram ID kiriting..."
        />

        <p className="login-hint">
          Agar ro‘yxatdan o‘tmagan bo‘lsangiz, Telegram botga kirib
          <b> /start </b> buyrug‘ini bering.
        </p>

        {error && <div className="login-error">{error}</div>}

        <button
          className="login-button"
          onClick={submit}
          disabled={loading}
        >
          {loading ? "Tekshirilmoqda..." : "Kirish"}
        </button>
      </div>
    </div>
  );
}