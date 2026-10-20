import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Spinner } from "./Feedback";
import { useAuth } from "../auth/AuthProvider";

export default function ProtectedRoute() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="auth-loading">
        <Spinner label="Checking your session…" />
      </div>
    );
  }

  if (!user) {
    const from = location.pathname + location.search + location.hash;
    return <Navigate to="/login" replace state={{ from }} />;
  }

  return <Outlet />;
}
