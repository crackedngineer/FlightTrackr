"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeMailCode } from "@/lib/api/mail-connection-service";
import { Loader2, CheckCircle, XCircle, Plane } from "lucide-react";

type Status = "loading" | "success" | "error";

const CONFIG: Record<
  Status,
  { icon: typeof Loader2; iconCls: string; title: string; borderCls: string }
> = {
  loading: {
    icon: Loader2,
    iconCls: "text-amber-400 animate-spin",
    title: "Connecting inbox…",
    borderCls: "border-amber-500/20",
  },
  success: {
    icon: CheckCircle,
    iconCls: "text-emerald-400",
    title: "Inbox connected!",
    borderCls: "border-emerald-500/20",
  },
  error: {
    icon: XCircle,
    iconCls: "text-red-400",
    title: "Connection Failed",
    borderCls: "border-red-500/20",
  },
};

export default function MailCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { code, state, provider, oauthError, oauthErrDesc } = useMemo(() => {
    return {
      code: searchParams.get("code"),
      state: searchParams.get("state"),
      provider: searchParams.get("provider") ?? "gmail",
      oauthError: searchParams.get("error"),
      oauthErrDesc: searchParams.get("error_description"),
    };
  }, [searchParams]);

  const hasOAuthError = !!oauthError || !code || !state;

  const [status, setStatus] = useState<Status>(hasOAuthError ? "error" : "loading");
  const [message, setMessage] = useState(
    hasOAuthError
      ? (oauthErrDesc ?? oauthError ?? "Missing OAuth parameters")
      : "Verifying access…",
  );

  useEffect(() => {
    if (hasOAuthError) {
      const t = setTimeout(() => router.replace("/dashboard"), 3000);
      return () => clearTimeout(t);
    }

    let isMounted = true;

    const handleConnect = async () => {
      try {
        await exchangeMailCode(provider, code!, state!);

        if (!isMounted) return;

        setStatus("success");
        setMessage("Gmail connected! Starting sync…");

        setTimeout(() => {
          router.replace("/dashboard");
        }, 1200);
      } catch (err) {
        if (!isMounted) return;

        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Connection failed");

        setTimeout(() => {
          router.replace("/dashboard");
        }, 3000);
      }
    };

    handleConnect();

    return () => {
      isMounted = false;
    };
  }, [hasOAuthError, code, state, provider, router]);

  const { icon: Icon, iconCls, title, borderCls } = CONFIG[status];

  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
      <div className="absolute inset-0 bg-dot-grid opacity-[0.12]" />
      <div className="absolute inset-0 bg-gradient-to-br from-amber-500/[0.04] via-transparent to-blue-900/[0.06]" />

      <div
        className={`relative z-10 w-full max-w-sm mx-4 rounded-2xl border ${borderCls} bg-card/60 backdrop-blur-md p-8 text-center space-y-6`}
      >
        <div className="flex items-center justify-center gap-2">
          <div className="w-7 h-7 rounded-lg border border-amber-500/25 bg-amber-500/8 flex items-center justify-center">
            <Plane className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <span className="font-data text-[11px] tracking-[0.35em] text-amber-500/60 uppercase">
            FlightTrackr
          </span>
        </div>

        <Icon className={`w-8 h-8 mx-auto ${iconCls}`} />

        <div>
          <h1 className="text-lg font-semibold text-foreground">{title}</h1>
          <p className="font-data text-[11px] tracking-[0.06em] text-muted-foreground mt-2 leading-relaxed">
            {message}
          </p>
        </div>

        {status === "loading" && (
          <div className="flex justify-center gap-1.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1 h-1 rounded-full bg-amber-400/50 animate-pulse"
                style={{ animationDelay: `${i * 180}ms` }}
              />
            ))}
          </div>
        )}

        {status === "error" && (
          <p className="font-data text-[10px] tracking-[0.2em] text-muted-foreground/40 uppercase">
            Redirecting…
          </p>
        )}
      </div>
    </div>
  );
}
