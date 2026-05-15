import type { User } from "@/lib/types";
import config from "@/lib/config";
import httpClient from "@/lib/api/http-client";

const REQUEST_GMAIL_ACCESS = true;

export async function signInWithGoogle(): Promise<void> {
  const res = await fetch(
    `${config.api.baseUrl}/auth/google/signin?request_gmail_access=${REQUEST_GMAIL_ACCESS}`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    },
  );
  if (!res.ok) throw new Error("Failed to initiate sign-in");
  const { url } = (await res.json()) as { url: string };
  window.location.href = url;
}

export async function storeGoogleToken(
  googleRefreshToken: string,
  googleAccessToken: string | null,
): Promise<void> {
  await httpClient.post("/auth/store-google-token", {
    google_refresh_token: googleRefreshToken,
    google_access_token: googleAccessToken,
  });
}

export async function callback(
  code: string,
  state: string,
  request_gmail_access: boolean,
): Promise<void> {
  await httpClient.post(
    "/auth/callback",
    { code, state, request_gmail_access },
    { includeAuth: false },
  );
}

export async function exchangeCode(code: string, state: string): Promise<void> {
  await httpClient.post("/auth/exchange", { code, state });
}

export async function signOut(): Promise<void> {
  await httpClient.post("/auth/signout").catch(() => undefined);
}

export async function connectGoogle(accessToken: string): Promise<void> {
  const res = await fetch(`${config.api.baseUrl}/auth/connect-google`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      error?: { message?: string };
    };
    throw new Error(
      body.error?.message ?? `connect-google failed: ${res.status}`,
    );
  }
}

// Requires localStorage.access_token to be synced by useAuth first
export async function getMe(): Promise<User> {
  return httpClient.get<User>("/auth/me");
}

// Backward-compatible class/singleton for lib/api/index.ts re-exports
export class AuthService {
  signInWithGoogle = signInWithGoogle;
  signOut = signOut;
  getMe = getMe;
}

export const authService = new AuthService();
export default authService;
