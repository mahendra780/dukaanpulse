export function Spinner({ label = "Loading…" }) {
  return <div className="spinner-wrap">{label}</div>;
}

export function EmptyState({ label = "Nothing here yet" }) {
  return <div className="empty-state">{label}</div>;
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return <div className="form-error">{message}</div>;
}
