import { streamChat } from "./stream";

const DEFAULT_BACKEND = "http://localhost:8000";

export function getBackendBase() {
  return process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND;
}

export async function fetchHistory(sessionId) {
  const base = getBackendBase();
  const res = await fetch(`${base}/api/history/${encodeURIComponent(sessionId)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load history");
  return await res.json();
}

export async function clearHistory(sessionId) {
  const base = getBackendBase();
  const res = await fetch(`${base}/api/history/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to clear history");
  return await res.json();
}

export async function chatSse({ message, sessionId, birthDetails, callbacks, signal }) {
  const base = getBackendBase();
  const url = `${base}/api/chat`;
  const payload = {
    message,
    session_id: sessionId,
    birth_details: birthDetails || undefined,
  };

  return await streamChat(url, payload, { ...callbacks, signal });
}
