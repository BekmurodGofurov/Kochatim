import { useEffect, useState, useRef } from "react";
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
    const hasAttempted = useRef(false);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        // initData bo'lmasa yoki allaqachon urinib ko'rgan bo'lsak chiqib ketamiz
        if (!tg || !tg.initData || hasAttempted.current) return;

        hasAttempted.current = true;

        tg.ready();
        tg.expand();

        const sessionToken = localStorage.getItem("session_token");
        const currentPath = window.location.pathname;

        // Agar foydalanuvchi allaqachon ichkarida bo'lsa va / yoki /login da bo'lmasa, 
        // splash korsatmaymiz, shunchaki loginni fonda yangilaymiz (ixtiyoriy)
        const showSplash = (currentPath === "/" || currentPath === "/login") && !sessionToken;

        if (showSplash) {
            setIsAuthenticating(true);
        }

        // 200ms kutamiz (tezroq ishlashi uchun)
        const timer = setTimeout(() => {
            axios.post(`${API_BASE}/auth/telegram-webapp`, { initData: tg.initData })
                .then(res => {
                    const { session_token, u_id } = res.data.data || {};
                    if (session_token) {
                        localStorage.setItem("session_token", session_token);
                        localStorage.setItem("u_id", u_id);

                        // Faqatgina Home yoki Login da bo'lsa Dashboard ga o'tkazamiz
                        if (window.location.pathname === "/" || window.location.pathname === "/login") {
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
        }, 200);

        return () => clearTimeout(timer);
    }, [navigate]);

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
                {/* Chiroyli Logo yoki Spinner */}
                <img src="/img1.png" alt="Logo" style={{ width: '80px', marginBottom: '20px' }} />
                <div className="spinner" style={{
                    width: '30px',
                    height: '30px',
                    border: '3px solid rgba(255,255,255,0.1)',
                    borderTop: '3px solid #007aff',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }}></div>
                <p style={{ marginTop: '15px', fontSize: '14px', opacity: 0.6 }}>Ko'chatim...</p>
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
