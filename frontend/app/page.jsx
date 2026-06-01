"use client";

import { useEffect, useMemo, useState } from "react";

import AppShell from "../components/AppShell";
import BirthForm from "../components/BirthForm";
import ChatWindow from "../components/ChatWindow";
import ChartSummary from "../components/ChartSummary";

import { chatSse, fetchHistory } from "../lib/api";
import { createMessage, makeId } from "../lib/types";

function makeSessionId() {
  return typeof window !== "undefined" ? (localStorage.getItem("astroagent_session") || "") : "";
}

export default function Page() {
  const [sessionId, setSessionId] = useState("");
  const [birthDetails, setBirthDetails] = useState(null);
  const [messages, setMessages] = useState([]);
  const [toolEvents, setToolEvents] = useState([]);
  const [streamingText, setStreamingText] = useState("");
  const [chart, setChart] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let sid = makeSessionId();
    if (!sid) {
      sid = makeId("sess");
      localStorage.setItem("astroagent_session", sid);
    }
    setSessionId(sid);

    fetchHistory(sid)
      .then((rows) => {
        const msgs = rows
          .filter((r) => r.role === "user" || r.role === "assistant")
          .map((r) => ({
            id: String(r.id),
            role: r.role,
            content: r.content,
            toolCalls: r.tool_calls || undefined,
            timestamp: new Date(r.created_at),
          }));
        setMessages(msgs);
      })
      .catch(() => {
        // history is best-effort
      });
  }, []);

  const canChat = useMemo(() => !!birthDetails && !busy, [birthDetails, busy]);

  function onBirthSubmit(details) {
    setBirthDetails(details);
    // Optional: nudge the agent to begin
    sendMessage("Cast my chart and tell me what stands out.", details);
  }

  async function sendMessage(text, birthOverride) {
    if (!sessionId) return;

    setBusy(true);
    setToolEvents([]);
    setStreamingText("");

    const userMsg = createMessage("user", text);
    setMessages((m) => [...m, userMsg]);

    const assistantId = makeId("asst");

    let assistantAccum = "";

    const detailsToSend = birthOverride || birthDetails;

    await chatSse({
      message: text,
      sessionId,
      birthDetails: detailsToSend,
      callbacks: {
        onToken: (t) => {
          assistantAccum += t;
          setStreamingText(assistantAccum);
        },
        onToolStart: (tool) => {
          setToolEvents((ev) => [...ev, { type: "tool_start", tool }]);
        },
        onToolEnd: (tool) => {
          setToolEvents((ev) => [...ev, { type: "tool_end", tool }]);
        },
        onChart: (c) => {
          setChart(c);
        },
        onError: (err) => {
          setToolEvents((ev) => [...ev, { type: "error", error: err }]);
        },
        onDone: () => {
          // finalize
        },
      },
    });

    if (assistantAccum.trim()) {
      setMessages((m) => [...m, { id: assistantId, role: "assistant", content: assistantAccum, timestamp: new Date() }]);
    }

    setStreamingText("");
    setBusy(false);
  }

  return (
    <AppShell>
      <div className="flex flex-1 flex-col">
        <BirthForm birthDetails={birthDetails} onSubmit={onBirthSubmit} />
        {chart ? <ChartSummary chart={chart} /> : null}
        <div className="flex-1" style={{ minHeight: 0 }}>
          <ChatWindow
            messages={messages}
            streamingText={streamingText}
            toolEvents={toolEvents}
            onSend={sendMessage}
            disabled={!birthDetails || busy}
          />
        </div>
      </div>
    </AppShell>
  );
}
