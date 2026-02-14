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
        // Allaqachon urinib ko'rgan bo'lsak yoki Telegram bo'lmasa to'xtatamiz
        if (!tg || !tg.initData || hasAttempted.current) return;

        hasAttempted.current = true;

        tg.ready();
        tg.expand();

        const sessionToken = localStorage.getItem("session_token");
        const currentPath = window.location.pathname;

        // Splash screen faqat Login sahifasida bo'lsak chiqishi mumkin
        // Home (/) da silent login bo'lgani ma'qul, lekin user xohlagancha loading ko'rsatishimiz mumkin
        const showSplash = (currentPath === "/login") && !sessionToken;

        if (showSplash) {
            setIsAuthenticating(true);
        }

        // 200ms kutamiz
        const timer = setTimeout(() => {
            axios.post(`${API_BASE}/auth/telegram-webapp`, { initData: tg.initData })
                .then(res => {
                    const { session_token, u_id } = res.data.data || {};
                    if (session_token) {
                        localStorage.setItem("session_token", session_token);
                        localStorage.setItem("u_id", u_id);

                        // Avtomatik Dashboard ga o'tkazmaymiz (User xohishiga ko'ra)
                        // Faqat Login sahifasida bo'lsak, Dashboard ga o'tkazish mantiqiyroq
                        if (window.location.pathname === "/login") {
                            navigate("/dashboard", { replace: true });
                        } else if (window.location.pathname === "/") {
                            // Home sahifasida bo'lsak, tugmalar yangilanishi uchun reload qilamiz 
                            // yoki shunchaki navigate(0) qilamiz. 
                            // Eng yaxshisi - react state orqali yangilash, lekin hozirgi strukturada 
                            // navigate(0) eng xavfsiz silent yo'l.
                            window.location.reload();
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
    }, [navigate]); // location.pathname dependency olib tashlandi

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
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                color: 'white'
            }}>
                <div className="spinner" style={{
                    width: '30px',
                    height: '30px',
                    border: '3px solid rgba(255,255,255,0.1)',
                    borderTop: '3px solid #007aff',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }}></div>
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
