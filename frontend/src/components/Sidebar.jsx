import { useRef } from "react";

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

function IconFile() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconAlertCircle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function IconBook() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      style={{ animation: "spin 1s linear infinite" }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function FileCard({ docStatus, onClear }) {
  const { status, filename, error } = docStatus;

  const iconColor =
    status === "ready" ? "#22c55e"
    : status === "error" ? "#ef4444"
    : "var(--accent)";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "10px",
        padding: "12px",
        borderRadius: "10px",
        border: "1px solid var(--border)",
        background: "var(--bg)",
      }}
    >
      <span style={{ color: iconColor, flexShrink: 0, marginTop: 2 }}>
        {status === "processing" ? <Spinner /> : status === "ready" ? <IconCheck /> : <IconAlertCircle />}
      </span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <p
          style={{
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--text-h)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {filename}
        </p>
        <p style={{ fontSize: "11px", color: "var(--text)", marginTop: 2 }}>
          {status === "processing" ? "Processing…" : status === "ready" ? "Ready" : error || "Error"}
        </p>
      </div>

      {status !== "processing" && (
        <button
          onClick={onClear}
          title="Remove document and clear database"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            width: 26,
            height: 26,
            borderRadius: 6,
            border: "1px solid var(--border)",
            background: "transparent",
            color: "var(--text)",
            cursor: "pointer",
            marginTop: 1,
            transition: "color 0.15s, border-color 0.15s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "#ef4444";
            e.currentTarget.style.borderColor = "#ef4444";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "var(--text)";
            e.currentTarget.style.borderColor = "var(--border)";
          }}
        >
          <IconTrash />
        </button>
      )}
    </div>
  );
}

function UploadZone({ onUpload }) {
  const fileRef = useRef(null);

  const handleFile = (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please upload a PDF file.");
      return;
    }
    onUpload(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    handleFile(file);
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
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "10px",
        padding: "24px 16px",
        borderRadius: "12px",
        border: "2px dashed var(--border)",
        cursor: "pointer",
        transition: "border-color 0.15s, background 0.15s",
        textAlign: "center",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
    >
      <input
        ref={fileRef}
        type="file"
        accept=".pdf"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <span style={{ color: "var(--text)" }}><IconUpload /></span>
      <div>
        <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-h)" }}>
          Upload PDF
        </p>
        <p style={{ fontSize: "11px", color: "var(--text)", marginTop: 4 }}>
          Click or drag &amp; drop · PDF only · 1 file
        </p>
      </div>
    </div>
  );
}

export default function Sidebar({ open, onToggle, docStatus, onUpload, onClear }) {
  const hasDoc = docStatus.status !== "none";

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
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-h)" }}>
            <IconBook />
            <span style={{ fontSize: "14px", fontWeight: 600, letterSpacing: "-0.01em" }}>
              Sources
            </span>
          </div>
        )}
        <button
          onClick={onToggle}
          title={open ? "Collapse sidebar" : "Expand sidebar"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            borderRadius: 6,
            border: "1px solid var(--border)",
            background: "var(--bg)",
            color: "var(--text)",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          {open ? <IconChevronLeft /> : <IconChevronRight />}
        </button>
      </div>

      {open && (
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          {hasDoc ? (
            <>
              <FileCard docStatus={docStatus} onClear={onClear} />
              {docStatus.status !== "processing" && (
                <div style={{ marginTop: 4 }}>
                  <p style={{ fontSize: "11px", color: "var(--text)", marginBottom: 8 }}>
                    Replace source
                  </p>
                  <UploadZone onUpload={onUpload} />
                </div>
              )}
            </>
          ) : (
            <>
              <p style={{ fontSize: "12px", color: "var(--text)" }}>
                Upload a PDF to start asking questions about it.
              </p>
              <UploadZone onUpload={onUpload} />
            </>
          )}
        </div>
      )}

      {!open && hasDoc && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            paddingTop: 12,
            color: docStatus.status === "ready" ? "#22c55e" : docStatus.status === "error" ? "#ef4444" : "var(--accent)",
          }}
          title={docStatus.filename}
        >
          <IconFile />
        </div>
      )}
    </aside>
  );
}
