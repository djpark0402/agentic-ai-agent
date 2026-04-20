import { useEffect, useState } from "react";
import {
  createConversation,
  deleteConversation,
  getMessages,
  listConversations,
  streamChat,
  type Conversation,
} from "./api";
import { getSessionId } from "./session";
import type { Message } from "./types";

export default function App() {
  const sessionId = getSessionId();

  const [system, setSystem] = useState("You are a helpful assistant.");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    refreshConversations();
  }, []);

  async function refreshConversations() {
    try {
      const list = await listConversations(sessionId);
      setConversations(list);
      if (!activeId && list.length > 0) {
        selectConversation(list[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function selectConversation(id: string) {
    setActiveId(id);
    setError(null);
    try {
      const msgs = await getMessages(id);
      setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function newChat() {
    // 빈 대화를 미리 만들지 않음 — 첫 메시지 전송 시점에 그 내용으로 제목을 지어 생성
    setActiveId(null);
    setMessages([]);
    setError(null);
  }

  async function removeChat(id: string) {
    try {
      await deleteConversation(id);
      const next = conversations.filter((c) => c.id !== id);
      setConversations(next);
      if (activeId === id) {
        if (next.length > 0) selectConversation(next[0].id);
        else {
          setActiveId(null);
          setMessages([]);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const send = async () => {
    if (!input.trim() || loading) return;
    setError(null);

    let convId = activeId;
    if (!convId) {
      try {
        const conv = await createConversation(sessionId, input.slice(0, 40));
        convId = conv.id;
        setConversations([conv, ...conversations]);
        setActiveId(conv.id);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        return;
      }
    }

    const userMsg: Message = { role: "user", content: input };
    setMessages([...messages, userMsg, { role: "assistant", content: "" }]);
    setInput("");
    setLoading(true);
    setStatus("요청 중...");

    try {
      await streamChat({
        messages: [...messages, userMsg],
        system,
        conversationId: convId,
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
      refreshConversations();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStatus(null);
    }
  };

  return (
    <div className="app layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>대화</h2>
          <button onClick={newChat} disabled={loading}>
            + 새 채팅
          </button>
        </div>
        <ul className="conv-list">
          {conversations.length === 0 && (
            <li className="conv-empty">대화가 없습니다</li>
          )}
          {conversations.map((c) => (
            <li
              key={c.id}
              className={`conv-item ${c.id === activeId ? "active" : ""}`}
              onClick={() => selectConversation(c.id)}
            >
              <span className="conv-title">{c.title || "(제목 없음)"}</span>
              <button
                className="conv-del"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("삭제하시겠습니까?")) removeChat(c.id);
                }}
                aria-label="삭제"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
        <div className="sidebar-footer">
          <small>session: {sessionId.slice(0, 8)}…</small>
        </div>
      </aside>

      <main className="main">
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
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
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
          </div>
        </section>
      </main>
    </div>
  );
}
