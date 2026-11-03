"use client";

import { useState } from "react";

import { useDeleteAccount, useExportData } from "@/lib/account";
import { type CurrentUser, useCurrentUser, useSignOut } from "@/lib/current-user";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function YourData({ user }: { user: CurrentUser }) {
  const exportData = useExportData();
  const deleteAccount = useDeleteAccount();
  const [confirmEmail, setConfirmEmail] = useState("");
  const confirmed = confirmEmail.trim().toLowerCase() === user.email.toLowerCase();

  return (
    <div className="rounded-card border border-border bg-surface p-6 shadow-card">
      <h2 className="mb-2 text-lg font-semibold">Your data</h2>
      <p className="mb-4 text-muted">
        Download every record in your workspace as one JSON file. Your original bill files are not
        included.
      </p>
      <button
        type="button"
        disabled={exportData.isPending}
        onClick={() => exportData.mutate()}
        className="rounded-control border border-border px-4 py-2"
      >
        {exportData.isPending ? "Preparing…" : "Download my data"}
      </button>
      {exportData.isError && <p className="mt-2 text-danger">{exportData.error.message}</p>}

      <h3 className="mt-6 mb-2 font-semibold text-danger">Delete account</h3>
      <p className="mb-3 text-muted">
        This deletes your workspace, bills, chats and login. It cannot be undone.
      </p>
      <label className="block text-sm text-muted" htmlFor="confirm-email">
        Type your email address to confirm
      </label>
      <div className="mt-1 flex flex-wrap gap-3">
        <input
          id="confirm-email"
          type="email"
          autoComplete="off"
          value={confirmEmail}
          onChange={(event) => setConfirmEmail(event.target.value)}
          className="min-w-0 flex-1 rounded-control border border-border px-3 py-2"
        />
        <button
          type="button"
          disabled={!confirmed || deleteAccount.isPending}
          onClick={() => deleteAccount.mutate({ confirm_email: confirmEmail })}
          className="rounded-control bg-danger px-4 py-2 text-brand-foreground disabled:opacity-50"
        >
          {deleteAccount.isPending ? "Deleting…" : "Delete my account"}
        </button>
      </div>
      {deleteAccount.isError && <p className="mt-2 text-danger">{deleteAccount.error.message}</p>}
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
        <YourData user={user} />
      </div>
    </section>
  );
}
