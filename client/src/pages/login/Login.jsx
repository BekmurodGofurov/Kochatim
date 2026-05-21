// src/pages/login/Login.jsx
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import { apiFetch } from "../../api/https";
import Header from "../../components/header/Header";
import "./Login.scss";

const CODE_LENGTH = 6;

const ERROR_MESSAGES = {
  CODE_NOT_FOUND: "Kod topilmadi. Botdan yangi kod oling.",
  CODE_EXPIRED: "Kodning muddati o'tgan. Botdan yangi kod oling.",
  CODE_USED: "Bu kod allaqachon ishlatilgan. Botdan yangi kod oling.",
};

export default function Login() {
  const [digits, setDigits] = useState(Array(CODE_LENGTH).fill(""));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRefs = useRef([]);
  const navigate = useNavigate();
  const { theme } = useTheme();

  const submit = async (codeDigits) => {
    const code = codeDigits.join("");
    if (code.length !== CODE_LENGTH) return;

    setError("");
    setLoading(true);
    try {
      const data = await apiFetch("/auth/verify-code", {
        method: "POST",
        body: { code },
      });
      localStorage.setItem("session_token", data.session_token);
      localStorage.setItem("u_id", String(data.u_id));
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const apiCode = err?.code || err?.data?.code;
      setError(ERROR_MESSAGES[apiCode] || "Noto'g'ri kod. Qayta urinib ko'ring.");
      setDigits(Array(CODE_LENGTH).fill(""));
      setTimeout(() => inputRefs.current[0]?.focus(), 0);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (index, e) => {
    const val = e.target.value.replace(/\D/g, "");
    if (!val) return;

    const newDigits = [...digits];
    newDigits[index] = val[val.length - 1];
    setDigits(newDigits);
    setError("");

    if (index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }

    if (newDigits.every((d) => d !== "")) {
      submit(newDigits);
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace") {
      if (digits[index]) {
        const newDigits = [...digits];
        newDigits[index] = "";
        setDigits(newDigits);
      } else if (index > 0) {
        inputRefs.current[index - 1]?.focus();
        const newDigits = [...digits];
        newDigits[index - 1] = "";
        setDigits(newDigits);
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, CODE_LENGTH);
    if (!pasted) return;

    const newDigits = Array(CODE_LENGTH).fill("");
    pasted.split("").forEach((ch, i) => { newDigits[i] = ch; });
    setDigits(newDigits);
    setError("");

    const nextEmpty = newDigits.findIndex((d) => d === "");
    const focusIndex = nextEmpty === -1 ? CODE_LENGTH - 1 : nextEmpty;
    inputRefs.current[focusIndex]?.focus();

    if (newDigits.every((d) => d !== "")) {
      submit(newDigits);
    }
  };

  const isFilled = digits.every((d) => d !== "");

  return (
    <div className={`login-page ${theme}-mode`}>
      <Header />
      <div className="login">
        <div className="login__card">
          <h1 className="login__title">Ko'chatim</h1>
          <p className="login__subtitle">Inventaringizni ko'rish uchun tizimga kiring</p>

          <label className="login__label">Telegram botdan olgan kodingizni kiriting</label>

          <div className="login__otp-row" onPaste={handlePaste}>
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                className={`login__otp-box${digit ? " filled" : ""}`}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(i, e)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                disabled={loading}
                autoFocus={i === 0}
              />
            ))}
          </div>

          <p className="login__hint">
            Telegram botga <b>/login</b> yozing va 6 xonali kodni oling.{" "}
            Botga o'tish:{" "}
            <b>
              <a href="https://t.me/kochatim_bot" target="_blank" rel="noopener noreferrer">
                @Kochatim_Bot
              </a>
            </b>
          </p>

          {error && <div className="login__error">{error}</div>}

          <button
            className="login__button"
            onClick={() => submit(digits)}
            disabled={loading || !isFilled}
          >
            {loading ? "Tekshirilmoqda..." : "Kirish"}
          </button>
        </div>
      </div>
    </div>
  );
}
