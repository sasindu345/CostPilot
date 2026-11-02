"use client";

import { Upload } from "lucide-react";
import Link from "next/link";

import { isWorking, useAddSampleDocument, useDocuments } from "@/lib/documents";

export function EmptyOverview() {
  const addSample = useAddSampleDocument();
  const { data: documents } = useDocuments();
  const isProcessing = addSample.isPending || documents?.some(isWorking);

  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-border bg-surface p-10 text-center shadow-card">
      <Upload aria-hidden className="size-8 text-brand" />
      <h2 className="text-lg font-semibold">
        {isProcessing ? "Reading your bill…" : "No spending to show yet"}
      </h2>
      <p className="max-w-md text-muted">
        Upload a cloud bill to see your spending here, or explore the app with made-up data.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Link
          href="/documents"
          className="rounded-control bg-brand px-4 py-2 text-brand-foreground"
        >
          Upload a bill
        </Link>
        <button
          type="button"
          disabled={isProcessing}
          onClick={() => addSample.mutate()}
          className="rounded-control border border-border px-4 py-2 disabled:opacity-60"
        >
          Try sample data
        </button>
      </div>
      {addSample.error && (
        <p role="alert" className="text-danger">
          {addSample.error.message}
        </p>
      )}
    </div>
  );
}
