import { useRef, useState } from "react";

function IconChevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function IconChevronRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function IconUploadArrow() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function IconLink() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function IconYoutube() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.59 6.69a4.83 4.83 0 0 0-3.77-3.37C14.1 3 12 3 12 3s-2.1 0-3.82.32a4.83 4.83 0 0 0-3.77 3.37A50.59 50.59 0 0 0 4 12a50.59 50.59 0 0 0 .41 5.31 4.83 4.83 0 0 0 3.77 3.37C9.9 21 12 21 12 21s2.1 0 3.82-.32a4.83 4.83 0 0 0 3.77-3.37A50.59 50.59 0 0 0 20 12a50.59 50.59 0 0 0-.41-5.31zM10 15V9l5 3-5 3z" />
    </svg>
  );
}

function IconPaste() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
    </svg>
  );
}

function IconUploadBig() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function IconFile() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function formatFileSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function FileCard({ docStatus, fileSize, onClear }) {
  const { status, filename, error, chunk_count } = docStatus;

  const statusColor =
    status === "ready" ? "#22c55e"
    : status === "error" ? "#ef4444"
    : "var(--accent)";

  const sizeLine = [
    fileSize ? formatFileSize(fileSize) : null,
    chunk_count ? `${chunk_count} chunk${chunk_count !== 1 ? "s" : ""} processed` : null,
  ].filter(Boolean).join(" · ");

  return (
    <div style={{ borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg)", overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 12px 8px" }}>
        <span style={{ color: statusColor, flexShrink: 0, marginTop: 1 }}>
          {status === "processing" ? <Spinner /> : <IconFile />}
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-h)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {filename}
          </p>
          {sizeLine && (
            <p style={{ fontSize: 11, color: "var(--accent)", marginTop: 2 }}>{sizeLine}</p>
          )}
        </div>
        {status !== "processing" && (
          <button
            onClick={onClear}
            title="Remove and clear database"
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0, width: 24, height: 24, borderRadius: 6,
              border: "1px solid var(--border)", background: "transparent",
              color: "var(--text)", cursor: "pointer",
              transition: "color 0.15s, border-color 0.15s, background 0.15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#ef4444";
              e.currentTarget.style.borderColor = "#ef4444";
              e.currentTarget.style.background = "rgba(239,68,68,0.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text)";
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            <IconX />
          </button>
        )}
      </div>
      <div style={{ padding: "6px 12px 10px" }}>
        <p style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.5 }}>
          {status === "processing"
            ? "Processing your source, this may take a moment…"
            : status === "ready"
            ? `Processed successfully. Split into ${chunk_count} chunk${chunk_count !== 1 ? "s" : ""} for optimal AI retrieval.`
            : error || "An error occurred during processing."}
        </p>
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg)",
  color: "var(--text-h)",
  fontSize: 13,
  outline: "none",
  fontFamily: "inherit",
};

const submitBtnStyle = {
  width: "100%",
  padding: "8px 0",
  borderRadius: 8,
  border: "none",
  background: "var(--accent)",
  color: "#fff",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
  transition: "opacity 0.15s",
};

function UploadForm({ onUpload }) {
  const fileRef = useRef(null);

  const handleFile = (file) => {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "txt", "csv"].includes(ext)) {
      alert("Please upload a PDF, TXT, or CSV file.");
      return;
    }
    onUpload(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => fileRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && fileRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: 10, padding: "28px 16px", borderRadius: 12,
        border: "2px dashed var(--border)", cursor: "pointer",
        transition: "border-color 0.15s", textAlign: "center",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
    >
      <input ref={fileRef} type="file" accept=".pdf,.txt,.csv" style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])} />
      <span style={{ color: "var(--text)" }}><IconUploadBig /></span>
      <div>
        <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-h)" }}>Upload sources</p>
        <p style={{ fontSize: 11, color: "var(--text)", marginTop: 4 }}>Drag &amp; drop or choose file</p>
        <p style={{ fontSize: 10, color: "var(--text)", marginTop: 4, opacity: 0.7 }}>Supported: .pdf · .txt · .csv</p>
      </div>
    </div>
  );
}

function LinkForm({ onSubmit }) {
  const [url, setUrl] = useState("");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <p style={{ fontSize: 12, color: "var(--text)" }}>Paste a webpage URL to extract its content.</p>
      <input
        style={inputStyle}
        type="url"
        placeholder="https://example.com/article"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && url.trim() && onSubmit(url.trim())}
      />
      <button
        style={{ ...submitBtnStyle, opacity: url.trim() ? 1 : 0.5, cursor: url.trim() ? "pointer" : "default" }}
        disabled={!url.trim()}
        onClick={() => url.trim() && onSubmit(url.trim())}
      >
        Add link
      </button>
    </div>
  );
}

function YoutubeForm({ onSubmit }) {
  const [url, setUrl] = useState("");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <p style={{ fontSize: 12, color: "var(--text)" }}>Paste a YouTube video URL to ingest its transcript.</p>
      <input
        style={inputStyle}
        type="url"
        placeholder="https://youtube.com/watch?v=..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && url.trim() && onSubmit(url.trim())}
      />
      <button
        style={{ ...submitBtnStyle, opacity: url.trim() ? 1 : 0.5, cursor: url.trim() ? "pointer" : "default" }}
        disabled={!url.trim()}
        onClick={() => url.trim() && onSubmit(url.trim())}
      >
        Add video
      </button>
    </div>
  );
}

