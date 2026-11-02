"use client";

import { ChevronDown, FileText, RotateCw, Trash2 } from "lucide-react";
import { useState } from "react";

import { StatusBadge } from "./status-badge";
import {
  useDeleteDocument,
  useReprocessDocument,
  type Document,
} from "./use-documents";
import { formatDateTime, formatFileSize, formatMonthRange, providerName } from "@/lib/format";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

export function DocumentRow({ document }: { document: Document }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const remove = useDeleteDocument();
  const reprocess = useReprocessDocument();
  const canReprocess = !["queued", "processing"].includes(document.status);
  const actionError = remove.error ?? reprocess.error;

  return (
    <li className="border-b border-border last:border-b-0">
      <div className="flex items-center gap-4 p-4">
        <FileText aria-hidden className="size-6 shrink-0 text-brand" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{document.file_name}</p>
          <p className="text-sm text-muted">
            {formatDateTime(document.created_at)} · {formatFileSize(document.size_bytes)}
          </p>
        </div>
        <StatusBadge status={document.status} />
        <button
          type="button"
          aria-expanded={isOpen}
          aria-label={`Details for ${document.file_name}`}
          onClick={() => setIsOpen((open) => !open)}
          className="rounded-control p-2 hover:bg-surface-subtle"
        >
          <ChevronDown aria-hidden className={`size-5 ${isOpen ? "rotate-180" : ""}`} />
        </button>
      </div>
      {document.error_message && (
        <p className="mx-4 mb-4 rounded-control bg-danger-tint px-4 py-2 text-sm text-danger">
          {document.error_message}
        </p>
      )}
      {document.status === "replaced" && (
        <p className="mx-4 mb-4 text-sm text-muted">
          A newer or more detailed file covers these months, so this one is not counted.
        </p>
      )}
      {isOpen && (
        <div className="px-4 pb-4">
          <dl className="mb-4 grid gap-4 sm:grid-cols-3">
            <Detail
              label="Records"
              value={document.row_count?.toLocaleString() ?? "Not read yet"}
            />
            <Detail label="Provider" value={providerName(document.provider_name)} />
            <Detail
              label="Billing period"
              value={formatMonthRange(document.first_month, document.last_month)}
            />
            <Detail
              label="Processed"
              value={document.processed_at ? formatDateTime(document.processed_at) : "Not yet"}
            />
          </dl>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!canReprocess || reprocess.isPending}
              onClick={() => reprocess.mutate(document.id)}
              className="flex items-center gap-2 rounded-control border border-border px-3 py-2 disabled:opacity-60"
            >
              <RotateCw aria-hidden className="size-4" />
              Reprocess
            </button>
            {isConfirmingDelete ? (
              <>
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(document.id)}
                  className="rounded-control bg-danger px-3 py-2 text-brand-foreground"
                >
                  Yes, delete it
                </button>
                <button
                  type="button"
                  onClick={() => setIsConfirmingDelete(false)}
                  className="rounded-control border border-border px-3 py-2"
                >
                  Keep it
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setIsConfirmingDelete(true)}
                className="flex items-center gap-2 rounded-control border border-border px-3 py-2 text-danger"
              >
                <Trash2 aria-hidden className="size-4" />
                Delete
              </button>
            )}
          </div>
          {actionError && (
            <p role="alert" className="mt-3 text-sm text-danger">
              {actionError.message}
            </p>
          )}
        </div>
      )}
    </li>
  );
}
