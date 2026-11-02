"use client";

import { ArrowRight, FileText } from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/card";
import { StatusBadge } from "@/components/status-badge";
import { useDocuments } from "@/lib/documents";
import { formatFileSize, formatMonthRange } from "@/lib/format";

const RECENT_COUNT = 3;

export function RecentDocuments() {
  const { data: documents } = useDocuments();

  return (
    <Card
      title="Recent Documents"
      action={
        <Link href="/documents" className="flex items-center gap-1 text-sm font-medium text-brand">
          View all
          <ArrowRight aria-hidden className="size-4" />
        </Link>
      }
    >
      <ul className="grid gap-3">
        {documents?.slice(0, RECENT_COUNT).map((document) => (
          <li key={document.id} className="flex items-center gap-3">
            <FileText aria-hidden className="size-6 shrink-0 text-brand" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{document.file_name}</p>
              <p className="text-sm text-muted">
                {formatMonthRange(document.first_month, document.last_month)} ·{" "}
                {formatFileSize(document.size_bytes)}
              </p>
            </div>
            <StatusBadge status={document.status} />
          </li>
        ))}
      </ul>
    </Card>
  );
}
