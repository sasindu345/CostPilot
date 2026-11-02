import {
  CircleAlert,
  CircleCheck,
  Clock,
  LoaderCircle,
  Replace,
  type LucideIcon,
} from "lucide-react";

import type { Document } from "@/lib/documents";

const STATUS_STYLES: Record<
  Document["status"],
  { label: string; icon: LucideIcon; className: string }
> = {
  queued: { label: "Waiting", icon: Clock, className: "bg-surface-subtle text-muted" },
  processing: {
    label: "Processing",
    icon: LoaderCircle,
    className: "bg-surface-subtle text-muted",
  },
  processed: { label: "Processed", icon: CircleCheck, className: "bg-brand-tint text-success" },
  failed: { label: "Failed", icon: CircleAlert, className: "bg-danger-tint text-danger" },
  replaced: { label: "Replaced", icon: Replace, className: "bg-surface-subtle text-muted" },
};

export function StatusBadge({ status }: { status: Document["status"] }) {
  const { label, icon: Icon, className } = STATUS_STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${className}`}
    >
      <Icon aria-hidden className="size-4" />
      {label}
    </span>
  );
}
