import type { Message } from "./types";

export type StreamEvent =
  | { type: "status"; stage: string; label: string; tool?: string }
  | { type: "token"; content: string }
  | { type: "done" }
  | { type: "error"; message: string };

export type Conversation = {
  id: string;
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type StoredMessage = {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
};

export async function streamChat(opts: {
  messages: Message[];
  system: string;
  conversationId?: string;
  onEvent: (e: StreamEvent) => void;
  signal?: AbortSignal;
}): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: opts.messages,
      system: opts.system,
      conversation_id: opts.conversationId,
    }),
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const event = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      for (const line of event.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        const payload = JSON.parse(line.slice(6)) as StreamEvent;
        opts.onEvent(payload);
        if (payload.type === "error") throw new Error(payload.message);
        if (payload.type === "done") return;
      }
    }
  }
}

export async function listConversations(sessionId: string): Promise<Conversation[]> {
  const res = await fetch(`/api/conversations?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function createConversation(
  sessionId: string,
  title?: string,
): Promise<Conversation> {
  const res = await fetch("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, title: title ?? null }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getMessages(conversationId: string): Promise<StoredMessage[]> {
  const res = await fetch(`/api/conversations/${conversationId}/messages`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`/api/conversations/${conversationId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
