import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatInterface from "./components/ChatInterface";

const API_URL = import.meta.env.VITE_API_URL;

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [docStatus, setDocStatus] = useState({ status: "none", filename: null, error: null, chunk_count: 0 });
  const [fileSize, setFileSize] = useState(null);

  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/doc/status`)
      .then((r) => r.json())
      .then((data) => setDocStatus(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (docStatus.status !== "processing") return;
    const id = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/doc/status`);
        const data = await res.json();
        setDocStatus(data);
        if (data.status !== "processing") clearInterval(id);
      } catch {
        // keep polling through transient network blips
      }
    }, 3000);
    return () => clearInterval(id);
  }, [docStatus.status]);

  const handleUpload = useCallback(async (file) => {
    setFileSize(file.size);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API_URL}/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setDocStatus({ status: "error", filename: file.name, error: err.detail || "Upload failed.", chunk_count: 0 });
        return;
      }
      setDocStatus(await res.json());
    } catch {
      setDocStatus({ status: "error", filename: file.name, error: "Could not reach the backend.", chunk_count: 0 });
    }
  }, []);

  const handleIngestUrl = useCallback(async (url) => {
    setFileSize(null);
    setDocStatus({ status: "processing", filename: url, error: null, chunk_count: 0 });
    try {
      const res = await fetch(`${API_URL}/ingest/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setDocStatus({ status: "error", filename: url, error: err.detail || "Failed to fetch URL.", chunk_count: 0 });
        return;
      }
      setDocStatus(await res.json());
    } catch {
      setDocStatus({ status: "error", filename: url, error: "Could not reach the backend.", chunk_count: 0 });
    }
  }, []);

  const handleIngestText = useCallback(async (title, content) => {
    setFileSize(null);
    const name = title || "Pasted Text";
    setDocStatus({ status: "processing", filename: name, error: null, chunk_count: 0 });
    try {
      const res = await fetch(`${API_URL}/ingest/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, content }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setDocStatus({ status: "error", filename: name, error: err.detail || "Failed to ingest text.", chunk_count: 0 });
        return;
      }
      setDocStatus(await res.json());
    } catch {
      setDocStatus({ status: "error", filename: name, error: "Could not reach the backend.", chunk_count: 0 });
    }
  }, []);

  const handleClear = useCallback(async () => {
    try {
      await fetch(`${API_URL}/doc/clear`, { method: "DELETE" });
      setDocStatus({ status: "none", filename: null, error: null, chunk_count: 0 });
      setFileSize(null);
    } catch {
      setDocStatus({ status: "error", filename: null, error: "Could not clear the document.", chunk_count: 0 });
    }
  }, []);

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden", background: "var(--bg)" }}>
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((o) => !o)}
        docStatus={docStatus}
        fileSize={fileSize}
        onUpload={handleUpload}
        onIngestUrl={handleIngestUrl}
        onIngestText={handleIngestText}
        onClear={handleClear}
      />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        <ChatInterface docStatus={docStatus} theme={theme} onToggleTheme={toggleTheme} />
      </div>
    </div>
  );
}
