"use client";

export function LoadingPanel({ label }: { label: string }) {
  return (
    <div role="status" className="rounded-card bg-surface p-8 text-center text-muted">
      {label}
    </div>
  );
}

export function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-card bg-surface p-8">
      <p>{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-control bg-brand px-4 py-2 text-brand-foreground"
      >
        Try again
      </button>
    </div>
  );
}
