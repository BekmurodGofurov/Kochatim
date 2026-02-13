import { useEffect, useState } from "react";
import { api } from "../api/endpoints";
import { useNavigate, useLocation } from "react-router-dom";

export default function TelegramHandler({ children }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [notRegistered, setNotRegistered] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        const initData = tg?.initData;

        if (initData) {
            // TMA muhitida ekanligimizni belgilaymiz
            sessionStorage.setItem("is_tma", "true");
            tg.expand();
        }

        const token = localStorage.getItem("session_token");

        // Agar TMA bo'lsa va hali login qilinmagan bo'lsa
        if (initData && !token) {
            setLoading(true);
            api
                .telegramLogin(initData)
                .then((res) => {
                    localStorage.setItem("session_token", res.session_token);
                    localStorage.setItem("u_id", res.u_id);

                    if (res.is_registered) {
                        // Agar ro'yxatdan o'tgan bo'lsa, dashboardga o'tkazamiz
                        navigate("/dashboard", { replace: true });
                    } else {
                        // Ro'yxatdan o'tmagan bo'lsa, xabar ko'rsatamiz
                        setNotRegistered(true);
                    }
                })
                .catch((err) => {
                    console.error("Telegram login failed", err);
                    setError("Telegram orqali kirishda xatolik yuz berdi.");
                })
                .finally(() => {
                    setLoading(false);
                });
        } else if (initData && token && location.pathname === "/") {
            // Allaqachon login bo'lgan bo'lsa va uy sahifasida bo'lsa
            navigate("/dashboard", { replace: true });
        }
    }, [navigate, location.pathname]);

    if (loading) {
        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", backgroundColor: "var(--bg-color, #fff)" }}>
                <p>Telegram orqali kirilmoqda...</p>
            </div>
        );
    }

    if (notRegistered) {
        return (
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", textAlign: "center", padding: "20px", backgroundColor: "var(--bg-color, #fff)" }}>
                <h2 style={{ color: "var(--primary-color, #2e7d32)" }}>Xush kelibsiz!</h2>
                <p>Websaytdan foydalanish uchun avval botda ro'yxatdan o'tishingiz kerak.</p>
                <p>Iltimos, botga qaytib <b>📞 Telefon raqamni yuborish</b> tugmasini bosing.</p>
                <button
                    onClick={() => window.Telegram?.WebApp?.close()}
                    style={{ marginTop: "20px", padding: "10px 20px", borderRadius: "8px", border: "none", backgroundColor: "var(--primary-color, #2e7d32)", color: "#fff", cursor: "pointer" }}
                >
                    Botga qaytish
                </button>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", color: "red", backgroundColor: "var(--bg-color, #fff)" }}>
                <p>{error}</p>
            </div>
        );
    }

    return children;
}
