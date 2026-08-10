import { useEffect, useRef, useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL;

function SourceChip({ source }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs"
      style={{ borderColor: "var(--border)", color: "var(--text)" }}
      title={source.preview}
    >
      Page {source.page}
    </span>
  );
}

function Message({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-left text-[15px] leading-relaxed ${
          isUser ? "text-white" : ""
        }`}
        style={
          isUser
            ? { background: "var(--accent)" }
            : {
                background: "var(--bg)",
                border: "1px solid var(--border)",
                color: "var(--text-h)",
              }
        }
      >
        {message.error ? (
          <p className="text-red-500">{message.content}</p>
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}

        {message.hasImage && message.imageUrl && (
          <img
            src={message.imageUrl}
            alt="Answer illustration"
            className="mt-3 max-w-full rounded-lg border"
            style={{ borderColor: "var(--border)" }}
          />
        )}

        {message.sources?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.sources.map((source, i) => (
              <SourceChip key={i} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="flex items-center gap-1 rounded-2xl px-4 py-3"
        style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full"
            style={{
              background: "var(--accent)",
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendQuestion() {
    const question = input.trim();
    if (!question || loading) return;

    if (!API_URL) {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
        {
          role: "assistant",
          error: true,
          content:
            "VITE_API_URL is not set — check frontend/.env and restart the dev server.",
        },
      ]);
      setInput("");
      return;
    }

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const { data } = await axios.post(
        `${API_URL}/query`,
        { question },
        { timeout: 35000 }
      );

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          hasImage: data.has_image,
          imageUrl: data.image_url,
        },
      ]);
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        (err.code === "ECONNABORTED"
          ? "The request took too long to process. Please try again."
          : err.request
          ? `Couldn't reach the API at ${API_URL}. Is the backend running?`
          : err.message);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", error: true, content: detail },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  }

  return (
    <div className="flex h-[100svh] flex-col">
      <header
        className="flex items-center justify-between border-b px-6 py-4"
        style={{ borderColor: "var(--border)" }}
      >
        <h2 className="!m-0">AnswerDoc</h2>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <p style={{ color: "var(--text)" }}>
              Ask a question about your document to get started.
            </p>
          </div>
        )}

        {messages.map((message, i) => (
          <Message key={i} message={message} />
        ))}

        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      <div
        className="border-t px-6 py-4"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-end gap-3">
          <textarea
            className="flex-1 resize-none rounded-xl border px-4 py-3 text-[15px] outline-none"
            style={{
              borderColor: "var(--border)",
              background: "var(--bg)",
              color: "var(--text-h)",
            }}
            rows={1}
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            type="button"
            onClick={sendQuestion}
            disabled={loading || !input.trim()}
            className="rounded-xl px-5 py-3 font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
