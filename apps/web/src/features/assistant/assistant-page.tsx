import { ChatPanel } from "@/components/assistant/chat-panel";

export function AssistantPage() {
  return (
    <section>
      <h1 className="text-3xl font-bold">AI Assistant</h1>
      <p className="mt-1 mb-6 text-muted">Ask about your cloud spending, trends, or savings.</p>
      <ChatPanel className="h-[var(--token-chat-height)] max-w-4xl" />
    </section>
  );
}
