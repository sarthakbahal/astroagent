import { useEffect, useMemo, useState } from "react";
import { TOOL_DONE, TOOL_LABELS } from "../lib/constants";

export default function ToolActivity({ events }) {
  const [completed, setCompleted] = useState({});
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const next = {};
    for (const e of events) {
      if (e.type === "tool_end" && e.tool) next[e.tool] = Date.now();
    }
    setCompleted(next);
  }, [events]);

  useEffect(() => {
    const hasDone = Object.keys(completed).length > 0;
    if (!hasDone) return;
    const id = setInterval(() => setTick((t) => t + 1), 500);
    return () => clearInterval(id);
  }, [completed]);

  const lines = useMemo(() => {
    const active = new Set();
    let lastError = null;
    for (const e of events) {
      if (e.type === "tool_start" && e.tool) active.add(e.tool);
      if (e.type === "tool_end" && e.tool) active.delete(e.tool);
      if (e.type === "error") lastError = e.error || "Unknown error";
    }

    const out = [];
    if (lastError) {
      out.push({ tool: "__error__", status: "error", error: String(lastError) });
    }
    // Show recently completed first, then active
    for (const tool of Object.keys(completed)) {
      out.push({ tool, status: "done" });
    }
    for (const tool of active) {
      out.push({ tool, status: "active" });
    }
    return out;
  }, [events, completed, tick]);

  if (!lines.length) return null;

  return (
    <div className="px-4 py-2 text-xs" style={{ color: "var(--text-muted)" }}>
      {lines.slice(0, 4).map((l) => {
        const label =
          l.status === "error"
            ? `! ${l.error}`
            : l.status === "done"
            ? TOOL_DONE[l.tool] || `✓ ${l.tool}`
            : TOOL_LABELS[l.tool] || `⟳ ${l.tool}...`;
        const doneAt = completed[l.tool];
        const shouldFade = l.status === "done" && doneAt && Date.now() - doneAt > 3000;
        return (
          <div
            key={`${l.tool}_${l.status}`}
            className={`font-mono ${shouldFade ? "tool-complete" : ""}`}
            aria-live="polite"
          >
            {label}
          </div>
        );
      })}
    </div>
  );
}
