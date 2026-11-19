export default function Logo({ onDark = false, showWord = true }) {
  return (
    <span className={onDark ? "logo logo-on-dark" : "logo"}>
      <svg className="logo-mark" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
        <rect width="64" height="64" rx="12" fill="#6d1f2c" />
        <path
          d="M13 10H51V16A6.33 6.33 0 0 1 38.33 16A6.33 6.33 0 0 1 25.67 16A6.33 6.33 0 0 1 13 16Z"
          fill="#c9a24a"
        />
        <path
          d="M20 55V38A12 12 0 0 1 44 38V55"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path
          fill="#ffffff"
          fillRule="evenodd"
          d="M24.5 36H31.5C37.3 36 40 39.3 40 43C40 46.7 37.3 50 31.5 50H24.5V48.9L26.2 48.5V37.5L24.5 37.1ZM29 37.8H31.4C34.2 37.8 35.4 40 35.4 43C35.4 46 34.2 48.2 31.4 48.2H29Z"
        />
      </svg>
      {showWord && (
        <span className="logo-word">
          <strong>Dukaan</strong>
          <span>Pulse</span>
        </span>
      )}
    </span>
  );
}