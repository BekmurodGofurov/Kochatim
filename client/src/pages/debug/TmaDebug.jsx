import React, { useEffect, useState } from "react";
import "./TmaDebug.scss";

export default function TmaDebug() {
    const [tgData, setTgData] = useState(null);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        if (tg) {
            setTgData({
                initData: tg.initData,
                initDataUnsafe: tg.initDataUnsafe,
                version: tg.version,
                platform: tg.platform,
                colorScheme: tg.colorScheme,
                viewportHeight: tg.viewportHeight,
                isExpanded: tg.isExpanded,
            });
        }
    }, []);

    if (!tgData) {
        return (
            <div className="tma-debug">
                <h1>Telegram SDK topilmadi</h1>
                <p>Iltimos, ushbu sahifani Telegram Mini App ichida oching.</p>
                <button onClick={() => window.location.reload()}>Yangilash</button>
            </div>
        );
    }

    return (
        <div className="tma-debug">
            <h1>TMA Debug Interface</h1>

            <section>
                <h2>User Information (Unsafe)</h2>
                <pre>{JSON.stringify(tgData.initDataUnsafe?.user, null, 2)}</pre>
            </section>

            <section>
                <h2>Raw initData</h2>
                <div className="raw-data">{tgData.initData}</div>
            </section>

            <section>
                <h2>Environment Details</h2>
                <ul>
                    <li><strong>Version:</strong> {tgData.version}</li>
                    <li><strong>Platform:</strong> {tgData.platform}</li>
                    <li><strong>ColorScheme:</strong> {tgData.colorScheme}</li>
                    <li><strong>Viewport Height:</strong> {tgData.viewportHeight}</li>
                </ul>
            </section>

            <button className="copy-btn" onClick={() => navigator.clipboard.writeText(tgData.initData)}>
                initData nusxalash
            </button>

            <button className="back-btn" onClick={() => window.history.back()}>
                Orqaga
            </button>
        </div>
    );
}
