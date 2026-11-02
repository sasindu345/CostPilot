"use client";

import { useCurrentUser, useSignOut } from "@/lib/current-user";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

export function SettingsPage() {
  const { data: user } = useCurrentUser();
  const signOut = useSignOut();

  if (!user) {
    return null;
  }

  return (
    <section>
      <h1 className="text-3xl font-bold">Settings</h1>
      <p className="mt-1 text-muted">Manage your account and security.</p>
      <div className="mt-6 grid max-w-3xl gap-6">
        <div className="rounded-card border border-border bg-surface p-6 shadow-card">
          <h2 className="mb-4 text-lg font-semibold">Account</h2>
          <dl className="grid gap-4 sm:grid-cols-2">
            <Detail label="Name" value={user.display_name} />
            <Detail label="Email" value={user.email} />
            <Detail label="Workspace" value={user.workspace_name} />
            <Detail label="Role" value={user.role} />
          </dl>
        </div>
        <div className="rounded-card border border-border bg-surface p-6 shadow-card">
          <h2 className="mb-2 text-lg font-semibold">Security</h2>
          <p className="mb-4 text-muted">Your password and sign-in are managed by Keycloak.</p>
          <div className="flex gap-3">
            <a
              href={user.account_url}
              className="rounded-control bg-brand px-4 py-2 text-brand-foreground"
            >
              Manage password
            </a>
            <button
              type="button"
              disabled={signOut.isPending}
              onClick={() => signOut.mutate()}
              className="rounded-control border border-border px-4 py-2"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
