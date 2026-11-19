// Placeholder shapes shown while data loads, so the page keeps its layout
// instead of collapsing to a single line of text.

export function SkeletonBlock({ width = "100%", height = 16, radius, className = "" }) {
  return (
    <span
      className={`skeleton ${className}`.trim()}
      style={{ width, height, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}

export function TableSkeleton({ rows = 6, cols = 5 }) {
  return (
    <div className="table-wrap skeleton-table" aria-hidden="true">
      <div className="skeleton-row skeleton-head" style={{ "--cols": cols }}>
        {Array.from({ length: cols }, (_, c) => (
          <SkeletonBlock key={c} width="55%" height={12} />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div className="skeleton-row" style={{ "--cols": cols }} key={r}>
          {Array.from({ length: cols }, (_, c) => (
            <SkeletonBlock key={c} width={c === 0 ? "70%" : "50%"} height={14} />
          ))}
        </div>
      ))}
    </div>
  );
}

function HeaderSkeleton() {
  return (
    <div className="page-header" aria-hidden="true">
      <div>
        <SkeletonBlock width={200} height={32} />
        <div style={{ marginTop: 8 }}>
          <SkeletonBlock width={280} height={16} />
        </div>
      </div>
    </div>
  );
}

// A whole page: heading, search bar and a table.
export function PageSkeleton({ label = "Loading…" }) {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <HeaderSkeleton />
      <div className="skeleton-toolbar" aria-hidden="true">
        <SkeletonBlock width={280} height={40} radius="var(--radius)" />
      </div>
      <TableSkeleton />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">Loading dashboard…</span>
      <HeaderSkeleton />
      <div className="stat-grid" aria-hidden="true">
        {Array.from({ length: 6 }, (_, i) => (
          <div className="stat-card" key={i}>
            <SkeletonBlock width="50%" height={14} />
            <div style={{ marginTop: 8 }}>
              <SkeletonBlock width="70%" height={28} />
            </div>
          </div>
        ))}
      </div>
      <div className="panel" aria-hidden="true">
        <SkeletonBlock width={220} height={20} />
        <div style={{ marginTop: 16 }}>
          <SkeletonBlock height={260} radius="var(--radius)" />
        </div>
      </div>
      <div className="detail-grid" aria-hidden="true">
        {[0, 1].map((i) => (
          <div className="panel" key={i}>
            <SkeletonBlock width={160} height={20} />
            {Array.from({ length: 4 }, (_, r) => (
              <div style={{ marginTop: 16 }} key={r}>
                <SkeletonBlock height={14} />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}