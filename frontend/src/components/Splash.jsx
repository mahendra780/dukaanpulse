import { useEffect, useState } from "react";
import "./Splash.css";

// Full-screen logo intro. The CSS timeline is 4.4s long: the mark draws in,
// the name expands out of it, holds, folds back in, then the screen fades to
// reveal the app underneath (which has been loading the whole time).
export default function Splash({ onFinish }) {
  const [ready, setReady] = useState(false);
  const [skipping, setSkipping] = useState(false);

  useEffect(() => {
    let cancelled = false;

    // Start the timeline once the serif font is available (or after 700ms,
    // so a slow or offline font never delays the intro).
    const fontReady = document.fonts?.load
      ? document.fonts.load('700 1em "Libre Baskerville"').catch(() => {})
      : Promise.resolve();
    const timeout = new Promise((resolve) => setTimeout(resolve, 700));
    Promise.race([fontReady, timeout]).then(() => {
      if (!cancelled) setReady(true);
    });

    // Safety net: never leave the overlay up if an animation event is missed.
    const failsafe = setTimeout(onFinish, 7000);

    document.body.style.overflow = "hidden";
    return () => {
      cancelled = true;
      clearTimeout(failsafe);
      document.body.style.overflow = "";
    };
  }, [onFinish]);

  const handleAnimationEnd = (event) => {
    if (event.target === event.currentTarget && event.animationName === "sp-out") {
      onFinish();
    }
  };

  const className = ["splash", ready && "splash-run", skipping && "splash-skip"]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={className}
      role="status"
      aria-label="DukaanPulse"
      onAnimationEnd={handleAnimationEnd}
    >
      <div className="sp-stage">
        <svg className="sp-mark" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
          <rect className="sp-badge" width="64" height="64" rx="12" fill="#6d1f2c" />
          <path
            className="sp-awning"
            d="M13 10H51V16A6.33 6.33 0 0 1 38.33 16A6.33 6.33 0 0 1 25.67 16A6.33 6.33 0 0 1 13 16Z"
            fill="#c9a24a"
          />
          <path
            className="sp-arch"
            d="M20 55V38A12 12 0 0 1 44 38V55"
            fill="none"
            stroke="#ffffff"
            strokeWidth="2.5"
            strokeLinecap="round"
            pathLength="1"
          />
          <path
            className="sp-d"
            fill="#ffffff"
            fillRule="evenodd"
            d="M24.5 36H31.5C37.3 36 40 39.3 40 43C40 46.7 37.3 50 31.5 50H24.5V48.9L26.2 48.5V37.5L24.5 37.1ZM29 37.8H31.4C34.2 37.8 35.4 40 35.4 43C35.4 46 34.2 48.2 31.4 48.2H29Z"
          />
        </svg>

        <div className="sp-reveal">
          <div className="sp-clip">
            <div className="sp-word">
              <div className="sp-name">
                <strong>Dukaan</strong>
                <span>Pulse</span>
              </div>
              <div className="sp-tag">Wholesale ERP</div>
            </div>
          </div>
        </div>
      </div>

      <button className="sp-skip" type="button" onClick={() => setSkipping(true)}>
        Skip
      </button>
    </div>
  );
}