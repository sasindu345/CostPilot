"use client";

import { DocumentRow } from "./document-row";
import { UploadPanel } from "./upload-panel";
import { useDocuments } from "@/lib/documents";

function DocumentList() {
  const { data: documents, error, isPending, refetch } = useDocuments();

  if (isPending) {
    return (
      <div role="status" className="p-8 text-center text-muted">
        Loading your documents…
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" className="flex flex-col items-center gap-3 p-8">
        <p>{error.message}</p>
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
  if (documents.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="font-medium">No documents yet</p>
        <p className="mt-1 text-muted">Upload your first bill to start tracking your spending.</p>
      </div>
    );
  }
  return (
    <ul>
      {documents.map((document) => (
        <DocumentRow key={document.id} document={document} />
      ))}
    </ul>
  );
}

export function DocumentsPage() {
  return (
    <section>
      <h1 className="text-3xl font-bold">Documents</h1>
      <p className="mt-1 text-muted">Upload and manage your cloud billing documents.</p>
      <div className="mt-6 grid max-w-4xl gap-6">
        <UploadPanel />
        <div className="rounded-card border border-border bg-surface shadow-card">
          <h2 className="border-b border-border p-4 text-lg font-semibold">Your documents</h2>
          <DocumentList />
        </div>
      </div>
    </section>
  );
}
