import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../api/https";
import { generateDeviceKey } from "../../api/deviceKey";

/**
 * Bu komponent Telegram Mini App ichida ochilganini aniqlaydi
 * va avtomatik loginni amalga oshiradi.
 */
export default function TelegramHandler() {
    const navigate = useNavigate();
    const hasAttempted = useRef(false);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        const sessionToken = localStorage.getItem("session_token");
        const currentPath = window.location.pathname;

        if (sessionToken && currentPath === "/") return;
        if (!tg || !tg.initData || hasAttempted.current) return;

        hasAttempted.current = true;
        tg.ready();
        tg.expand();

        const timer = setTimeout(async () => {
            try {
                // Bind the new session to a key that never leaves this browser.
                const deviceKey = await generateDeviceKey();
                const data = await apiFetch("/auth/telegram-webapp", {
                    method: "POST",
                    body: { initData: tg.initData, device_key: deviceKey.publicJwk },
                });
                const { session_token, u_id } = data || {};
                if (session_token) {
                    await deviceKey.save();
                    localStorage.setItem("session_token", session_token);
                    localStorage.setItem("u_id", String(u_id));

                    if (window.location.pathname === "/login") {
                        navigate("/dashboard", { replace: true });
                    } else if (window.location.pathname === "/") {
                        window.location.reload();
                    }
                }
            } catch (err) {
                console.error("Auto-login error:", err);
            }
        }, 200);

        return () => clearTimeout(timer);
    }, [navigate]);

    return null;
}
