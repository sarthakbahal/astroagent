import { useEffect, useRef } from "react";

export default function StreamingMessage({ content }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [content]);

  return (
    <div ref={ref} className="px-4 py-3 text-left" style={{ color: "var(--text)" }}>
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
          {content}
        </div>
      </div>
    </div>
  );
}
