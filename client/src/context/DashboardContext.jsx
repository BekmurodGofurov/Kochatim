import { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { apiFetch, getSessionToken } from "../api/https";

const DashboardContext = createContext(null);

export function DashboardProvider({ children }) {
    const location = useLocation();
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(false); // Initially not loading until we have a token
    const [error, setError] = useState(null);
    const [lastFetched, setLastFetched] = useState(0);

    // Sales caching
    const [salesData, setSalesData] = useState(null);
    const [salesLoading, setSalesLoading] = useState(false);
    const [salesError, setSalesError] = useState(null);
    const [salesLastFetched, setSalesLastFetched] = useState(0);

    // Ma'lumotni yuklash funksiyasi
    const fetchDashboard = useCallback(async (force = false) => {
        // 0) Token borligini tekshirish
        if (!getSessionToken()) {
            setLoading(false);
            return;
        }

        // Agar majburiy bo'lmasa va ma'lumot 5 minut ichida olingan bo'lsa, qayta yuklamaymiz
        const now = Date.now();
        if (!force && dashboardData && now - lastFetched < 5 * 60 * 1000) {
            return; // Cache valid
        }

        setLoading(true);
        try {
            const data = await apiFetch("/api/me/dashboard");
            setDashboardData(data);
            setLastFetched(now);
            setError(null);
        } catch (err) {
            console.error("Dashboard fetch error:", err);
            setError(err.message || "Ma'lumotlarni yuklashda xatolik");
        } finally {
            setLoading(false);
        }
    }, [dashboardData, lastFetched]);

    const fetchSales = useCallback(async (force = false) => {
        if (!getSessionToken()) return;

        const now = Date.now();
        if (!force && salesData && now - salesLastFetched < 5 * 60 * 1000) {
            return; // Cache valid
        }

        setSalesLoading(true);
        try {
            const data = await apiFetch("/api/sales");
            setSalesData(data);
            setSalesLastFetched(now);
            setSalesError(null);
        } catch (err) {
            console.error("Sales fetch error:", err);
            setSalesError(err.message || "Sotuvlar tarixini yuklashda xatolik");
        } finally {
            setSalesLoading(false);
        }
    }, [salesData, salesLastFetched]);

    // Token bor bo'lsa va data yo'q bo'lsa har gal path o'zgarganda yuklashga harakat qilamiz
    useEffect(() => {
        const token = getSessionToken();
        if (token && !dashboardData && !loading) {
            fetchDashboard();
        }
    }, [location.pathname, dashboardData, loading, fetchDashboard]);

    // Dastur ishga tushganda bir marta DASHBOARD yuklaymiz
    useEffect(() => {
        if (!dashboardData) {
            fetchDashboard();
        }
    }, [fetchDashboard, dashboardData]);

    const value = useMemo(() => ({
        dashboardData,
        loading,
        error,
        refreshDashboard: () => fetchDashboard(true),

        salesData,
        salesLoading,
        salesError,
        fetchSales, // component ichida chaqiriladi
        refreshSales: () => fetchSales(true),
    }), [
        dashboardData, loading, error, fetchDashboard,
        salesData, salesLoading, salesError, fetchSales
    ]);

    return (
        <DashboardContext.Provider value={value}>
            {children}
        </DashboardContext.Provider>
    );
}

// Hook
export function useDashboard() {
    const context = useContext(DashboardContext);
    if (!context) {
        throw new Error("useDashboard must be used within a DashboardProvider");
    }
    return context;
}
