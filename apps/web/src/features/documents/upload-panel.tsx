"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";

import { useCurrentUser } from "@/lib/current-user";
import { useUploadDocument } from "@/lib/documents";

const ACCEPTED_FILES = ".csv,.gz";
const BYTES_PER_MB = 1024 * 1024;

export function UploadPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [sizeError, setSizeError] = useState<string>();
  const upload = useUploadDocument();
  const { data: user } = useCurrentUser();

  function sendFiles(files: FileList | null) {
    const file = files?.[0];
    setSizeError(undefined);
    upload.reset();
    if (user && file && file.size > user.max_upload_mb * BYTES_PER_MB) {
      setSizeError(`That file is too large. The limit is ${user.max_upload_mb} MB.`);
    } else if (file) {
      upload.mutate(file);
    }
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  const borderClass = isDragging ? "border-brand bg-brand-tint" : "border-brand-border bg-surface";

  return (
    <section aria-label="Upload a bill">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          sendFiles(event.dataTransfer.files);
        }}
        className={`flex flex-col items-center gap-3 rounded-card border-2 border-dashed p-8 text-center ${borderClass}`}
      >
        <Upload aria-hidden className="size-8 text-brand" />
        <p className="font-medium">Drag a billing file here</p>
        <p className="text-sm text-muted">AWS .csv or .csv.gz files</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_FILES}
          aria-label="Choose a billing file"
          className="sr-only"
          onChange={(event) => sendFiles(event.target.files)}
        />
        <button
          type="button"
          disabled={upload.isPending}
          onClick={() => inputRef.current?.click()}
          className="rounded-control bg-brand px-4 py-2 text-brand-foreground disabled:opacity-60"
        >
          {upload.isPending ? "Uploading…" : "Choose file"}
        </button>
      </div>
      {(sizeError ?? upload.error) && (
        <p role="alert" className="mt-3 rounded-control bg-danger-tint px-4 py-2 text-danger">
          {sizeError ?? upload.error?.message}
        </p>
      )}
    </section>
  );
}
