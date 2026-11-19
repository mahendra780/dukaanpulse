import { useCallback, useEffect, useRef, useState } from "react";
import Splash from "./Splash";

const SEEN_KEY = "dukaanpulse:splash-seen";

function alreadySeen() {
  try {
    return sessionStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

// Plays the logo intro once per browser session. The app renders underneath
// from the very first moment, so the session check and first data load happen
// while the logo animates, and the page is ready when the intro fades out.
export default function SplashGate({ children }) {
  const [playing, setPlaying] = useState(() => !alreadySeen());
  const appRef = useRef(null);

  // Keep keyboard focus out of the hidden app while the intro is on screen,
  // and let the page know so its own entrance animations wait for the end.
  useEffect(() => {
    if (appRef.current) appRef.current.inert = playing;
    document.documentElement.dataset.splash = playing ? "playing" : "done";
  }, [playing]);

  const finish = useCallback(() => {
    try {
      sessionStorage.setItem(SEEN_KEY, "1");
    } catch {
      /* private mode: the intro will just play again next visit */
    }
    setPlaying(false);
  }, []);

  return (
    <>
      <div ref={appRef} style={{ display: "contents" }}>
        {children}
      </div>
      {playing && <Splash onFinish={finish} />}
    </>
  );
}