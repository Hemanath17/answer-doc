import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatInterface from "./components/ChatInterface";

const API_URL = import.meta.env.VITE_API_URL;

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [docStatus, setDocStatus] = useState({ status: "none", filename: null, error: null });

  // On mount, check if the backend already has a document ready (e.g. after a page refresh).
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
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API_URL}/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setDocStatus({ status: "error", filename: file.name, error: err.detail || "Upload failed." });
        return;
      }
      const data = await res.json();
      setDocStatus(data);
    } catch {
      setDocStatus({ status: "error", filename: file.name, error: "Could not reach the backend." });
    }
  }, []);

  const handleClear = useCallback(async () => {
    try {
      await fetch(`${API_URL}/doc/clear`, { method: "DELETE" });
      setDocStatus({ status: "none", filename: null, error: null });
    } catch {
      setDocStatus({ status: "error", filename: null, error: "Could not clear the document." });
    }
  }, []);

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        overflow: "hidden",
        background: "var(--bg)",
      }}
    >
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((o) => !o)}
        docStatus={docStatus}
        onUpload={handleUpload}
        onClear={handleClear}
      />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        <ChatInterface docStatus={docStatus} />
      </div>
    </div>
  );
}
