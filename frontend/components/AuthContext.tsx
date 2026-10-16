"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { insforge } from "@/services/insforge";

export interface AuthUser {
  id: string;
  email?: string;
  name?: string;
  [key: string]: any;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signUp: (email: string, password: string, name?: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signIn: async () => ({ success: false }),
  signUp: async () => ({ success: false }),
  signOut: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function loadUser() {
      try {
        const { data, error } = await insforge.auth.getCurrentUser();
        if (mounted && data?.user) {
          setUser(data.user as AuthUser);
        }
      } catch (err) {
        console.error("Failed to fetch current user session:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadUser();
    return () => {
      mounted = false;
    };
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      const { data, error } = await insforge.auth.signInWithPassword({
        email,
        password,
      });
      if (error) {
        return { success: false, error: error.message || "Failed to sign in" };
      }
      if (data?.user) {
        setUser(data.user as AuthUser);
        return { success: true };
      }
      return { success: false, error: "No user returned" };
    } catch (err: any) {
      return { success: false, error: err?.message || "Unexpected authentication error" };
    }
  };

  const signUp = async (email: string, password: string, name?: string) => {
    try {
      const { data, error } = await insforge.auth.signUp({
        email,
        password,
        name: name || "SRE Operator",
      });
      if (error) {
        return { success: false, error: error.message || "Failed to sign up" };
      }
      // If auto-logged in or verified, sign in immediately
      const loginRes = await signIn(email, password);
      return loginRes;
    } catch (err: any) {
      return { success: false, error: err?.message || "Unexpected sign up error" };
    }
  };

  const signOut = async () => {
    try {
      await insforge.auth.signOut();
    } catch (err) {
      console.error("Sign out error:", err);
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
