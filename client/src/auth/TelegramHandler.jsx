import { useEffect, useState, useRef } from "react";
import { api } from "../api/endpoints";
import { useNavigate, useLocation } from "react-router-dom";

export default function TelegramHandler({ children }) {
    const [isChecking, setIsChecking] = useState(true);
    const [error, setError] = useState(null);
    const [notRegistered, setNotRegistered] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const loginAttempted = useRef(false);

    useEffect(() => {
        let checkCount = 0;
        const checkInterval = setInterval(() => {
            const tg = window.Telegram?.WebApp;
            const initData = tg?.initData;
            const hasTgObject = !!tg;
            const isTmaEnvironment = !!initData;

            console.log(`TMA Check #${checkCount}:`, { hasTgObject, isTmaEnvironment });

            if (hasTgObject) {
                sessionStorage.setItem("tg_detected", "true");
                tg.ready();
                tg.expand();

                if (isTmaEnvironment) {
                    sessionStorage.setItem("is_tma", "true");
                }

                // Majburiy debugga o'tkazamiz
                if (location.pathname !== "/debug-tma") {
                    navigate("/debug-tma", { replace: true });
                }
                clearInterval(checkInterval);
                setIsChecking(false);
            }

            checkCount++;
            if (checkCount > 15) { // 3 soniya kutamiz
                clearInterval(checkInterval);
                setIsChecking(false);
                sessionStorage.setItem("tg_detected", "false");
            }
        }, 200);

        return () => clearInterval(checkInterval);
    }, [navigate, location.pathname]);

    // Tekshirish vaqtida loader ko'rsatamiz
    if (isChecking) {
        return (
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", backgroundColor: "var(--bg-color, #fff)", textAlign: "center", padding: "20px" }}>
                <div style={{ width: "40px", height: "40px", border: "4px solid #f3f3f3", borderTop: "4px solid var(--primary-color, #2e7d32)", borderRadius: "50%", animation: "spin 1s linear infinite" }}></div>
                <p style={{ marginTop: "20px", fontWeight: "500" }}>Tizim tekshirilmoqda...</p>
                <p style={{ fontSize: "12px", color: "#666" }}>Telegram SDK qidirilmoqda... {window.Telegram ? "✅ Topildi" : "❌ Hali yo'q"}</p>
                <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    // Ro'yxatdan o'tmagan TMA foydalanuvchisi uchun xabar
    if (notRegistered) {
        return (
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", textAlign: "center", padding: "20px", backgroundColor: "var(--bg-color, #fff)" }}>
                <h2 style={{ color: "var(--primary-color, #2e7d32)" }}>Diqqat!</h2>
                <p>Siz hali ro'yxatdan o'tmagansiz.</p>
                <p>Botga qaytib <b>📞 Telefon raqamni yuborish</b> tugmasini bosing va qayta urinib ko'ring.</p>
                <button
                    onClick={() => window.Telegram?.WebApp?.close()}
                    style={{ marginTop: "20px", padding: "12px 24px", borderRadius: "10px", border: "none", backgroundColor: "var(--primary-color, #2e7d32)", color: "#fff", cursor: "pointer", fontWeight: "bold" }}
                >
                    Botga qaytish
                </button>
            </div>
        );
    }

    // Xatolik yuz berganda
    if (error) {
        return (
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", padding: "20px", textAlign: "center", backgroundColor: "var(--bg-color, #fff)" }}>
                <p style={{ color: "red", fontWeight: "bold", marginBottom: "15px" }}>{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    style={{ padding: "10px 20px", borderRadius: "8px", border: "1px solid #ccc", background: "#f5f5f5" }}
                >
                    Qaytadan urinish
                </button>
            </div>
        );
    }

    // Agar hamma narsa joyida bo'lsa, asosiy ilovani ko'rsatamiz
    return children;
}
