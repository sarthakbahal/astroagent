import { PLANET_SYMBOLS } from "../lib/constants";

function line(symbol, label, sign, degree) {
  return (
    <div className="flex items-baseline gap-2">
      <span style={{ color: "var(--accent)" }}>{symbol}</span>
      <span style={{ color: "var(--text)" }}>{label}</span>
      {sign ? <span style={{ color: "var(--text)" }}>{sign}</span> : null}
      {typeof degree === "number" ? <span style={{ color: "var(--text-muted)" }}>{degree.toFixed(0)}°</span> : null}
    </div>
  );
}

export default function ChartSummary({ chart }) {
  if (!chart || !chart.planets) return null;

  const p = chart.planets;

  const sun = p.Sun;
  const moon = p.Moon;
  const rising = chart.ascendant;

  return (
    <div className="mx-4 my-3 border px-4 py-3" style={{ borderColor: "var(--border)" }}>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3" style={{ fontFamily: "var(--font-mono)" }}>
        <div className="space-y-1 text-sm">
          {line(PLANET_SYMBOLS.Sun, "Sun", sun?.sign, sun?.degree)}
          {line(PLANET_SYMBOLS.Moon, "Moon", moon?.sign, moon?.degree)}
          <div className="flex items-baseline gap-2">
            <span style={{ color: "var(--accent)" }}>↑</span>
            <span style={{ color: "var(--text)" }}>Rising</span>
            <span style={{ color: "var(--text)" }}>{rising}</span>
          </div>
        </div>

        <div className="space-y-1 text-sm">
          {line(PLANET_SYMBOLS.Mars, "Mars", p.Mars?.sign, p.Mars?.degree)}
          {line(PLANET_SYMBOLS.Venus, "Venus", p.Venus?.sign, p.Venus?.degree)}
          {line(PLANET_SYMBOLS.Mercury, "Mercury", p.Mercury?.sign, p.Mercury?.degree)}
        </div>

        <div className="space-y-1 text-sm">
          {line(PLANET_SYMBOLS.Jupiter, "Jupiter", p.Jupiter?.sign, p.Jupiter?.degree)}
          {line(PLANET_SYMBOLS.Saturn, "Saturn", p.Saturn?.sign, p.Saturn?.degree)}
          {line(PLANET_SYMBOLS.Uranus, "Uranus", p.Uranus?.sign, p.Uranus?.degree)}
          {line(PLANET_SYMBOLS.Neptune, "Neptune", p.Neptune?.sign, p.Neptune?.degree)}
          {line(PLANET_SYMBOLS.Pluto, "Pluto", p.Pluto?.sign, p.Pluto?.degree)}
        </div>
      </div>
    </div>
  );
}
