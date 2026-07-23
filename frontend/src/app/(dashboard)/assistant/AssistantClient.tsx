"use client";

import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import {
  MessageSquare,
  Send,
  Loader2,
  Bot,
  User,
  Wrench,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import {
  chatWithAssistant,
  getAssistantPrompts,
  AssistantMessage,
  AssistantChatResponse,
} from "@/lib/api";

// ── Simple Markdown renderer (bold, code, tables, line-breaks) ──────────────
function MarkdownText({ text }: { text: string }) {
  const lines = text.split("\n");

  const renderInline = (s: string, key: number) => {
    // Bold: **...**
    const parts = s.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={key}>
        {parts.map((p, i) => {
          if (p.startsWith("**") && p.endsWith("**")) {
            return <strong key={i}>{p.slice(2, -2)}</strong>;
          }
          // Inline code: `...`
          const codeParts = p.split(/(`[^`]+`)/g);
          return codeParts.map((cp, j) =>
            cp.startsWith("`") && cp.endsWith("`") ? (
              <code
                key={j}
                style={{
                  fontFamily: "monospace",
                  background: "rgba(255,255,255,0.08)",
                  padding: "1px 5px",
                  borderRadius: 4,
                  fontSize: "0.9em",
                }}
              >
                {cp.slice(1, -1)}
              </code>
            ) : (
              <span key={j}>{cp}</span>
            )
          );
        })}
      </span>
    );
  };

  const elements: React.ReactNode[] = [];
  let tableBuffer: string[] = [];
  let inTable = false;

  const flushTable = () => {
    if (tableBuffer.length < 2) {
      tableBuffer.forEach((l, i) => elements.push(<div key={`tl-${i}`}>{l}</div>));
      tableBuffer = [];
      inTable = false;
      return;
    }
    const rows = tableBuffer
      .filter((l) => !l.match(/^[\|\s\-:]+$/))
      .map((l) =>
        l
          .split("|")
          .filter((_, i, arr) => i > 0 && i < arr.length - 1)
          .map((c) => c.trim())
      );
    const [header, ...body] = rows;
    elements.push(
      <div
        key={`table-${elements.length}`}
        style={{ overflowX: "auto", margin: "8px 0" }}
      >
        <table
          style={{
            borderCollapse: "collapse",
            fontSize: "0.875rem",
            minWidth: "100%",
          }}
        >
          <thead>
            <tr>
              {header?.map((h, i) => (
                <th
                  key={i}
                  style={{
                    padding: "6px 12px",
                    textAlign: "left",
                    borderBottom: "1px solid rgba(255,255,255,0.12)",
                    fontWeight: 600,
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    style={{
                      padding: "5px 12px",
                      borderBottom: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableBuffer = [];
    inTable = false;
  };

  lines.forEach((line, idx) => {
    if (line.startsWith("|")) {
      inTable = true;
      tableBuffer.push(line);
      return;
    }
    if (inTable) {
      flushTable();
    }

    if (line === "") {
      elements.push(<br key={`br-${idx}`} />);
    } else {
      elements.push(
        <div key={idx} style={{ marginBottom: 2 }}>
          {renderInline(line, idx)}
        </div>
      );
    }
  });

  if (inTable) flushTable();

  return <div style={{ lineHeight: 1.7 }}>{elements}</div>;
}

// ── Tool call badge ─────────────────────────────────────────────────────────
function ToolBadge({ toolName }: { toolName: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "1px 8px",
        borderRadius: 999,
        background: "rgba(99,102,241,0.12)",
        border: "1px solid rgba(99,102,241,0.25)",
        color: "#818cf8",
        fontSize: "0.75rem",
        fontFamily: "monospace",
        fontWeight: 500,
      }}
    >
      <Wrench size={10} />
      {toolName}
    </span>
  );
}

// ── Chat bubble ─────────────────────────────────────────────────────────────
interface BubbleProps {
  role: "user" | "assistant";
  content: string;
  toolCalls?: AssistantChatResponse["tool_calls"];
}

function Bubble({ role, content, toolCalls }: BubbleProps) {
  const isUser = role === "user";
  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        gap: 10,
        alignItems: "flex-start",
        animation: "slideUp 0.2s ease",
      }}
    >
      {!isUser && (
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 10,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            marginTop: 4,
          }}
        >
          <Bot size={16} color="#fff" />
        </div>
      )}

      <div style={{ maxWidth: "78%", display: "flex", flexDirection: "column", gap: 6 }}>
        {toolCalls && toolCalls.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {toolCalls.map((tc, i) => (
              <ToolBadge key={i} toolName={tc.tool_name} />
            ))}
          </div>
        )}
        <div
          style={{
            padding: "12px 16px",
            borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
            background: isUser
              ? "linear-gradient(135deg, #6366f1, #7c3aed)"
              : "var(--surface-2)",
            border: isUser ? "none" : "1px solid var(--border)",
            color: "var(--text-primary)",
            fontSize: "0.9375rem",
            boxShadow: isUser
              ? "0 4px 15px rgba(99,102,241,0.25)"
              : "0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          {isUser ? (
            <span style={{ whiteSpace: "pre-wrap" }}>{content}</span>
          ) : (
            <MarkdownText text={content} />
          )}
        </div>
      </div>

      {isUser && (
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 10,
            background: "linear-gradient(135deg, #6366f1, #7c3aed)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            marginTop: 4,
          }}
        >
          <User size={16} color="#fff" />
        </div>
      )}
    </div>
  );
}

// ── Thinking indicator ───────────────────────────────────────────────────────
function Thinking() {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 10,
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <Bot size={16} color="#fff" />
      </div>
      <div
        style={{
          padding: "14px 18px",
          borderRadius: "4px 18px 18px 18px",
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          display: "flex",
          gap: 5,
          alignItems: "center",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "#6366f1",
              display: "inline-block",
              animation: `bounce 1.2s ease ${i * 0.2}s infinite`,
              opacity: 0.7,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────
interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  toolCalls?: AssistantChatResponse["tool_calls"];
}

export default function AssistantClient() {
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I'm your **ShopFloor Scheduling Assistant**.\n\nI can help you analyze your production schedules, check machine utilization, find late jobs, review maintenance alerts, and compare algorithm performance.\n\nType a question below or pick a suggestion to get started!",
    },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [prompts, setPrompts] = useState<string[]>([]);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load starter prompts
  useEffect(() => {
    getAssistantPrompts()
      .then(setPrompts)
      .catch(() =>
        setPrompts([
          "What's the makespan of my latest run?",
          "Which machine has the worst utilization?",
          "Show me all late jobs",
          "Are there any active maintenance alerts?",
          "Compare algorithm performance",
        ])
      );
  }, []);

  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({
      behavior: smooth ? "smooth" : "auto",
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinking, scrollToBottom]);

  // Show scroll button
  const handleScroll = () => {
    if (!chatRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatRef.current;
    setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 120);
  };

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || thinking) return;

      const userEntry: ChatEntry = { role: "user", content: trimmed };
      setMessages((prev) => [...prev, userEntry]);
      setInput("");
      setThinking(true);

      const history: AssistantMessage[] = messages
        .slice(-10)
        .map(({ role, content }) => ({ role, content }));
      history.push({ role: "user", content: trimmed });

      try {
        const res = await chatWithAssistant(trimmed, history);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.reply, toolCalls: res.tool_calls },
        ]);
        if (res.suggested_prompts?.length) {
          setPrompts(res.suggested_prompts);
        }
      } catch (err: unknown) {
        const errMsg =
          err instanceof Error ? err.message : "Something went wrong.";
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ Error: ${errMsg}\n\nPlease ensure the backend is running and you're logged in.`,
          },
        ]);
      } finally {
        setThinking(false);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    },
    [messages, thinking]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div
      className="animate-fade-in"
      style={{
        maxWidth: 860,
        margin: "0 auto",
        height: "calc(100vh - var(--topnav-height) - 48px)",
        display: "flex",
        flexDirection: "column",
        gap: 0,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          marginBottom: 20,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 14,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 16px rgba(99,102,241,0.3)",
          }}
        >
          <Sparkles size={22} color="#fff" />
        </div>
        <div>
          <h1 style={{ fontSize: "1.5rem", lineHeight: 1.1 }}>AI Scheduling Assistant</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>
            Ask questions about your schedules, machines, and performance
          </p>
        </div>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 12px",
            borderRadius: 999,
            background: "rgba(16,185,129,0.1)",
            border: "1px solid rgba(16,185,129,0.2)",
            color: "#10b981",
            fontSize: "0.8125rem",
            fontWeight: 600,
          }}
        >
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#10b981" }} />
          Online
        </div>
      </div>

      {/* Chat window */}
      <div
        ref={chatRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 18,
          padding: "20px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg) var(--radius-lg) 0 0",
          position: "relative",
        }}
      >
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} content={m.content} toolCalls={m.toolCalls} />
        ))}
        {thinking && <Thinking />}
        <div ref={bottomRef} />

        {/* Scroll to bottom button */}
        {showScrollBtn && (
          <button
            onClick={() => scrollToBottom()}
            style={{
              position: "sticky",
              bottom: 16,
              left: "50%",
              transform: "translateX(-50%)",
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 2px 10px rgba(0,0,0,0.15)",
              color: "var(--text-secondary)",
              transition: "all 0.15s",
            }}
          >
            <ChevronDown size={16} />
          </button>
        )}
      </div>

      {/* Suggested prompts */}
      {prompts.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 8,
            padding: "10px 16px",
            background: "var(--surface-2)",
            borderLeft: "1px solid var(--border)",
            borderRight: "1px solid var(--border)",
            overflowX: "auto",
            scrollbarWidth: "none",
            flexShrink: 0,
          }}
        >
          {prompts.map((p, i) => (
            <button
              key={i}
              id={`prompt-chip-${i}`}
              onClick={() => sendMessage(p)}
              disabled={thinking}
              style={{
                padding: "5px 12px",
                borderRadius: 999,
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontSize: "0.8125rem",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.15s",
                fontFamily: "inherit",
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLButtonElement).style.borderColor = "#6366f1";
                (e.target as HTMLButtonElement).style.color = "#818cf8";
                (e.target as HTMLButtonElement).style.background = "rgba(99,102,241,0.08)";
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLButtonElement).style.borderColor = "var(--border)";
                (e.target as HTMLButtonElement).style.color = "var(--text-secondary)";
                (e.target as HTMLButtonElement).style.background = "transparent";
              }}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div
        style={{
          display: "flex",
          gap: 10,
          padding: "14px 16px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderTop: "none",
          borderRadius: "0 0 var(--radius-lg) var(--radius-lg)",
          flexShrink: 0,
          alignItems: "flex-end",
        }}
      >
        <textarea
          ref={inputRef}
          id="assistant-input"
          rows={1}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            // Auto-resize
            e.target.style.height = "auto";
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask about schedules, machines, late jobs…"
          disabled={thinking}
          style={{
            flex: 1,
            resize: "none",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            padding: "10px 14px",
            background: "var(--surface-2)",
            color: "var(--text-primary)",
            fontFamily: "inherit",
            fontSize: "0.9375rem",
            lineHeight: 1.5,
            outline: "none",
            transition: "border-color 0.15s",
            minHeight: 44,
          }}
          onFocus={(e) => (e.target.style.borderColor = "#6366f1")}
          onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
        />
        <button
          id="assistant-send-btn"
          className="btn btn-primary"
          onClick={() => sendMessage(input)}
          disabled={thinking || !input.trim()}
          style={{
            width: 44,
            height: 44,
            padding: 0,
            borderRadius: "var(--radius-md)",
            background:
              input.trim() && !thinking
                ? "linear-gradient(135deg, #6366f1, #7c3aed)"
                : "var(--surface-2)",
            borderColor: input.trim() && !thinking ? "transparent" : "var(--border)",
            color:
              input.trim() && !thinking ? "#fff" : "var(--text-muted)",
            transition: "all 0.2s",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Send message (Enter)"
        >
          {thinking ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>

      {/* Bounce animation */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.6; }
          40% { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
