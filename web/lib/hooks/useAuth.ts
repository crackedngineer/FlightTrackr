"use client";

import { useState, useEffect, useCallback } from "react";
import {
  signOut as apiSignOut,
  getMe,
  signInWithGoogle,
} from "@/lib/api/auth-service";
import type { User } from "@/lib/types";

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  error: string | null;
}

function enrichUser(u: User): User {
  return {
    ...u,
    name:
      u.name ??
      ((u.user_metadata?.full_name ?? u.user_metadata?.name) as
        | string
        | undefined),
  };
}

export function useAuth(): AuthState & {
  signIn: (_provider: "google") => Promise<void>;
  signOut: () => Promise<void>;
  refreshAuth: () => Promise<void>;
} {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isAuthenticated: false,
    user: null,
    error: null,
  });

  // On mount: check auth state via HttpOnly cookie — no localStorage needed
  useEffect(() => {
    getMe()
      .then((user) => {
        setState({
          isLoading: false,
          isAuthenticated: true,
          user: enrichUser(user),
          error: null,
        });
      })
      .catch(() => {
        setState({
          isLoading: false,
          isAuthenticated: false,
          user: null,
          error: null,
        });
      });
  }, []);

  const signIn = useCallback(async (_provider: "google") => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      if (_provider === "google") await signInWithGoogle();
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : "Sign in failed",
      }));
      throw err;
    }
  }, []);

  const signOut = useCallback(async () => {
    await apiSignOut().catch(() => {});
    setState({
      isLoading: false,
      isAuthenticated: false,
      user: null,
      error: null,
    });
    window.location.href = "/login";
  }, []);

  const refreshAuth = useCallback(async () => {
    try {
      const user = await getMe();
      setState((prev) => ({
        ...prev,
        isAuthenticated: true,
        user: enrichUser(user),
      }));
    } catch {
      setState((prev) => ({ ...prev, isAuthenticated: false, user: null }));
    }
  }, []);

  return { ...state, signIn, signOut, refreshAuth };
}
