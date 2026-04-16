import type { Message } from "./types";

export type StreamEvent =
  | { type: "status"; stage: string; label: string; tool?: string }
  | { type: "token"; content: string }
  | { type: "done" }
  | { type: "error"; message: string };

export async function streamChat(opts: {
  messages: Message[];
  system: string;
  onEvent: (e: StreamEvent) => void;
  signal?: AbortSignal;
}): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: opts.messages, system: opts.system }),
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
