import { createContext, useCallback, useContext, useRef, useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from "lucide-react";

const ToastContext = createContext(null);

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

// Error/warning stay up longer than success/info -- the person is more
// likely to need time to read and act on them.
const DURATIONS = {
  success: 4000,
  info: 4000,
  warning: 6000,
  error: 7000,
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  // What the screen-reader live regions currently announce. These two
  // regions stay mounted in the page permanently -- screen readers
  // announce changes to an EXISTING live region far more reliably than
  // a live region that is created at the same moment as its content.
  const [announcement, setAnnouncement] = useState({ polite: null, assertive: null });
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback((type, message) => {
    const id = nextId.current++;
    const urgent = type === "error" || type === "warning";
    setToasts((t) => [...t, { id, type, message }]);
    setAnnouncement((a) => ({ ...a, [urgent ? "assertive" : "polite"]: { id, message } }));
    window.setTimeout(() => dismiss(id), DURATIONS[type] ?? 5000);
  }, [dismiss]);

  const toast = useRef({
    success: (message) => show("success", message),
    error: (message) => show("error", message),
    warning: (message) => show("warning", message),
    info: (message) => show("info", message),
  }).current;

  return (
    <ToastContext.Provider value={toast}>
      {children}

      {/* Screen-reader announcements (visually hidden). The key makes the
          same message announce again if it happens twice in a row. */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {announcement.polite && <span key={announcement.polite.id}>{announcement.polite.message}</span>}
      </div>
      <div className="sr-only" role="alert" aria-live="assertive" aria-atomic="true">
        {announcement.assertive && <span key={announcement.assertive.id}>{announcement.assertive.message}</span>}
      </div>

      <div className="toast-stack">
        {toasts.map((t) => {
          const Icon = ICONS[t.type] || Info;
          return (
            <div key={t.id} className={`toast toast-${t.type}`}>
              <Icon size={18} className="toast-icon" aria-hidden="true" />
              <span className="toast-message">{t.message}</span>
              <button className="toast-dismiss" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">
                <X size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

// Returns { success(msg), error(msg), warning(msg), info(msg) }.
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}