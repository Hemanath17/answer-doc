import { useEffect, useRef, useState, useCallback } from "react";
import { streamQuery } from "../lib/streamQuery";

/* ── Icons ────────────────────────────────────────────────────────────── */

function IconCopy() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconThumbUp({ filled }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function IconThumbDown({ filled }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    </svg>
  );
}

function IconStop() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}

function IconSend() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

/* ── Source chip ──────────────────────────────────────────────────────── */

function SourceChip({ source }) {
  return (
    <span
      title={source.preview}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 20,
        border: "1px solid var(--border)",
        fontSize: 11,
        color: "var(--text)",
        background: "var(--bg)",
      }}
    >
      Page {source.page}
    </span>
  );
}

/* ── Message action bar ───────────────────────────────────────────────── */

function ActionBar({ message, onCopy, onLike, onDislike }) {
  const iconBtn = (label, onClick, active, children) => (
    <button
      title={label}
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 4,
        padding: "4px 8px",
        borderRadius: 6,
        border: "1px solid var(--border)",
        background: active ? "var(--accent-bg)" : "transparent",
        color: active ? "var(--accent)" : "var(--text)",
        cursor: "pointer",
        fontSize: 12,
        transition: "background 0.12s, color 0.12s",
      }}
    >
      {children}
    </button>
  );

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
      {iconBtn(
        message.copied ? "Copied!" : "Copy",
        () => onCopy(message.id, message.content),
        false,
        <>{message.copied ? <IconCheck /> : <IconCopy />}<span>{message.copied ? "Copied" : "Copy"}</span></>
      )}
      {iconBtn("Helpful", () => onLike(message.id), message.liked === true, <IconThumbUp filled={message.liked === true} />)}
      {iconBtn("Not helpful", () => onDislike(message.id), message.liked === false, <IconThumbDown filled={message.liked === false} />)}
    </div>
  );
}

/* ── Message bubble ───────────────────────────────────────────────────── */

function Message({ message, onCopy, onLike, onDislike }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <div
          style={{
            maxWidth: "70%",
            padding: "10px 14px",
            borderRadius: "18px 18px 4px 18px",
            background: "var(--accent)",
            color: "#fff",
            fontSize: 14,
            lineHeight: 1.55,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 20 }}>
      <div
        style={{
          maxWidth: "80%",
          padding: "14px 16px",
          borderRadius: "4px 18px 18px 18px",
          border: "1px solid var(--border)",
          background: "var(--bg)",
          color: "var(--text-h)",
          fontSize: 14,
          lineHeight: 1.65,
        }}
      >
        {message.error ? (
          <p style={{ color: "#ef4444", whiteSpace: "pre-wrap" }}>{message.content}</p>
        ) : (
          <p style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {message.content}
            {message.streaming && (
              <span
                style={{
                  display: "inline-block",
                  width: 2,
                  height: "1em",
                  marginLeft: 2,
                  verticalAlign: "middle",
                  background: "currentColor",
                  animation: "blink 1s step-end infinite",
                }}
              />
            )}
          </p>
        )}

        {message.hasImage && message.imageUrl && (
          <img
            src={message.imageUrl}
            alt="Answer illustration"
            style={{
              marginTop: 12,
              maxWidth: "100%",
              borderRadius: 8,
              border: "1px solid var(--border)",
            }}
          />
        )}

        {message.sources?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
            {message.sources.map((source, i) => (
              <SourceChip key={i} source={source} />
            ))}
          </div>
        )}

        {!message.streaming && !message.error && (
          <ActionBar
            message={message}
            onCopy={onCopy}
            onLike={onLike}
            onDislike={onDislike}
          />
        )}
      </div>
    </div>
  );
}

/* ── Waiting indicator (before first token) ───────────────────────────── */

