/**
 * This project is plain JavaScript (no TypeScript).
 * We still document shapes using JSDoc for clarity.
 */

/**
 * @typedef {Object} BirthDetails
 * @property {string} date - YYYY-MM-DD
 * @property {string} time - HH:MM
 * @property {string} place
 * @property {number | null | undefined} lat
 * @property {number | null | undefined} lng
 * @property {string} timezone
 */

/**
 * @typedef {Object} Message
 * @property {string} id
 * @property {"user" | "assistant"} role
 * @property {string} content
 * @property {string[] | undefined} toolCalls
 * @property {Date} timestamp
 */

/**
 * @typedef {Object} ChartData
 * @property {Object.<string, {sign: string, degree: number, house: number}>} planets
 * @property {Object.<string, string>} houses
 * @property {{sign: string, degree: number}} ascendant
 * @property {{sign: string, degree: number}} midheaven
 * @property {string=} system
 */

/**
 * @typedef {Object} StreamEvent
 * @property {"tool_start" | "tool_end" | "token" | "chart" | "done" | "error"} type
 * @property {string=} tool
 * @property {string=} content
 * @property {ChartData=} chart
 * @property {string=} error
 */

export function makeId(prefix) {
  const rand = Math.random().toString(16).slice(2);
  return `${prefix}_${Date.now()}_${rand}`;
}

/** @param {any} value */
export function isBirthDetails(value) {
  return (
    value &&
    typeof value === "object" &&
    typeof value.date === "string" &&
    typeof value.time === "string" &&
    typeof value.place === "string" &&
    typeof value.timezone === "string"
  );
}

/**
 * @param {"user" | "assistant"} role
 * @param {string} content
 * @param {string[]=} toolCalls
 * @returns {Message}
 */
export function createMessage(role, content, toolCalls) {
  return {
    id: makeId("msg"),
    role,
    content,
    toolCalls: toolCalls && toolCalls.length ? toolCalls : undefined,
    timestamp: new Date(),
  };
}

export function formatBirthSummary(details) {
  if (!isBirthDetails(details)) return "";
  const date = details.date;
  const time = details.time;
  const place = details.place;
  const niceDate = date;
  return `Born ${niceDate} · ${time} · ${place}`;
}
