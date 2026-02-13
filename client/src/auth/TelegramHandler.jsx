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
        // 1. Telegram SDK ni tekshirish
        const tg = window.Telegram?.WebApp;

        // Agar tg obyekti bo'lsa, demak bu TMA muhiti bo'lishi EHTIMOL
        // Lekin initData bo'lmaguncha biz kimmizligini bilmaymiz
        const initData = tg?.initData;
        const hasTgObject = !!tg;
        const isTmaEnvironment = !!initData;

        // Debug uchun konsolga chiqaramiz
        console.log("TMA Check:", { hasTgObject, initDataLength: initData?.length, isTmaEnvironment });

        if (hasTgObject) {
            sessionStorage.setItem("tg_detected", "true");
            tg.ready();
            tg.expand();
        }

        if (isTmaEnvironment) {
            sessionStorage.setItem("is_tma", "true");
        } else {
            sessionStorage.removeItem("is_tma");
        }

        // 2. TMA deb gumon qilsak debug sahifasiga yo'naltiramiz
        if (hasTgObject && location.pathname !== "/debug-tma") {
            navigate("/debug-tma", { replace: true });
            setIsChecking(false);
            return;
        }

        const token = localStorage.getItem("session_token");

        // 3. TMA bo'lsa va hali login qilinmagan bo'lsa (Debugdan keyin ishlaydi)
        if (isTmaEnvironment && !token && !loginAttempted.current) {
            loginAttempted.current = true;
            setIsChecking(true);

            api
                .telegramLogin(initData)
                .then((res) => {
                    localStorage.setItem("session_token", res.session_token);
                    localStorage.setItem("u_id", res.u_id);

                    if (res.is_registered) {
                        // Ro'yxatdan o'tgan bo'lsa dashboardga o'tkazamiz
                        navigate("/dashboard", { replace: true });
                    } else {
                        setNotRegistered(true);
                    }
                })
                .catch((err) => {
                    console.error("Telegram auto-login failed:", err);
                    if (err.status === 401) {
                        setError("Telegram orqali tasdiqlashda xatolik yuz berdi. Iltimos, botni qayta ishga tushiring.");
                    } else {
                        setError("Serverga ulanishda xatolik yuz berdi. Internetni tekshiring.");
                    }
                })
                .finally(() => {
                    setIsChecking(false);
                });
        }
        // 4. TMA bo'lsa va allaqachon login qilingan bo'lsa (Home yoki Login sahifasida turganda)
        else if (isTmaEnvironment && token && (location.pathname === "/" || location.pathname === "/login")) {
            navigate("/dashboard", { replace: true });
            setIsChecking(false);
        }
        // 5. Normal brauzer bo'lsa yoki barcha tekshiruvlar tugagan bo'lsa
        else {
            setIsChecking(false);
        }
    }, [navigate, location.pathname]);

    // Tekshirish vaqtida loader ko'rsatamiz
    if (isChecking) {
        return (
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", backgroundColor: "var(--bg-color, #fff)" }}>
                <div className="loader-spinner"></div> {/* Agar CSS loader bo'lsa */}
                <p style={{ marginTop: "20px", fontWeight: "500" }}>Kutib turing...</p>
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
