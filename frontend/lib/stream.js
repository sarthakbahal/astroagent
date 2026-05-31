import { makeId } from "./types";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function parseSseLine(line) {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data:")) return null;
  const jsonPart = trimmed.slice("data:".length).trim();
  if (!jsonPart) return null;
  try {
    return JSON.parse(jsonPart);
  } catch {
    return { type: "error", error: "Failed to parse SSE JSON" };
  }
}

async function readStreamLines(stream, onLine) {
  const reader = stream.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 1);
      onLine(line);
    }
  }

  if (buffer.length) onLine(buffer);
}

/**
 * Connects to FastAPI SSE endpoint by POSTing to /api/chat.
 * Retries once on network drop.
 */
export async function streamChat(
  url,
  payload,
  {
    onToken,
    onToolStart,
    onToolEnd,
    onChart,
    onDone,
    onError,
    signal,
  }
) {
  const attemptId = makeId("stream");

  async function attempt(tryIndex) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status}: ${txt || res.statusText}`);
    }

    if (!res.body) throw new Error("No response body");

    let gotDone = false;

    await readStreamLines(res.body, (line) => {
      const evt = parseSseLine(line);
      if (!evt) return;

      if (evt.type === "token") {
        onToken && onToken(evt.content || "");
      } else if (evt.type === "tool_start") {
        onToolStart && onToolStart(evt.tool);
      } else if (evt.type === "tool_end") {
        onToolEnd && onToolEnd(evt.tool);
      } else if (evt.type === "chart") {
        onChart && onChart(evt.chart);
      } else if (evt.type === "error") {
        onError && onError(evt.error || "Unknown error");
      } else if (evt.type === "done") {
        gotDone = true;
        onDone && onDone();
      }
    });

    if (!gotDone) {
      throw new Error("Stream ended without done");
    }

    return { attemptId, tryIndex };
  }

  try {
    return await attempt(0);
  } catch (err) {
    // Single retry for dropped connections
    if (signal && signal.aborted) {
      onError && onError("Aborted");
      return null;
    }
    try {
      await sleep(600);
      return await attempt(1);
    } catch (err2) {
      onError && onError(err2.message || String(err2));
      return null;
    }
  }
}