function PasteForm({ onSubmit }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <p style={{ fontSize: 12, color: "var(--text)" }}>Paste any text content directly.</p>
      <input
        style={inputStyle}
        type="text"
        placeholder="Title (optional)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        style={{ ...inputStyle, resize: "vertical", minHeight: 90, lineHeight: 1.5 }}
        placeholder="Paste your text here…"
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <button
        style={{ ...submitBtnStyle, opacity: content.trim() ? 1 : 0.5, cursor: content.trim() ? "pointer" : "default" }}
        disabled={!content.trim()}
        onClick={() => content.trim() && onSubmit(title.trim(), content.trim())}
      >
        Add text
      </button>
    </div>
  );
}

const MODES = [
  { id: "upload",  label: "Upload",  Icon: IconUploadArrow },
  { id: "link",    label: "Link",    Icon: IconLink },
  { id: "youtube", label: "YouTube", Icon: IconYoutube },
  { id: "paste",   label: "Paste",   Icon: IconPaste },
];

function SourceInputPanel({ mode, setMode, onUpload, onIngestUrl, onIngestYoutube, onIngestText }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Mode content */}
      {mode === "upload"  && <UploadForm  onUpload={onUpload} />}
      {mode === "link"    && <LinkForm    onSubmit={onIngestUrl} />}
      {mode === "youtube" && <YoutubeForm onSubmit={onIngestYoutube} />}
      {mode === "paste"   && <PasteForm   onSubmit={onIngestText} />}

      {/* Tab switcher */}
      <div style={{ display: "flex", gap: 4, borderTop: "1px solid var(--border)", paddingTop: 10 }}>
        {MODES.map(({ id, label, Icon }) => {
          const active = mode === id;
          return (
            <button
              key={id}
              onClick={() => setMode(id)}
              title={label}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 3,
                padding: "6px 2px",
                borderRadius: 8,
                border: "1px solid",
                borderColor: active ? "var(--accent-border)" : "var(--border)",
                background: active ? "var(--accent-bg)" : "transparent",
                color: active ? "var(--accent)" : "var(--text)",
                cursor: "pointer",
                fontSize: 10,
                fontWeight: active ? 600 : 400,
                transition: "all 0.12s",
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.borderColor = "var(--accent-border)"; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.borderColor = "var(--border)"; }}
            >
              <Icon />
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function Sidebar({ open, onToggle, docStatus, fileSize, onUpload, onIngestUrl, onIngestYoutube, onIngestText, onClear }) {
  const hasDoc = docStatus.status !== "none";
  const [mode, setMode] = useState("upload");

  return (
    <aside
      style={{
        width: open ? "272px" : "52px",
        flexShrink: 0,
        transition: "width 0.2s ease",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        background: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border)",
        height: "100%",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: open ? "space-between" : "center",
          padding: open ? "16px 16px 12px" : "16px 0",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
          gap: 8,
        }}
      >
        {open && (
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-h)", letterSpacing: "-0.01em" }}>
              Add sources
            </p>
            <p style={{ fontSize: 11, color: "var(--text)", marginTop: 2, lineHeight: 1.4 }}>
              Sources let the AI base its responses on your documents.
            </p>
          </div>
        )}
        <button
          onClick={onToggle}
          title={open ? "Collapse sidebar" : "Expand sidebar"}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 28, height: 28, borderRadius: 6,
            border: "1px solid var(--border)", background: "var(--bg)",
            color: "var(--text)", cursor: "pointer", flexShrink: 0,
          }}
        >
          {open ? <IconChevronLeft /> : <IconChevronRight />}
        </button>
      </div>

      {/* Body */}
      {open && (
        <div
          style={{
            flex: 1, overflowY: "auto", padding: "16px",
            display: "flex", flexDirection: "column", gap: 12,
          }}
        >
          {hasDoc && (
            <>
              <FileCard docStatus={docStatus} fileSize={fileSize} onClear={onClear} />
              {docStatus.status !== "processing" && (
                <>
                  <p style={{ fontSize: 11, color: "var(--text)", marginBottom: -4 }}>Replace source</p>
                  <SourceInputPanel
                    mode={mode} setMode={setMode}
                    onUpload={onUpload}
                    onIngestUrl={onIngestUrl}
                    onIngestYoutube={onIngestYoutube}
                    onIngestText={onIngestText}
                  />
                </>
              )}
            </>
          )}

          {!hasDoc && (
            <>
              <p style={{ fontSize: 12, color: "var(--text)" }}>
                Upload a document or add a source to start asking questions.
              </p>
              <SourceInputPanel
                mode={mode} setMode={setMode}
                onUpload={onUpload}
                onIngestUrl={onIngestUrl}
                onIngestYoutube={onIngestYoutube}
                onIngestText={onIngestText}
              />
            </>
          )}
        </div>
      )}

      {/* Source count footer */}
      {open && (
        <div
          style={{
            flexShrink: 0, padding: "10px 16px", borderTop: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}
        >
          <p style={{ fontSize: 11, color: "var(--text)" }}>
            {hasDoc ? "1 / 1 source" : "0 / 1 source"}
          </p>
          {hasDoc && docStatus.status !== "processing" && (
            <button
              onClick={onClear}
              style={{ fontSize: 11, color: "#ef4444", background: "none", border: "none", cursor: "pointer", padding: 0, opacity: 0.8 }}
              onMouseEnter={(e) => { e.currentTarget.style.opacity = "1"; }}
              onMouseLeave={(e) => { e.currentTarget.style.opacity = "0.8"; }}
            >
              Clear All
            </button>
          )}
        </div>
      )}

      {/* Collapsed icon */}
      {!open && hasDoc && (
        <div
          style={{
            display: "flex", justifyContent: "center", paddingTop: 12,
            color: docStatus.status === "ready" ? "#22c55e"
              : docStatus.status === "error" ? "#ef4444"
              : "var(--accent)",
          }}
          title={docStatus.filename}
        >
          <IconFile />
        </div>
      )}
    </aside>
  );
}
