import { PLANET_SYMBOLS } from "../lib/constants";
import NorthIndianKundli from "./NorthIndianKundli";

function line(symbol, label, sign, degree) {
  return (
    <div className="flex items-baseline gap-2">
      <span style={{ color: "var(--accent)" }}>{symbol}</span>
      <span style={{ color: "var(--text)" }}>{label}</span>
      {sign ? <span style={{ color: "var(--text)" }}>{sign}</span> : null}
      {typeof degree === "number" ? (
        <span style={{ color: "var(--text-muted)" }}>{degree.toFixed(0)}°</span>
      ) : null}
    </div>
  );
}

export default function ChartSummary({ chart }) {
  if (!chart || !chart.planets) return null;

  const p      = chart.planets;
  const rising = chart.ascendant;

  return (
    <div
      className="mx-4 my-3 border px-4 py-3"
      style={{ borderColor: "var(--border)" }}
    >
      {/* system label */}
      {chart.system ? (
        <div
          className="mb-2 text-xs"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {chart.system.replace("_", " ")}
        </div>
      ) : null}

      {/* ── planet positions grid (unchanged) ── */}
      <div
        className="grid grid-cols-1 gap-3 md:grid-cols-3"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        <div className="space-y-1 text-sm">
          {line(PLANET_SYMBOLS.Sun,  "Sun",  p.Sun?.sign,  p.Sun?.degree)}
          {line(PLANET_SYMBOLS.Moon, "Moon", p.Moon?.sign, p.Moon?.degree)}
          <div className="flex items-baseline gap-2">
            <span style={{ color: "var(--accent)" }}>↑</span>
            <span style={{ color: "var(--text)" }}>Rising</span>
            <span style={{ color: "var(--text)" }}>{rising?.sign || ""}</span>
            {typeof rising?.degree === "number" ? (
              <span style={{ color: "var(--text-muted)" }}>
                {rising.degree.toFixed(0)}°
              </span>
            ) : null}
          </div>
        </div>

        <div className="space-y-1 text-sm">
          {line(PLANET_SYMBOLS.Mars,    "Mars",    p.Mars?.sign,    p.Mars?.degree)}
          {line(PLANET_SYMBOLS.Venus,   "Venus",   p.Venus?.sign,   p.Venus?.degree)}
          {line(PLANET_SYMBOLS.Mercury, "Mercury", p.Mercury?.sign, p.Mercury?.degree)}
        </div>

        <div className="space-y-1 text-sm">
          {line(PLANET_SYMBOLS.Jupiter, "Jupiter", p.Jupiter?.sign, p.Jupiter?.degree)}
          {line(PLANET_SYMBOLS.Saturn,  "Saturn",  p.Saturn?.sign,  p.Saturn?.degree)}
          {line(PLANET_SYMBOLS.Uranus,  "Uranus",  p.Uranus?.sign,  p.Uranus?.degree)}
          {line(PLANET_SYMBOLS.Neptune, "Neptune", p.Neptune?.sign, p.Neptune?.degree)}
          {line(PLANET_SYMBOLS.Pluto,   "Pluto",   p.Pluto?.sign,   p.Pluto?.degree)}
          {line(PLANET_SYMBOLS.Rahu,    "Rahu",    p.Rahu?.sign,    p.Rahu?.degree)}
          {line(PLANET_SYMBOLS.Ketu,    "Ketu",    p.Ketu?.sign,    p.Ketu?.degree)}
        </div>
      </div>

      {/* ── divider ── */}
      <div
        className="my-4"
        style={{ borderTop: "1px solid var(--border)" }}
      />

      {/* ── North Indian Kundli ── */}
      <NorthIndianKundli chartData={chart} />
    </div>
  );
}