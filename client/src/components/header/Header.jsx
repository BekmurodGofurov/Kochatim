import { Link, useLocation } from "react-router-dom";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import "./Header.scss";

export default function Header() {
    const { theme, toggleTheme } = useTheme();
    const location = useLocation();
    const isLoggedIn = !!localStorage.getItem("session_token");
    const isLoginPage = location.pathname === "/login";

    return (
        <header className="app-header">
            <div className="container">
                <Link to="/" className="logo">
                    <img src="/img1.png" alt="Ko'chatim" />
                    <span>Ko'chatim</span>
                </Link>

                <div className="header-actions">
                    <button
                        onClick={toggleTheme}
                        className="theme-toggle"
                        title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
                    >
                        {theme === "light" ? <Moon size={20} /> : <Sun size={20} />}
                    </button>

                    {!isLoginPage && (
                        isLoggedIn ? (
                            <Link to="/dashboard" className="login-btn">
                                Dashboard
                            </Link>
                        ) : (
                            <Link to="/login" className="login-btn">
                                Login
                            </Link>
                        )
                    )}
                </div>
            </div>
        </header>
    );
}
