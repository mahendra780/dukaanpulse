import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  clearPostLoginPath,
  clearStoredSession,
  getPostLoginPath,
  setUnauthorizedHandler,
} from "../api/client";
import { getCurrentUser, login as loginRequest, logout as logoutRequest, switchWorkspace as switchWorkspaceRequest } from "../api/endpoints";
import { useToast } from "../components/ToastProvider";

const AuthContext = createContext(null);

function currentPath(location) {
  return location.pathname + location.search + location.hash;
}

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    clearStoredSession();
    setUser(null);
  }, []);

  // Leave straight away and tell the server in the background. Waiting for
  // the server's reply first meant the click seemed to do nothing for as long
  // as that request took.
  const logout = useCallback(() => {
    logoutRequest().catch(() => {
      // A stale or expired cookie should still leave the UI signed out.
    });
    clearSession();
    clearPostLoginPath();
    navigate("/login", { replace: true });
    toast.success("You have been logged out.");
  }, [clearSession, navigate, toast]);

  const handleUnauthorized = useCallback(() => {
    clearSession();

    if (location.pathname !== "/login") {
      navigate("/login", {
        replace: true,
        state: {
          from: getPostLoginPath() || currentPath(location),
          sessionExpired: true,
        },
      });
    }
  }, [clearSession, location, navigate]);

  useEffect(() => setUnauthorizedHandler(handleUnauthorized), [handleUnauthorized]);

  useEffect(() => {
    let isCurrent = true;

    getCurrentUser()
      .then((currentUser) => {
        if (isCurrent) setUser(currentUser);
      })
      .catch(() => {
        if (isCurrent) clearSession();
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [clearSession]);

  const refresh = useCallback(async () => {
    const currentUser = await getCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  const login = useCallback(async (identifier, password) => {
    const currentUser = await loginRequest(identifier, password);
    setUser(currentUser);
    return currentUser;
  }, [clearSession]);

  const switchWorkspace = useCallback(async (workspaceId) => {
    const currentUser = await switchWorkspaceRequest({ workspace_id: workspaceId });
    setUser(currentUser);
    return currentUser;
  }, []);

  const can = useCallback(
    (permission) => user?.permissions?.includes(permission) ?? false,
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refresh, switchWorkspace, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}