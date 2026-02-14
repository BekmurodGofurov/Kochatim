import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://api.kochatim.uz";

/**
 * Bu komponent Telegram Mini App ichida ochilganini aniqlaydi 
 * va avtomatik loginni amalga oshiradi.
 */
export default function TelegramHandler() {
    const navigate = useNavigate();
    const location = useLocation();
    const [isAuthenticating, setIsAuthenticating] = useState(false);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        if (!tg || !tg.initData) return;

        tg.ready();
        tg.expand();

        // 500ms kutamiz (ba'zi platformalarda SDK kechroq yuklanadi)
        const timer = setTimeout(() => {
            const rawData = tg.initData;

            if (rawData) {
                // Agar allaqachon dashboard yoki ichkarida bo'lsak, qayta login qilmaymiz (ixtiyoriy)
                // Lekin session yangilash uchun foydali bo'lishi mumkin.
                // Eng muhimi - faqat Home yoki Login dan Dashboard ga o'tkazish.

                setIsAuthenticating(true);
                axios.post(`${API_BASE}/auth/telegram-webapp`, { initData: rawData })
                    .then(res => {
                        const { session_token, u_id } = res.data.data || {};
                        if (session_token) {
                            localStorage.setItem("session_token", session_token);
                            localStorage.setItem("u_id", u_id);

                            // Faqat Home (/) yoki Login (/login) sahifasida bo'lsak Dashboardga o'tkazamiz
                            const currentPath = window.location.pathname;
                            if (currentPath === "/" || currentPath === "/login") {
                                navigate("/dashboard", { replace: true });
                            }
                        }
                    })
                    .catch(err => {
                        console.error("Auto-login error:", err);
                    })
                    .finally(() => {
                        setIsAuthenticating(false);
                    });
            }
        }, 500);

        return () => clearTimeout(timer);
    }, [navigate]); // Faqat bir marta (mount bo'lganda) ishlaydi

    if (isAuthenticating) {
        return (
            <div className="tma-splash-screen" style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: '#1c1c1c',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                color: 'white'
            }}>
                <div className="spinner" style={{
                    width: '40px',
                    height: '40px',
                    border: '4px solid rgba(255,255,255,0.1)',
                    borderTop: '4px solid #007aff',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }}></div>
                <p style={{ marginTop: '15px', fontSize: '14px', opacity: 0.8 }}>Ko'chatim yuklanmoqda...</p>
                <style>{`
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        );
    }

    return null;
}
