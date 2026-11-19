import Logo from "../components/Logo";
import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
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
  const [identifier, setIdentifier] = useState("");
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
      await login(identifier, password);
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
        <div className="login-brand"><Logo /></div>
        <h1 id="login-title">Sign in</h1>
        <p>Use your DukaanPulse account to continue.</p>

        <form onSubmit={handleSubmit}>
          <ErrorBanner message={error} />

          <div className="field">
            <label htmlFor="identifier">Username or mobile number</label>
            <input
              id="identifier"
              name="identifier"
              type="text"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
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
          <div className="auth-links">
            <Link to="/forgot-password">Forgot password?</Link>
            <Link to="/signup">Create a business account</Link>
          </div>
        </form>
      </section>
    </main>
  );
}
