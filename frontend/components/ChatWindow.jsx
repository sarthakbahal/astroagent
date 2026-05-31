import { useEffect, useMemo, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import StreamingMessage from "./StreamingMessage";
import ToolActivity from "./ToolActivity";

function CompassRose() {
  return (
    <svg
      width="400"
      height="400"
      viewBox="0 0 400 400"
      className="compass-drift"
      aria-hidden="true"
    >
      <g fill="none" stroke="currentColor" strokeWidth="1">
        <circle cx="200" cy="200" r="160" />
        <circle cx="200" cy="200" r="120" />
        <circle cx="200" cy="200" r="80" />
        <path d="M200 30 L220 180 L200 200 L180 180 Z" />
        <path d="M200 370 L220 220 L200 200 L180 220 Z" />
        <path d="M30 200 L180 180 L200 200 L180 220 Z" />
        <path d="M370 200 L220 180 L200 200 L220 220 Z" />
        <path d="M200 60 L200 340" />
        <path d="M60 200 L340 200" />
      </g>
    </svg>
  );
}

export default function ChatWindow({ messages, streamingText, toolEvents, onSend, disabled }) {
  const [input, setInput] = useState("");
  const endRef = useRef(null);

  const hasMessages = messages && messages.length > 0;

  useEffect(() => {
    if (!endRef.current) return;
    endRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streamingText]);

  const canSend = useMemo(() => input.trim().length > 0 && !disabled, [input, disabled]);

  function submit(e) {
    e.preventDefault();
    if (!canSend) return;
    const text = input.trim();
    setInput("");
    onSend(text);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="relative flex-1 overflow-y-auto">
        <div
          className="pointer-events-none absolute inset-0 flex items-center justify-center"
          style={{ color: "var(--text-muted)", opacity: 0.04 }}
        >
          <CompassRose />
        </div>

        {!hasMessages && !streamingText ? (
          <div className="relative z-10 flex h-full flex-col items-center justify-center px-6 text-center">
            <div className="mb-2" style={{ fontFamily: "var(--font-cormorant)", color: "var(--text-muted)" }}>
              ✦
            </div>
            <div
              className="text-lg"
              style={{ fontFamily: "var(--font-cormorant)", color: "var(--text-muted)" }}
            >
              Share your birth details to begin your reading
            </div>
          </div>
        ) : null}

        <div className="relative z-10">
          {messages.map((m) => (
            <div key={m.id}>
              <MessageBubble message={m} />
              <div className="mx-4" style={{ borderTop: "1px solid var(--border)" }} />
            </div>
          ))}

          {toolEvents && toolEvents.length ? <ToolActivity events={toolEvents} /> : null}

          {streamingText ? (
            <>
              <StreamingMessage content={streamingText} />
              <div className="mx-4" style={{ borderTop: "1px solid var(--border)" }} />
            </>
          ) : null}

          <div ref={endRef} />
        </div>
      </div>

      <form onSubmit={submit} className="px-4 py-4">
        <div className="flex items-end gap-3">
          <input
            className="ledger-input w-full"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the sky..."
            disabled={disabled}
          />
          <button
            type="submit"
            className="text-xl"
            style={{ color: canSend ? "var(--accent)" : "var(--text-muted)" }}
            aria-label="Send"
          >
            →
          </button>
        </div>
      </form>
    </div>
  );
}