function WaitingIndicator() {
  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 16 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "12px 16px",
          borderRadius: "4px 18px 18px 18px",
          border: "1px solid var(--border)",
          background: "var(--bg)",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              display: "block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--accent)",
              animation: `bounce 1.2s ease infinite`,
              animationDelay: `${i * 0.2}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

/* ── Global animation keyframes (injected once) ───────────────────────── */

const STYLE = `
  @keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); }
    40% { transform: translateY(-8px); }
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }
`;

/* ── Main ChatInterface ───────────────────────────────────────────────── */

export default function ChatInterface({ docStatus }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [waitingForFirstToken, setWaitingForFirstToken] = useState(false);
  const bottomRef = useRef(null);
  const assistantIdRef = useRef(null);
  const abortRef = useRef(null);
  const textareaRef = useRef(null);

  const docReady = docStatus.status === "ready";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waitingForFirstToken]);

  /* Update a single message by id */
  const patchMessage = useCallback((id, patch) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  /* ── Send / stream ── */
  async function sendQuestion() {
    const question = input.trim();
    if (!question || loading) return;

    const assistantId = `a-${Date.now()}`;
    assistantIdRef.current = assistantId;

    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: question },
      { id: assistantId, role: "assistant", content: "", streaming: true, liked: null, copied: false },
    ]);
    setInput("");
    setLoading(true);
    setWaitingForFirstToken(true);
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    abortRef.current = new AbortController();

    const appendToken = (token) => {
      setWaitingForFirstToken(false);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: m.content + token } : m
        )
      );
    };

    const finalizeMessage = (payload) => {
      patchMessage(assistantId, {
        streaming: false,
        sources: payload.sources,
        hasImage: payload.has_image,
        imageUrl: payload.image_url,
      });
      setLoading(false);
      setWaitingForFirstToken(false);
    };

    const showError = (msg) => {
      patchMessage(assistantId, { streaming: false, error: true, content: msg });
      setLoading(false);
      setWaitingForFirstToken(false);
    };

    await streamQuery(question, {
      onToken: appendToken,
      onDone: finalizeMessage,
      onError: showError,
      signal: abortRef.current.signal,
    });
  }

  /* ── Stop ── */
  function handleStop() {
    abortRef.current?.abort();
    // finalizeMessage will be called by streamQuery's abort handler
  }

  /* ── Message actions ── */
  const handleCopy = useCallback((id, content) => {
    navigator.clipboard.writeText(content).catch(() => {});
    patchMessage(id, { copied: true });
    setTimeout(() => patchMessage(id, { copied: false }), 2000);
  }, [patchMessage]);

  const handleLike = useCallback((id) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, liked: m.liked === true ? null : true } : m
      )
    );
  }, []);

  const handleDislike = useCallback((id) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, liked: m.liked === false ? null : false } : m
      )
    );
  }, []);

  /* ── Auto-resize textarea ── */
  function handleInputChange(e) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  }

  const placeholder = !docReady
    ? docStatus.status === "processing"
      ? "Processing your PDF…"
      : "Upload a PDF from the sidebar to get started"
    : "Ask a question…";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
        overflow: "hidden",
        background: "var(--bg)",
      }}
    >
      {/* Inject keyframes once */}
      <style>{STYLE}</style>

      {/* Header */}
      <header
        style={{
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          height: 56,
          borderBottom: "1px solid var(--border)",
          background: "var(--bg)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 28,
              height: 28,
              borderRadius: 8,
              background: "var(--accent)",
              color: "#fff",
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            A
          </span>
          <span style={{ fontWeight: 600, fontSize: 15, color: "var(--text-h)", letterSpacing: "-0.01em" }}>
            AnswerDoc
          </span>
        </div>

        {docStatus.filename && (
          <span
            style={{
              fontSize: 12,
              color: "var(--text)",
              padding: "3px 10px",
              borderRadius: 20,
              border: "1px solid var(--border)",
              maxWidth: 240,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {docStatus.filename}
          </span>
        )}
      </header>

      {/* Message list */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          padding: "24px 24px 8px",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              color: "var(--text)",
              textAlign: "center",
              padding: "0 32px",
            }}
          >
            <span style={{ fontSize: 40 }}>📖</span>
            <p style={{ fontSize: 16, fontWeight: 500, color: "var(--text-h)" }}>
              {docReady ? `Chatting about "${docStatus.filename}"` : "No source loaded"}
            </p>
            <p style={{ fontSize: 13, maxWidth: 320 }}>
              {docReady
                ? "Ask anything about your document — page references and images included."
                : "Upload a PDF using the sidebar to start asking questions."}
            </p>
          </div>
        )}

        {messages.map((message, i) => (
          <Message
            key={message.id || i}
            message={message}
            onCopy={handleCopy}
            onLike={handleLike}
            onDislike={handleDislike}
          />
        ))}

        {waitingForFirstToken && <WaitingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div
        style={{
          flexShrink: 0,
          padding: "12px 24px 20px",
          borderTop: "1px solid var(--border)",
          background: "var(--bg)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 8,
            padding: "8px 8px 8px 16px",
            borderRadius: 16,
            border: "1px solid var(--border)",
            background: "var(--bg)",
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
            transition: "border-color 0.15s",
          }}
          onFocusCapture={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
          onBlurCapture={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={loading || !docReady}
            placeholder={placeholder}
            style={{
              flex: 1,
              resize: "none",
              border: "none",
              outline: "none",
              background: "transparent",
              color: "var(--text-h)",
              fontSize: 14,
              lineHeight: 1.5,
              minHeight: 22,
              maxHeight: 160,
              overflowY: "auto",
              fontFamily: "inherit",
              padding: "4px 0",
            }}
          />

          {loading ? (
            <button
              onClick={handleStop}
              title="Stop generating"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 36,
                height: 36,
                borderRadius: 10,
                border: "none",
                background: "#ef4444",
                color: "#fff",
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              <IconStop />
            </button>
          ) : (
            <button
              onClick={sendQuestion}
              disabled={!input.trim() || !docReady}
              title="Send"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 36,
                height: 36,
                borderRadius: 10,
                border: "none",
                background: input.trim() && docReady ? "var(--accent)" : "var(--border)",
                color: input.trim() && docReady ? "#fff" : "var(--text)",
                cursor: input.trim() && docReady ? "pointer" : "default",
                flexShrink: 0,
                transition: "background 0.15s",
              }}
            >
              <IconSend />
            </button>
          )}
        </div>

        <p style={{ fontSize: 11, color: "var(--text)", marginTop: 8, textAlign: "center" }}>
          Answers are based solely on your uploaded document.
        </p>
      </div>
    </div>
  );
}
