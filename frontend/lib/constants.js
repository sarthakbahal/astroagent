export const PLANET_SYMBOLS = {
  Sun: "☉",
  Moon: "☽",
  Mercury: "☿",
  Venus: "♀",
  Mars: "♂",
  Jupiter: "♃",
  Saturn: "♄",
  Uranus: "♅",
  Neptune: "♆",
  Pluto: "♇",
};

export const ZODIAC_GLYPHS = {
  Aries: "♈",
  Taurus: "♉",
  Gemini: "♊",
  Cancer: "♋",
  Leo: "♌",
  Virgo: "♍",
  Libra: "♎",
  Scorpio: "♏",
  Sagittarius: "♐",
  Capricorn: "♑",
  Aquarius: "♒",
  Pisces: "♓",
};

export const TOOL_LABELS = {
  compute_birth_chart: "⟳ computing ephemeris positions...",
  geocode_place: "⟳ resolving coordinates...",
  get_daily_transits: "⟳ reading current sky...",
  knowledge_lookup: "⟳ consulting the texts...",
};

export const TOOL_DONE = {
  compute_birth_chart: "✓ ephemeris computed",
  geocode_place: "✓ coordinates resolved",
  get_daily_transits: "✓ sky read",
  knowledge_lookup: "✓ texts consulted",
};

export const PLANET_NAMES = Object.keys(PLANET_SYMBOLS);
export const SIGN_NAMES = Object.keys(ZODIAC_GLYPHS);
