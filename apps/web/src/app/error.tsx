"use client";

import { ErrorPanel } from "@/components/data-states";

export default function ErrorPage({ retry }: { retry: () => void }) {
  return <ErrorPanel message="Something went wrong on this page." onRetry={retry} />;
}
