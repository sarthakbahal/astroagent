// components/NorthIndianChart.jsx

const HOUSE_POSITIONS = {
  // gridRow, gridCol for each house number
  1:  { row: 1, col: 2 },   // top center
  2:  { row: 1, col: 3 },   // top right
  3:  { row: 2, col: 3 },   // right top
  4:  { row: 3, col: 3 },   // right bottom  
  5:  { row: 4, col: 3 },   // bottom right
  6:  { row: 4, col: 2 },   // bottom center
  7:  { row: 4, col: 1 },   // bottom left
  8:  { row: 3, col: 1 },   // left bottom
  9:  { row: 2, col: 1 },   // left top
  10: { row: 1, col: 1 },   // top left
  11: { row: 2, col: 2 },   // inner left (NOT standard — see below)
  12: { row: 3, col: 2 },   // inner right
}

// Zodiac signs in order
const SIGNS = [
  "Ari","Tau","Gem","Can","Leo","Vir",
  "Lib","Sco","Sag","Cap","Aqu","Pis"
]

const SIGN_GLYPHS = {
  "Aries":"♈","Taurus":"♉","Gemini":"♊","Cancer":"♋",
  "Leo":"♌","Virgo":"♍","Libra":"♎","Scorpio":"♏",
  "Sagittarius":"♐","Capricorn":"♑","Aquarius":"♒","Pisces":"♓"
}

export default function NorthIndianChart({ chartData }) {
  if (!chartData) return null

  const ascSign = chartData.ascendant?.sign
  const allSigns = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
  const ascIndex = allSigns.indexOf(ascSign)

  // Build house → sign mapping
  // House 1 = ascendant sign, each subsequent house = next sign
  const houseSign = {}
  for (let h = 1; h <= 12; h++) {
    houseSign[h] = allSigns[(ascIndex + h - 1) % 12]
  }

  // Build sign → planets mapping
  const planetsBySign = {}
  if (chartData.planets) {
    Object.entries(chartData.planets).forEach(([planet, data]) => {
      const sign = data.sign
      if (!planetsBySign[sign]) planetsBySign[sign] = []
      planetsBySign[sign].push(planet)
    })
  }

  // North Indian grid — 4x4 with center 2x2 merged
  // Houses in fixed positions:
  // 12 | 1  | 2
  // 11 |    | 3
  // 10 | 9  | 4  ... etc
  // This is the standard diamond layout

  const cells = [
    { house: 12, style: "col-start-1 row-start-1" },
    { house: 1,  style: "col-start-2 row-start-1" },
    { house: 2,  style: "col-start-3 row-start-1" },
    { house: 11, style: "col-start-1 row-start-2" },
    { house: 3,  style: "col-start-3 row-start-2" },
    { house: 10, style: "col-start-1 row-start-3" },
    { house: 4,  style: "col-start-3 row-start-3" },
    { house: 9,  style: "col-start-1 row-start-4" },
    { house: 8,  style: "col-start-2 row-start-4" },
    { house: 5,  style: "col-start-3 row-start-4" },
    // corner houses
    { house: 7,  style: "col-start-3 row-start-3" }, // adjust
    { house: 6,  style: "col-start-2 row-start-4" },
  ]

  return (
    <div className="w-full max-w-sm mx-auto">
      <p className="text-xs font-mono text-center mb-2"
         style={{ color: "var(--text-muted)", letterSpacing: "0.1em" }}>
        NORTH INDIAN KUNDLI · LAHIRI AYANAMSA
      </p>

      {/* The grid */}
      <div className="relative border"
           style={{ borderColor: "var(--border)", aspectRatio: "1" }}>
        
        {/* SVG diagonal lines for the diamond pattern */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {/* Outer box diagonals */}
          <line x1="0%" y1="0%" x2="33%" y2="33%"
                stroke="var(--border)" strokeWidth="0.5"/>
          <line x1="100%" y1="0%" x2="67%" y2="33%"
                stroke="var(--border)" strokeWidth="0.5"/>
          <line x1="0%" y1="100%" x2="33%" y2="67%"
                stroke="var(--border)" strokeWidth="0.5"/>
          <line x1="100%" y1="100%" x2="67%" y2="67%"
                stroke="var(--border)" strokeWidth="0.5"/>
          {/* Inner diamond */}
          <line x1="33%" y1="33%" x2="67%" y2="33%"
                stroke="var(--border)" strokeWidth="0.5"/>
          <line x1="33%" y1="33%" x2="33%" y2="67%"
                stroke="var(--border)" strokeWidth="0.5"/>
          <line x1="67%" y1="33%" x2="67%" y2="67%"
                stroke="var(--border)" strokeWidth="0.5"/>
          <line x1="33%" y1="67%" x2="67%" y2="67%"
                stroke="var(--border)" strokeWidth="0.5"/>
        </svg>

        {/* 3x4 grid for house cells */}
        <div className="absolute inset-0 grid"
             style={{ gridTemplateColumns: "1fr 1fr 1fr",
                      gridTemplateRows: "1fr 1fr 1fr 1fr" }}>
          
          {/* Render each house */}
          {Object.entries(houseSign).map(([houseNum, sign]) => {
            const planets = planetsBySign[sign] || []
            const isLagna = parseInt(houseNum) === 1
            
            return (
              <HouseCell
                key={houseNum}
                houseNum={houseNum}
                sign={sign}
                planets={planets}
                isLagna={isLagna}
              />
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 justify-center">
        {chartData.planets && Object.entries(chartData.planets)
          .map(([name, data]) => (
            <span key={name} className="text-xs font-mono"
                  style={{ color: "var(--text-muted)" }}>
              <span style={{ color: "var(--accent)" }}>
                {SIGN_GLYPHS[data.sign]}
              </span>
              {" "}{name.slice(0,2)} {data.degree}°
            </span>
          ))
        }
      </div>
    </div>
  )
}

function HouseCell({ houseNum, sign, planets, isLagna }) {
  return (
    <div className="relative flex flex-col items-center justify-center p-1"
         style={{ borderRight: "0.5px solid var(--border)",
                  borderBottom: "0.5px solid var(--border)",
                  minHeight: "60px" }}>
      
      {/* House number — tiny, top left */}
      <span className="absolute top-1 left-1 text-xs font-mono"
            style={{ color: "var(--text-muted)", fontSize: "9px" }}>
        {houseNum}
      </span>

      {/* Sign glyph + name */}
      <span style={{ color: isLagna ? "var(--accent)" : "var(--text-muted)",
                     fontSize: "11px", fontFamily: "monospace" }}>
        {SIGN_GLYPHS[sign]}
      </span>
      <span style={{ color: isLagna ? "var(--accent)" : "var(--text)",
                     fontSize: "9px", letterSpacing: "0.05em" }}>
        {sign.slice(0,3).toUpperCase()}
        {isLagna && " ↑"}
      </span>

      {/* Planets in this house */}
      {planets.length > 0 && (
        <div className="flex flex-wrap justify-center gap-0.5 mt-0.5">
          {planets.map(p => (
            <span key={p}
                  className="text-xs font-mono"
                  style={{ color: "var(--accent)", fontSize: "8px" }}>
              {p.slice(0,2)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}