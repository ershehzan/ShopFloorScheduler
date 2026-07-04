"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  UserProfile,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  getCurrentUserProfile,
  getAccessToken,
} from "./api";

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const loadUser = useCallback(async () => {
    await Promise.resolve();
    if (getAccessToken()) {
      try {
        const profile = await getCurrentUserProfile();
        setUser(profile);
      } catch (err) {
        console.error("Failed to load user profile:", err);
        apiLogout();
        setUser(null);
      }
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadUser();
    }, 0);

    // Listen to token expiration events broadcasted by our fetch interceptor
    const handleAuthExpired = () => {
      setUser(null);
      router.push("/login");
    };

    window.addEventListener("sf_auth_expired", handleAuthExpired);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("sf_auth_expired", handleAuthExpired);
    };
  }, [loadUser, router]);

  // Protect dashboard routes
  useEffect(() => {
    if (!loading) {
      const isPublicRoute = pathname === "/login" || pathname === "/register";
      if (!user && !isPublicRoute) {
        router.push("/login");
      } else if (user && isPublicRoute) {
        router.push("/dashboard");
      }
    }
  }, [user, loading, pathname, router]);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      await apiLogin(email, password);
      const profile = await getCurrentUserProfile();
      setUser(profile);
      router.push("/dashboard");
    } catch (err) {
      setUser(null);
      setLoading(false);
      throw err;
    }
  };

  const register = async (email: string, username: string, password: string) => {
    setLoading(true);
    try {
      await apiRegister(email, username, password);
      // Auto login after registration
      await apiLogin(email, password);
      const profile = await getCurrentUserProfile();
      setUser(profile);
      router.push("/dashboard");
    } catch (err) {
      setLoading(false);
      throw err;
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await apiLogout();
    } finally {
      setUser(null);
      setLoading(false);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
