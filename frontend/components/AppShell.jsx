export default function AppShell({ children }) {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col">
        {/* Decorative rings */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{
              width: 600,
              height: 600,
              border: "1px solid var(--border)",
              opacity: 0.06,
            }}
          />
          <div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{
              width: 900,
              height: 900,
              border: "1px solid var(--border)",
              opacity: 0.06,
            }}
          />
        </div>

        <header className="relative z-10 px-4 pt-6">
          <div
            className="text-[14px] tracking-[0.3em]"
            style={{
              fontFamily: "var(--font-cormorant)",
              color: "var(--accent)",
            }}
          >
            ARADHANA
          </div>
          <div className="mt-4" style={{ borderTop: "1px solid var(--accent-dim)" }} />
        </header>

        <main className="relative z-10 flex flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}
