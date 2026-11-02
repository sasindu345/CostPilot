"use client";

import { useEffect } from "react";

import { ApiError } from "@/lib/api";
import { LOGIN_PATH, useCurrentUser } from "@/lib/current-user";

/** Shows the app only to signed-in users, and sends everyone else to the login page. */
export function AuthGate({ children }: Readonly<{ children: React.ReactNode }>) {
  const { data, error, isPending, refetch } = useCurrentUser();
  const isSignedOut = error instanceof ApiError && error.status === 401;

  useEffect(() => {
    if (isSignedOut) {
      window.location.assign(LOGIN_PATH);
    }
  }, [isSignedOut]);

  if (data) {
    return children;
  }
  if (isPending || isSignedOut) {
    return (
      <div role="status" className="flex min-h-screen items-center justify-center text-muted">
        Loading CostPilot…
      </div>
    );
  }
  return (
    <div role="alert" className="flex min-h-screen flex-col items-center justify-center gap-3">
      <p>We could not reach CostPilot.</p>
      <button
        type="button"
        onClick={() => refetch()}
        className="rounded-control bg-brand px-4 py-2 text-brand-foreground"
      >
        Try again
      </button>
    </div>
  );
}
