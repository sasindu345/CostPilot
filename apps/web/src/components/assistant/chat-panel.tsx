"use client";

import { MessageSquare, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  askQuestion,
  useAssistantInfo,
  useConversations,
  useMessages,
  useRefreshChat,
  useStartConversation,
  type AnswerTrace,
  type Source,
} from "@/lib/assistant";

function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return null;
  }
  return (
    <ul className="mt-2 border-t border-border pt-2 text-sm">
      {sources.map((source) => (
        <li key={source.url}>
          <a href={source.url} target="_blank" rel="noreferrer" className="text-brand underline">
            {source.title}
          </a>
        </li>
      ))}
    </ul>
  );
}

const GRADE_MEANINGS: Record<string, string> = {
  A: "Full evidence",
  B: "Good evidence, with a small gap",
  C: "Limited evidence",
  D: "Not enough evidence",
};
const MILLISECONDS = 1000;

function AnswerDetails({ grade, trace }: { grade?: string | null; trace?: AnswerTrace }) {
  const { routes = [], facts = [], limitations = [], checks, metrics } = trace ?? {};
  const seconds = ((metrics?.total_ms ?? 0) / MILLISECONDS).toFixed(1);

  return (
    <div className="mt-2 border-t border-border pt-2 text-sm">
      {grade && (
        <p className="font-medium">
          Evidence grade {grade}: {GRADE_MEANINGS[grade]}
        </p>
      )}
      <details>
        <summary className="cursor-pointer text-muted">How was this answer made?</summary>
        <ul className="mt-1 grid gap-1">
          {routes.length > 0 && <li>Specialists: {routes.join(", ")}</li>}
          {facts.map((fact) => (
            <li key={fact.label}>
              {fact.label}: {fact.value}
            </li>
          ))}
          {limitations.map((limitation) => (
            <li key={limitation}>Limit: {limitation}</li>
          ))}
          {checks?.blocked_by_guardrail && <li>Blocked by a safety rule, with no AI used</li>}
          {checks?.used_template && <li>Written by code, as the AI answer failed its check</li>}
          {checks?.answer_attempts !== undefined && !checks.used_template && (
            <li>Passed the number check on attempt {checks.answer_attempts}</li>
          )}
          <li>
            {metrics?.ai_calls ?? 0} AI calls in {seconds} seconds
          </li>
        </ul>
      </details>
    </div>
  );
}

function Bubble({
  isUser,
  text,
  sources = [],
  children,
}: {
  isUser: boolean;
  text: string;
  sources?: Source[];
  children?: React.ReactNode;
}) {
  const style = isUser
    ? "ml-8 bg-brand text-brand-foreground"
    : "mr-8 border border-border bg-surface-subtle";
  return (
    <div className={`rounded-control px-4 py-3 ${style}`}>
      <p className="whitespace-pre-wrap">{text}</p>
      <Sources sources={sources} />
      {children}
    </div>
  );
}

type Pending = {
  question: string;
  status: string;
  answer: string;
};

export function ChatPanel({ className = "" }: { className?: string }) {
  const { data: info } = useAssistantInfo();
  const { data: conversations } = useConversations();
  const conversationId = conversations?.[0]?.id;
  const { data: messages } = useMessages(conversationId);
  const startConversation = useStartConversation();
  const refreshChat = useRefreshChat();
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<Pending>();
  const [error, setError] = useState<string>();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [messages, pending]);

  async function send(question: string) {
    if (!question.trim() || pending) {
      return;
    }
    setDraft("");
    setError(undefined);
    setPending({ question, status: "Starting", answer: "" });
    try {
      const id = conversationId ?? (await startConversation.mutateAsync()).id;
      await askQuestion(id, question, (event) => {
        setPending((current) => {
          if (!current) {
            return current;
          }
          if (event.type === "status") {
            return { ...current, status: event.text };
          }
          if (event.type === "text") {
            return { ...current, answer: current.answer + event.text };
          }
          return event.type === "replace" ? { ...current, answer: event.text } : current;
        });
      });
      await refreshChat();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
      setDraft(question);
    } finally {
      setPending(undefined);
    }
  }

  const isEmpty = !pending && (messages?.length ?? 0) === 0;

  return (
    <section
      aria-label="AI Assistant"
      className={`flex min-h-0 flex-col rounded-card border border-border bg-surface p-5 shadow-card ${className}`}
    >
      <div className="mb-3 flex items-center gap-3">
        <MessageSquare aria-hidden className="size-6 text-brand" />
        <h2 className="text-lg font-semibold">AI Assistant</h2>
      </div>
      {info?.is_free_tier && (
        <p className="mb-3 rounded-control bg-brand-tint px-3 py-2 text-sm">
          This uses a free Gemini key, so please use made-up bills only.
        </p>
      )}

      <div aria-live="polite" className="grid flex-1 content-start gap-3 overflow-y-auto">
        {isEmpty && (
          <>
            <p className="text-muted">
              Ask about your cloud spending, trends, or optimization opportunities.
            </p>
            {info?.suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => send(suggestion)}
                className="rounded-control border border-border px-4 py-2 text-left font-medium hover:bg-surface-subtle"
              >
                {suggestion}
              </button>
            ))}
          </>
        )}
        {messages?.map((message) => (
          <Bubble
            key={message.id}
            isUser={message.role === "user"}
            text={message.content}
            sources={message.sources}
          >
            {message.role === "assistant" && (
              <AnswerDetails grade={message.grade} trace={message.trace as AnswerTrace} />
            )}
          </Bubble>
        ))}
        {pending && (
          <>
            <Bubble isUser text={pending.question} />
            {pending.answer ? (
              <Bubble isUser={false} text={pending.answer} />
            ) : (
              <p role="status" className="text-sm text-muted">
                {pending.status}…
              </p>
            )}
          </>
        )}
        <div ref={endRef} />
      </div>

      {error && (
        <p role="alert" className="mt-3 rounded-control bg-danger-tint px-3 py-2 text-danger">
          {error}
        </p>
      )}
      <form
        className="mt-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          send(draft);
        }}
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          aria-label="Ask about your cloud costs"
          placeholder="Ask anything about your cloud costs..."
          className="min-w-0 flex-1 rounded-control border border-border px-3 py-2"
        />
        <button
          type="submit"
          aria-label="Send"
          disabled={Boolean(pending) || !draft.trim()}
          className="rounded-control bg-brand p-3 text-brand-foreground disabled:opacity-60"
        >
          <Send aria-hidden className="size-5" />
        </button>
      </form>
    </section>
  );
}
