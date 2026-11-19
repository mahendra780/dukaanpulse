const TONE_MAP = {
  ACTIVE: "green",
  RECEIVED: "green",
  PAID: "green",
  DELIVERED: "green",
  COMPLETED: "green",
  CONFIRMED: "accent",
  DISPATCHED: "accent",
  APPROVED: "accent",
  PENDING: "amber",
  PARTIALLY_PAID: "amber",
  PARTIALLY_RECEIVED: "amber",
  PARTIALLY_FULFILLED: "amber",
  REQUESTED: "amber",
  UNPAID: "red",
  CANCELLED: "red",
  REJECTED: "red",
  INACTIVE: "gray",
};

export default function StatusBadge({ status }) {
  const tone = TONE_MAP[status] || "gray";
  return <span className={`badge badge-${tone}`}>{status?.replaceAll("_", " ")}</span>;
}