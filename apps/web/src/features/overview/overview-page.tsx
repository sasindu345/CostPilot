"use client";

import { useState } from "react";

import { ChatPanel } from "@/components/assistant/chat-panel";
import { Card } from "@/components/card";
import { SpendingChart } from "@/components/charts/spending-chart";
import { TopServices } from "@/components/charts/top-services";
import { ErrorPanel, LoadingPanel } from "@/components/data-states";
import { PeriodSelect } from "@/components/period-select";
import { useOverview } from "@/lib/analytics";
import { formatMonth } from "@/lib/format";

import { EmptyOverview } from "./empty-overview";
import { RecentDocuments } from "./recent-documents";
import { StatCards } from "./stat-cards";

const DEFAULT_MONTHS = 6;

export function OverviewPage() {
  const [months, setMonths] = useState(DEFAULT_MONTHS);
  const { data: overview, error, isPending, refetch } = useOverview({ months });

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Welcome to CostPilot</h1>
          <p className="mt-1 text-muted">Your AI-powered cloud cost management workspace.</p>
        </div>
        {overview && <PeriodSelect value={months} onChange={setMonths} />}
      </div>

      {isPending && <LoadingPanel label="Loading your spending…" />}
      {error && <ErrorPanel message={error.message} onRetry={() => refetch()} />}
      {overview === null && <EmptyOverview />}
      {overview && (
        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_var(--token-assistant-panel-width)]">
          <div className="grid min-w-0 content-start gap-4">
            <StatCards overview={overview} months={months} />
            <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
              <Card title="Monthly Cloud Spending">
                <SpendingChart overview={overview} />
              </Card>
              <Card title={`Top Services (${formatMonth(overview.latest_month)})`}>
                <TopServices overview={overview} />
              </Card>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <RecentDocuments />
              <Card title="AI Recommendations">
                <p className="text-muted">
                  Recommendations will appear here, with their evidence, once the AI assistant is
                  ready.
                </p>
              </Card>
            </div>
          </div>
          <ChatPanel className="hidden max-h-[var(--token-chat-height)] 2xl:flex" />
        </div>
      )}
    </section>
  );
}
