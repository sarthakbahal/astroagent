import { PLANET_SYMBOLS, ZODIAC_GLYPHS } from "../lib/constants";

export default function PlanetGlyph({ planet, sign }) {
  const pSym = planet ? PLANET_SYMBOLS[planet] : "";
  const sGlyph = sign ? ZODIAC_GLYPHS[sign] : "";

  return (
    <span className="inline-flex items-center gap-1 font-mono">
      {pSym ? <span style={{ color: "var(--accent)" }}>{pSym}</span> : null}
      <span style={{ fontFamily: "var(--font-inter)" }}>{planet}</span>
      {sGlyph ? (
        <span className="ml-1" style={{ color: "var(--accent-dim)" }}>
          {sGlyph}
        </span>
      ) : null}
    </span>
  );
}
