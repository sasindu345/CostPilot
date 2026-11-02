"use client";

import { Lightbulb } from "lucide-react";

import { Card } from "@/components/card";
import { formatMoney } from "@/lib/format";
import { useRecommendations } from "@/lib/recommendations";

export function RecommendationsCard() {
  const { data: recommendations } = useRecommendations();

  return (
    <Card title="AI Recommendations">
      {recommendations?.length === 0 && (
        <p className="text-muted">No recommendations for your latest bill.</p>
      )}
      <ul className="grid gap-3">
        {recommendations?.map((item) => (
          <li key={item.id} className="flex gap-3 rounded-control bg-surface-subtle p-3">
            <Lightbulb aria-hidden className="size-5 shrink-0 text-brand" />
            <div className="min-w-0">
              <p className="font-medium">{item.title}</p>
              <p className="text-sm text-muted">
                {item.monthly_saving === null
                  ? "Saving: needs usage data"
                  : `Saving: ${formatMoney(item.monthly_saving, item.currency)} a month`}
              </p>
              {item.source_url && (
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-brand underline"
                >
                  {item.source_title}
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
