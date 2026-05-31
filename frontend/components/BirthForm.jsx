import { useMemo, useState } from "react";
import { formatBirthSummary, isBirthDetails } from "../lib/types";

function validate({ date, time, place }) {
  const errs = {};
  if (!date) errs.date = "Date is required";
  if (!time) errs.time = "Time is required";
  if (!place) errs.place = "Place is required";
  return errs;
}

export default function BirthForm({ birthDetails, onSubmit }) {
  const [date, setDate] = useState(birthDetails?.date || "");
  const [time, setTime] = useState(birthDetails?.time || "");
  const [place, setPlace] = useState(birthDetails?.place || "");
  const [timezone, setTimezone] = useState(birthDetails?.timezone || "UTC");

  const [touched, setTouched] = useState({});
  const errs = useMemo(() => validate({ date, time, place }), [date, time, place]);

  const collapsed = isBirthDetails(birthDetails);

  const summary = useMemo(() => formatBirthSummary(birthDetails), [birthDetails]);

  function handleSubmit(e) {
    e.preventDefault();
    setTouched({ date: true, time: true, place: true });
    if (Object.keys(errs).length) return;
    onSubmit({ date, time, place, lat: null, lng: null, timezone });
  }

  return (
    <div className="px-4 pt-4">
      <div
        className="overflow-hidden transition-[max-height] duration-500 ease-in-out"
        style={{ maxHeight: collapsed ? 0 : 320 }}
      >
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <div>
            <label className="ledger-label">Date of Birth</label>
            <input
              className="ledger-input w-full"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, date: true }))}
              placeholder="YYYY-MM-DD"
            />
            {touched.date && errs.date ? (
              <div className="mt-1 text-xs" style={{ color: "var(--danger)" }}>
                {errs.date}
              </div>
            ) : null}
          </div>

          <div>
            <label className="ledger-label">Time of Birth</label>
            <input
              className="ledger-input w-full"
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, time: true }))}
              placeholder="HH:MM"
            />
            {touched.time && errs.time ? (
              <div className="mt-1 text-xs" style={{ color: "var(--danger)" }}>
                {errs.time}
              </div>
            ) : null}
          </div>

          <div>
            <label className="ledger-label">Place of Birth</label>
            <input
              className="ledger-input w-full"
              type="text"
              value={place}
              onChange={(e) => setPlace(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, place: true }))}
              placeholder="City, Country"
            />
            {touched.place && errs.place ? (
              <div className="mt-1 text-xs" style={{ color: "var(--danger)" }}>
                {errs.place}
              </div>
            ) : null}
          </div>

          <div className="md:col-span-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                Timezone: {timezone}
              </div>
              <button
                type="submit"
                className="border px-4 py-2 text-sm transition-colors"
                style={{
                  borderColor: "var(--accent)",
                  color: "var(--accent)",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--accent)";
                  e.currentTarget.style.color = "var(--bg)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--accent)";
                }}
              >
                Cast Your Chart
              </button>
            </div>
          </div>
        </form>
      </div>

      {collapsed ? (
        <div className="mt-2 font-mono text-xs" style={{ color: "var(--text-muted)" }}>
          {summary}
        </div>
      ) : null}

      <div className="mt-4">
        <hr />
      </div>
    </div>
  );
}
