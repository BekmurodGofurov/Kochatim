import React, { useEffect, useState } from "react";
import "./TmaDebug.scss";

export default function TmaDebug() {
    const [tgData, setTgData] = useState(null);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        const hasWindowTg = !!window.Telegram;

        if (tg) {
            setTgData({
                hasWindowTg,
                noWebApp: false,
                initData: tg.initData,
                initDataUnsafe: tg.initDataUnsafe,
                version: tg.version,
                platform: tg.platform,
                colorScheme: tg.colorScheme,
                viewportHeight: tg.viewportHeight,
                isExpanded: tg.isExpanded,
            });
        } else {
            setTgData({ hasWindowTg, noWebApp: true });
        }
    }, []);

    if (!tgData) {
        return <div className="tma-debug"><h1>Kutib turing...</h1></div>;
    }

    return (
        <div className="tma-debug">
            <h1>TMA Debug Interface</h1>

            <section style={{ border: "2px solid #2e7d32", backgroundColor: "#e8f5e9" }}>
                <h2>Detection Status</h2>
                <ul>
                    <li><strong>window.Telegram:</strong> {tgData.hasWindowTg ? "MAVJUD ✅" : "YUQ ❌"}</li>
                    <li><strong>WebApp Object:</strong> {tgData.noWebApp ? "YUQ ❌" : "MAVJUD ✅"}</li>
                    <li><strong>initData (Length):</strong> {tgData.initData?.length || 0}</li>
                    <li><strong>Platform:</strong> {tgData.platform || "noma'lum"}</li>
                </ul>
            </section>

            <section>
                <h2>User Information (Unsafe)</h2>
                <pre>{JSON.stringify(tgData.initDataUnsafe?.user, null, 2) || "User topilmadi"}</pre>
            </section>

            <section>
                <h2>Raw initData</h2>
                <div className="raw-data" style={{ fontSize: "10px", wordBreak: "break-all", background: "#eee", padding: "10px" }}>
                    {tgData.initData || "initData bo'sh (empty)"}
                </div>
            </section>

            <button className="copy-btn" onClick={() => {
                if (tgData.initData) {
                    navigator.clipboard.writeText(tgData.initData);
                    alert("initData nusxalandi!");
                } else {
                    alert("Nusxalash uchun ma'lumot yo'q");
                }
            }}>
                initData nusxalash
            </button>

            <button className="back-btn" onClick={() => window.location.reload()}>
                Sahifani yangilash
            </button>

            <button className="back-btn" style={{ marginTop: "10px", backgroundColor: "#fbe9e7" }} onClick={() => window.location.href = "/"}>
                Bosh sahifaga qaytish
            </button>
        </div>
    );
}
