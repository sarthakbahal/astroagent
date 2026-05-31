import PlanetGlyph from "./PlanetGlyph";
import { PLANET_NAMES } from "../lib/constants";

function splitWithPlanets(text) {
  const words = text.split(/(\b)/g);
  return words.map((w, idx) => {
    const clean = w.replace(/[^A-Za-z]/g, "");
    if (PLANET_NAMES.includes(clean)) {
      return <PlanetGlyph key={`p_${idx}`} planet={clean} />;
    }
    return <span key={`t_${idx}`}>{w}</span>;
  });
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="fade-in-up px-4 py-3 text-right" style={{ color: "var(--text)" }}>
        <div className="inline-flex max-w-[85%] items-start justify-end gap-2">
          <span style={{ color: "var(--accent-dim)" }}>✦</span>
          <div className="text-sm leading-6" style={{ fontFamily: "var(--font-inter)" }}>
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in-up px-4 py-3 text-left" style={{ color: "var(--text)" }}>
      <div className="max-w-[88%]">
        <div
          className="aradhana-label mb-1 text-[10px] tracking-[0.15em]"
          style={{
            fontFamily: "var(--font-cormorant)",
            color: "var(--accent)",
          }}
        >
          ARADHANA
        </div>
        <div className="text-sm leading-7" style={{ fontFamily: "var(--font-inter)" }}>
          {splitWithPlanets(message.content)}
        </div>
      </div>
    </div>
  );
}
