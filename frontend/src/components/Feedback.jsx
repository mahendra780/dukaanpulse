import { XCircle } from "lucide-react";

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="spinner-wrap" role="status" aria-live="polite">
      {label}
    </div>
  );
}

export function EmptyState({ label = "Nothing here yet" }) {
  return <div className="empty-state">{label}</div>;
}

// role="alert" makes screen readers announce it the moment it appears;
// the icon means the error isn't signalled by red colour alone.
export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="form-error" role="alert">
      <XCircle size={16} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}