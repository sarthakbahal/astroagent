const SIGNS = [
  "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
  "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

const SIGN_SHORT = {
  "Aries":"Ari","Taurus":"Tau","Gemini":"Gem","Cancer":"Can",
  "Leo":"Leo","Virgo":"Vir","Libra":"Lib","Scorpio":"Sco",
  "Sagittarius":"Sag","Capricorn":"Cap","Aquarius":"Aqu","Pisces":"Pis"
}

const PLANET_SYMBOL = {
  Sun:"☉", Moon:"☽", Mercury:"☿", Venus:"♀", Mars:"♂",
  Jupiter:"♃", Saturn:"♄", Uranus:"♅", Neptune:"♆", Pluto:"♇",
  Rahu:"☊", Ketu:"☋"
}

const PLANET_SHORT = {
  Sun:"Su", Moon:"Mo", Mercury:"Me", Venus:"Ve", Mars:"Ma",
  Jupiter:"Ju", Saturn:"Sa", Uranus:"Ur", Neptune:"Ne", Pluto:"Pl",
  Rahu:"Ra", Ketu:"Ke"
}

export default function NorthIndianKundli({ chartData }) {
  if (!chartData || !chartData.planets) return null

  const ascSign = chartData.ascendant?.sign
  const ascIdx  = SIGNS.indexOf(ascSign)
  if (ascIdx === -1) return null

  // House N → which sign occupies it
  const houseSign = {}
  for (let h = 1; h <= 12; h++) {
    houseSign[h] = SIGNS[(ascIdx + h - 1) % 12]
  }

  // Sign → planets in that sign
  const planetsBySign = {}
  Object.entries(chartData.planets).forEach(([name, data]) => {
    if (!planetsBySign[data.sign]) planetsBySign[data.sign] = []
    planetsBySign[data.sign].push(name)
  })

  // Render one house cell — SVG text lines
  function houseContent(houseNum, cx, cy, isLagna) {
    const sign    = houseSign[houseNum]
    const planets = planetsBySign[sign] || []
    const color   = isLagna ? "#c9a84c" : "var(--color-text-primary)"
    const muted   = "var(--color-text-secondary)"

    return (
      <g key={houseNum}>
        {/* tiny house number */}
        <text
          x={cx} y={cy - 18}
          textAnchor="middle"
          fontSize="8"
          fontFamily="var(--font-mono,monospace)"
          fill={muted}
          opacity="0.5"
        >{houseNum}</text>

        {/* sign name */}
        <text
          x={cx} y={cy - 4}
          textAnchor="middle"
          fontSize="12"
          fontFamily="var(--font-serif,serif)"
          fill={color}
          fontWeight={isLagna ? "600" : "400"}
        >
          {SIGN_SHORT[sign]}{isLagna ? " ↑" : ""}
        </text>

        {/* planets — two per line */}
        {chunk(planets, 2).map((pair, i) => (
          <text
            key={i}
            x={cx} y={cy + 12 + i * 13}
            textAnchor="middle"
            fontSize="10"
            fontFamily="var(--font-mono,monospace)"
            fill="#c9a84c"
          >
            {pair.map(p =>
              `${PLANET_SYMBOL[p] || ""}${PLANET_SHORT[p] || p}`
            ).join("  ")}
          </text>
        ))}
      </g>
    )
  }

  const S  = 360   // outer square size
  const O  = 20    // origin offset
  const T  = S / 3 // third = 120

  // Cell centers [house, cx, cy]
  const cells = [
    [1,  O + T*1.5,  O + T*0.3 ],   // top-center triangle
    [2,  O + T*2.5,  O + T*0.7 ],   // top-right corner
    [3,  O + T*2.8,  O + T*1.5 ],   // right-center triangle
    [4,  O + T*2.5,  O + T*2.3 ],   // bottom-right corner
    [5,  O + T*1.5,  O + T*2.7 ],   // bottom-center triangle
    [6,  O + T*0.5,  O + T*2.3 ],   // bottom-left corner
    [7,  O + T*0.2,  O + T*1.5 ],   // left-center triangle
    [8,  O + T*0.5,  O + T*0.7 ],   // top-left corner
    [9,  O + T*1.0,  O + T*1.4 ],   // inner top-left
    [10, O + T*2.0,  O + T*1.4 ],   // inner top-right
    [11, O + T*2.0,  O + T*1.7 ],   // inner bottom-right
    [12, O + T*1.0,  O + T*1.7 ],   // inner bottom-left
  ]

  const cx = O + S / 2  // 200
  const cy = O + S / 2  // 200

  return (
    <div style={{ width: "100%", maxWidth: "420px", margin: "0 auto" }}>
      <p style={{
        fontFamily: "var(--font-mono,monospace)",
        fontSize: "10px",
        color: "var(--color-text-secondary)",
        letterSpacing: "0.15em",
        textAlign: "center",
        marginBottom: "8px",
        textTransform: "uppercase",
      }}>
        North Indian Kundli · Lahiri Ayanamsa
      </p>

      <svg
        viewBox={`0 0 400 400`}
        width="100%"
        style={{ display: "block" }}
      >
        {/* Outer square */}
        <rect
          x={O} y={O} width={S} height={S}
          fill="none"
          stroke="var(--color-border-secondary)"
          strokeWidth="0.75"
        />

        {/* Vertical thirds */}
        <line x1={O+T}   y1={O} x2={O+T}   y2={O+S} stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T*2} y1={O} x2={O+T*2} y2={O+S} stroke="var(--color-border-secondary)" strokeWidth="0.5"/>

        {/* Horizontal thirds */}
        <line x1={O} y1={O+T}   x2={O+S} y2={O+T}   stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O} y1={O+T*2} x2={O+S} y2={O+T*2} stroke="var(--color-border-secondary)" strokeWidth="0.5"/>

        {/* Inner diamond diagonals */}
        {/* top-left inner → center → top-right inner */}
        <line x1={O+T}   y1={O+T}   x2={cx}      y2={O}       stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T*2} y1={O+T}   x2={cx}      y2={O}       stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T}   y1={O+T*2} x2={cx}      y2={O+S}     stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T*2} y1={O+T*2} x2={cx}      y2={O+S}     stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T}   y1={O+T}   x2={O}       y2={cy}      stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T}   y1={O+T*2} x2={O}       y2={cy}      stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T*2} y1={O+T}   x2={O+S}     y2={cy}      stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T*2} y1={O+T*2} x2={O+S}     y2={cy}      stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        {/* center square diagonals */}
        <line x1={O+T}   y1={O+T}   x2={O+T*2}   y2={O+T*2}   stroke="var(--color-border-secondary)" strokeWidth="0.5"/>
        <line x1={O+T*2} y1={O+T}   x2={O+T}     y2={O+T*2}   stroke="var(--color-border-secondary)" strokeWidth="0.5"/>

        {/* House content */}
        {cells.map(([h, x, y]) =>
          houseContent(h, x, y, h === 1)
        )}
      </svg>
    </div>
  )
}

function chunk(arr, size) {
  const result = []
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size))
  }
  return result
}