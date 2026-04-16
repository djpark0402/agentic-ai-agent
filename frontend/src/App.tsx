import { useState } from "react";
import { streamChat } from "./api";
import type { Message } from "./types";

export default function App() {
  const [system, setSystem] = useState("You are a helpful assistant.");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const send = async () => {
    if (!input.trim() || loading) return;
    setError(null);
    const userMsg: Message = { role: "user", content: input };
    setMessages([...messages, userMsg, { role: "assistant", content: "" }]);
    setInput("");
    setLoading(true);
    setStatus("요청 중...");

    try {
      await streamChat({
        messages: [...messages, userMsg],
        system,
        onEvent: (ev) => {
          if (ev.type === "status") {
            setStatus(ev.label);
          } else if (ev.type === "token") {
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = {
                ...copy[copy.length - 1],
                content: copy[copy.length - 1].content + ev.content,
              };
              return copy;
            });
          }
        },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStatus(null);
    }
  };

  const reset = () => {
    setMessages([]);
    setError(null);
    setStatus(null);
  };

  return (
    <div className="app">
      <h1>Solar Chat</h1>

      <section className="system">
        <label>System Prompt</label>
        <textarea
          value={system}
          onChange={(e) => setSystem(e.target.value)}
          rows={2}
        />
      </section>

      <section className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <div className="role">{m.role}</div>
            <div className="content">
              {m.content || (loading && i === messages.length - 1 ? "…" : "")}
            </div>
          </div>
        ))}
        {loading && status && (
          <div className="status">
            <span className="dot" /> {status}
          </div>
        )}
      </section>

      {error && <div className="error">Error: {error}</div>}

      <section className="input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="메시지를 입력하세요..."
          rows={3}
        />
        <div className="buttons">
          <button onClick={send} disabled={loading}>
            {loading ? "전송 중..." : "전송"}
          </button>
          <button onClick={reset} disabled={loading}>
            리셋
          </button>
        </div>
      </section>
    </div>
  );
}
