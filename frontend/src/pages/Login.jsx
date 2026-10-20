import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ErrorBanner } from "../components/Feedback";
import {
  clearPostLoginPath,
  extractErrorMessage,
  getPostLoginPath,
} from "../api/client";
import { useAuth } from "../auth/AuthProvider";

function isSafePath(path) {
  return typeof path === "string" && path.startsWith("/") && !path.startsWith("//");
}

export default function Login() {
  const { user, isLoading, login } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(
    location.state?.sessionExpired
      ? "Your session has expired. Please sign in again."
      : ""
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isLoading) {
    return <div className="auth-loading">Checking your session…</div>;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login(username, password);
      const rememberedPath = location.state?.from || getPostLoginPath();
      clearPostLoginPath();
      navigate(isSafePath(rememberedPath) ? rememberedPath : "/", { replace: true });
    } catch (requestError) {
      setError(extractErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand">Dukaan<span>Pulse</span></div>
        <h1 id="login-title">Sign in</h1>
        <p>Use your DukaanPulse account to continue.</p>

        <form onSubmit={handleSubmit}>
          <ErrorBanner message={error} />

          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              name="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
              autoFocus
              disabled={isSubmitting}
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
              disabled={isSubmitting}
            />
          </div>

          <button className="btn btn-primary login-submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
