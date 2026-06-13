import { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { apiFetch, getSessionToken } from "../api/https";

const DashboardContext = createContext(null);

const DASHBOARD_TTL         = 5  * 60 * 1000; // 5 daqiqa
const SALES_TTL             = 5  * 60 * 1000; // 5 daqiqa
const SETTINGS_TTL          = 2  * 60 * 1000; // 2 daqiqa (sessions o'zgaruvchan)
const PARTNER_DASHBOARDS_TTL = 5 * 60 * 1000; // 5 daqiqa

export function DashboardProvider({ children }) {
    const location = useLocation();

    // --- Dashboard ---
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastFetched, setLastFetched] = useState(0);

    // --- Sales ---
    const [salesData, setSalesData] = useState(null);
    const [salesLoading, setSalesLoading] = useState(false);
    const [salesError, setSalesError] = useState(null);
    const [salesLastFetched, setSalesLastFetched] = useState(0);

    // --- Settings (partners + sessions + invite_token — bitta endpoint) ---
    const [settingsData, setSettingsData] = useState(null);
    const [settingsLoading, setSettingsLoading] = useState(false);
    const [settingsLastFetched, setSettingsLastFetched] = useState(0);

    // --- Partner dashboards (Inventory N+1 fix) ---
    const [partnerDashboardsData, setPartnerDashboardsData] = useState(null);
    const [partnerDashboardsLoading, setPartnerDashboardsLoading] = useState(false);
    const [partnerDashboardsLastFetched, setPartnerDashboardsLastFetched] = useState(0);

    const fetchDashboard = useCallback(async (force = false) => {
        if (!getSessionToken()) { setLoading(false); return; }
        const now = Date.now();
        if (!force && dashboardData && now - lastFetched < DASHBOARD_TTL) return;
        setLoading(true);
        try {
            const data = await apiFetch("/api/me/dashboard");
            setDashboardData(data);
            setLastFetched(now);
            setError(null);
        } catch (err) {
            setError(err.message || "Ma'lumotlarni yuklashda xatolik");
        } finally {
            setLoading(false);
        }
    }, [dashboardData, lastFetched]);

    const fetchSales = useCallback(async (force = false) => {
        if (!getSessionToken()) return;
        const now = Date.now();
        if (!force && salesData && now - salesLastFetched < SALES_TTL) return;
        setSalesLoading(true);
        try {
            const data = await apiFetch("/api/sales");
            setSalesData(data);
            setSalesLastFetched(now);
            setSalesError(null);
        } catch (err) {
            setSalesError(err.message || "Sotuvlar tarixini yuklashda xatolik");
        } finally {
            setSalesLoading(false);
        }
    }, [salesData, salesLastFetched]);

    const fetchSettings = useCallback(async (force = false) => {
        if (!getSessionToken()) return;
        const now = Date.now();
        if (!force && settingsData && now - settingsLastFetched < SETTINGS_TTL) return;
        setSettingsLoading(true);
        try {
            const data = await apiFetch("/api/me/settings");
            setSettingsData(data);
            setSettingsLastFetched(now);
        } catch {
            // mavjud ma'lumot saqlanadi
        } finally {
            setSettingsLoading(false);
        }
    }, [settingsData, settingsLastFetched]);

    const fetchPartnerDashboards = useCallback(async (force = false) => {
        if (!getSessionToken()) return;
        const now = Date.now();
        if (!force && partnerDashboardsData && now - partnerDashboardsLastFetched < PARTNER_DASHBOARDS_TTL) return;
        setPartnerDashboardsLoading(true);
        try {
            const data = await apiFetch("/api/partners/dashboards");
            setPartnerDashboardsData(Array.isArray(data) ? data : []);
            setPartnerDashboardsLastFetched(now);
        } catch {
            setPartnerDashboardsData([]);
        } finally {
            setPartnerDashboardsLoading(false);
        }
    }, [partnerDashboardsData, partnerDashboardsLastFetched]);

    // Hamkor o'chirilganda yoki qo'shilganda ikkala keshni tozalash
    const invalidatePartners = useCallback(() => {
        setSettingsData(null);
        setSettingsLastFetched(0);
        setPartnerDashboardsData(null);
        setPartnerDashboardsLastFetched(0);
    }, []);

    // Sessiya o'chirilganda
    const invalidateSessions = useCallback(() => {
        setSettingsData(null);
        setSettingsLastFetched(0);
    }, []);

    // Token bor bo'lsa va dashboard yo'q bo'lsa — yuklash
    useEffect(() => {
        if (getSessionToken() && !dashboardData && !loading) fetchDashboard();
    }, [location.pathname, dashboardData, loading, fetchDashboard]);

    useEffect(() => {
        if (!dashboardData) fetchDashboard();
    }, [fetchDashboard, dashboardData]);

    const value = useMemo(() => ({
        dashboardData, loading, error,
        refreshDashboard: () => fetchDashboard(true),

        salesData, salesLoading, salesError,
        fetchSales,
        refreshSales: () => fetchSales(true),

        settingsData, settingsLoading,
        fetchSettings,
        invalidatePartners,
        invalidateSessions,

        partnerDashboardsData, partnerDashboardsLoading,
        fetchPartnerDashboards,
    }), [
        dashboardData, loading, error, fetchDashboard,
        salesData, salesLoading, salesError, fetchSales,
        settingsData, settingsLoading, fetchSettings, invalidatePartners, invalidateSessions,
        partnerDashboardsData, partnerDashboardsLoading, fetchPartnerDashboards,
    ]);

    return (
        <DashboardContext.Provider value={value}>
            {children}
        </DashboardContext.Provider>
    );
}

export function useDashboard() {
    const context = useContext(DashboardContext);
    if (!context) throw new Error("useDashboard must be used within a DashboardProvider");
    return context;
}
