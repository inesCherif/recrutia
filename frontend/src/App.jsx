import { useState, useEffect, useCallback } from "react";
import LoginPage from "./pages/LoginPage";
import HomePage from "./pages/HomePage";
import RecruiterDashboard from "./pages/RecruiterDashboard";
import StudentDashboard from "./pages/StudentDashboard";
import { isAuthenticated, clearToken, authAPI } from "./api";

const SPACE_LABELS = {
  student: { icon: "🎓", label: "Espace Candidat" },
  recruiter: { icon: "🚀", label: "Espace Recruteur" },
};

// --- Toast Container Component ---
function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    function handleToast(e) {
      const toast = e.detail;
      setToasts((prev) => [...prev.slice(-4), toast]); // keep max 5

      // Auto-dismiss
      setTimeout(() => removeToast(toast.id), toast.duration || 5000);
    }

    window.addEventListener("recrutia:toast", handleToast);
    return () => window.removeEventListener("recrutia:toast", handleToast);
  }, [removeToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="alert" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type || "error"}`}>
          <span className="toast-icon">
            {t.type === "success" ? "✅" : t.type === "warning" ? "⚠️" : "❌"}
          </span>
          <span className="toast-message">{t.message}</span>
          <button
            className="toast-close"
            onClick={() => removeToast(t.id)}
            aria-label="Fermer"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

// --- Main App ---
export default function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("home");
  const [checking, setChecking] = useState(() => isAuthenticated());

  useEffect(() => {
    if (!checking) return;

    let cancelled = false;

    authAPI
      .me()
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        setChecking(false);
      })
      .catch(() => {
        if (cancelled) return;
        clearToken();
        setChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, [checking]);

  function handleLogin(userData) {
    setUser(userData);
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setPage("home");
  }

  if (checking) {
    return (
      <div className="login-page">
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Chargement...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <ToastContainer />
        <LoginPage onLogin={handleLogin} />
      </>
    );
  }

  const isInSpace = page !== "home";
  const spaceInfo = SPACE_LABELS[page];

  return (
    <div className="app-layout">
      {/* Global Toast Notifications */}
      <ToastContainer />

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo" onClick={() => setPage("home")} style={{ cursor: "pointer" }}>
          <span>🤖 Recrutia</span>
        </div>

        <nav className="sidebar-nav">
          {isInSpace ? (
            <>
              {/* Back to Home */}
              <button
                className="sidebar-link back-link"
                onClick={() => setPage("home")}
              >
                ← Accueil
              </button>

              {/* Current space indicator */}
              <div className="sidebar-space-indicator">
                <span className="space-icon">{spaceInfo?.icon}</span>
                <span className="space-label">{spaceInfo?.label}</span>
              </div>
            </>
          ) : (
            /* Home — no extra links, the home cards handle navigation */
            <button
              className="sidebar-link active"
              onClick={() => setPage("home")}
            >
              🏠 Accueil
            </button>
          )}
        </nav>

        <div style={{ borderTop: "1px solid var(--border-glass)", paddingTop: 16, marginTop: "auto" }}>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 8 }}>
            👤 {user.username}
          </div>
          <button className="btn btn-secondary btn-sm btn-full" onClick={handleLogout}>
            Se déconnecter
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {page === "home" && (
          <HomePage user={user} onNavigate={setPage} />
        )}
        {page === "recruiter" && <RecruiterDashboard />}
        {page === "student" && <StudentDashboard />}
      </main>
    </div>
  );
}
