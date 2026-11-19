import { XCircle } from "lucide-react";
import { PageSkeleton, TableSkeleton } from "./Skeleton";

// variant="table" (default): a table-shaped placeholder, for the list area
//   of a page whose heading and toolbar are already on screen.
// variant="page": a full-page placeholder (heading + toolbar + table).
// variant="text": a plain centred line, for the session check before the
//   app shell exists.
export function Spinner({ label = "Loading…", variant = "table" }) {
  if (variant === "page") return <PageSkeleton label={label} />;
  if (variant === "text") {
    return (
      <div className="spinner-wrap" role="status" aria-live="polite">
        {label}
      </div>
    );
  }
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <TableSkeleton />
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