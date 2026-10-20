import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  clearPostLoginPath,
  clearStoredSession,
  getPostLoginPath,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from "../api/client";
import { getCurrentUser, login as loginRequest } from "../api/endpoints";

const AuthContext = createContext(null);

function currentPath(location) {
  return location.pathname + location.search + location.hash;
}

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState(getStoredToken);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    clearStoredSession();
    setToken(null);
    setUser(null);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    clearPostLoginPath();
    navigate("/login", { replace: true });
  }, [clearSession, navigate]);

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

    if (!token) {
      setIsLoading(false);
      return () => {
        isCurrent = false;
      };
    }

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
  }, []);

  const login = useCallback(async (username, password) => {
    const response = await loginRequest(username, password);
    storeToken(response.access_token);
    setToken(response.access_token);

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      clearSession();
      throw error;
    }
  }, [clearSession]);

  const can = useCallback(
    (permission) => user?.permissions?.includes(permission) ?? false,
    [user],
  );

  return (
    <AuthContext.Provider value={{ token, user, isLoading, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
