import { useEffect, useRef, useState } from "react";

// Splits "₹12,48,500" into a prefix ("₹"), the number, and a suffix ("") so
// the number can count up while the rest stays put. Anything that is not
// "text, number, text" (for example a date) is shown as-is without animation.
const NUMBER = /^([^\d-]*)(-?[\d,]+(?:\.\d+)?)([\s\S]*)$/;
const DURATION_MS = 700;

function parseValue(value) {
  const text = typeof value === "number" ? String(value) : value;
  if (typeof text !== "string") return null;
  const match = NUMBER.exec(text.trim());
  if (!match || /\d/.test(match[3])) return null;
  const number = Number(match[2].replace(/,/g, ""));
  if (!Number.isFinite(number)) return null;
  return {
    prefix: match[1],
    suffix: match[3],
    number,
    decimals: (match[2].split(".")[1] || "").length,
  };
}

const prefersReducedMotion = () =>
  typeof window !== "undefined"
  && Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

export default function StatCard({ label, value }) {
  const parsed = parseValue(value);
  const target = parsed ? parsed.number : 0;
  const animate = parsed !== null && target !== 0 && !prefersReducedMotion();

  const [shown, setShown] = useState(animate ? 0 : target);
  const current = useRef(animate ? 0 : target);

  useEffect(() => {
    if (!animate) {
      current.current = target;
      setShown(target);
      return undefined;
    }
    const from = current.current;
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / DURATION_MS);
      const eased = 1 - (1 - progress) ** 3;
      const next = progress === 1 ? target : from + (target - from) * eased;
      current.current = next;
      setShown(next);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, animate]);

  if (!parsed || !animate) {
    return (
      <div className="stat-card">
        <div className="label">{label}</div>
        <div className="value">{value}</div>
      </div>
    );
  }

  // Once the count finishes, show the original text exactly as given.
  const display = shown === target
    ? value
    : `${parsed.prefix}${shown.toLocaleString("en-IN", {
        minimumFractionDigits: parsed.decimals,
        maximumFractionDigits: parsed.decimals,
      })}${parsed.suffix}`;

  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className="value">
        <span aria-hidden="true">{display}</span>
        <span className="sr-only">{value}</span>
      </div>
    </div>
  );
}