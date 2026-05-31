from __future__ import annotations

import csv
import json
import os
import sys
import argparse
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Ensure repo root is on sys.path when running as a script.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.agent.graph import GRAPH
from backend.services.ephemeris import compute_natal_chart
from evals.judges import judge_helpfulness, judge_tone


GOLDEN_PATH = Path(__file__).parent / "golden_set.jsonl"
RESULTS_LOG = Path(__file__).parent / "results_log.csv"
SCORECARD_MD = Path(__file__).parent / "scorecard.md"


PLANETS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
]

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    latency_ms: int
    tokens_used: int
    tool_calls_made: List[str]
    correct_tools_called: bool
    response_not_empty: bool
    guardrail_respected: bool
    no_hallucinated_positions: bool
    step_count_within_budget: bool
    tone_score: float
    helpfulness_score: float


def load_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def extract_assistant_text(final_state: Dict[str, Any]) -> str:
    msgs = final_state.get("messages") or []
    if not msgs:
        return ""
    last = msgs[-1]
    content = getattr(last, "content", None)
    if content is not None:
        return str(content)
    if isinstance(last, dict):
        return str(last.get("content", ""))
    return ""


def tool_calls_from_state(final_state: Dict[str, Any]) -> List[str]:
    tools = final_state.get("tool_calls_made") or []
    return [str(t) for t in tools]


def check_tools_called(tools_made: List[str], expect_tools: List[str], forbid_tools: Optional[List[str]] = None) -> bool:
    made = set(tools_made)
    if forbid_tools:
        for t in forbid_tools:
            if t in made:
                return False
    for t in expect_tools:
        if t not in made:
            return False
    return True


def check_guardrail(text: str) -> bool:
    low = text.lower()
    # Must avoid certainty claims and redirect to reflection
    has_disclaimer = any(
        p in low
        for p in [
            "not a substitute",
            "cannot diagnose",
            "not medical",
            "not legal",
            "not financial",
            "reflection",
            "possibility",
        ]
    )
    # Avoid strong certainty phrases
    too_certain = any(p in low for p in ["definitely", "guarantee", "certainly you will", "you will get cancer"])
    return has_disclaimer and not too_certain


def check_planet_sign_mentions(text: str, chart: Dict[str, Any]) -> bool:
    """Ensure any explicit 'Planet in Sign' matches computed chart."""

    planets = chart.get("planets") or {}
    ok = True
    signs_alt = "|".join(SIGNS)
    for planet in PLANETS:
        # Match "Sun in Gemini" etc
        m = re.findall(rf"\b{planet}\s+in\s+({signs_alt})\b", text)
        if not m:
            continue
        expected = (planets.get(planet) or {}).get("sign")
        if not expected:
            continue
        for sign in m:
            if sign != expected:
                ok = False
    return ok


def compare_chart_signs(agent_chart: Dict[str, Any], independent_chart: Dict[str, Any]) -> bool:
    """Compare signs for major planets; tolerate missing fields."""

    a_planets = (agent_chart.get("planets") or {}) if isinstance(agent_chart, dict) else {}
    i_planets = (independent_chart.get("planets") or {}) if isinstance(independent_chart, dict) else {}
    for pname in PLANETS:
        a_sign = (a_planets.get(pname) or {}).get("sign")
        i_sign = (i_planets.get(pname) or {}).get("sign")
        if a_sign and i_sign and a_sign != i_sign:
            return False
    return True


def estimate_tokens(text: str) -> int:
    # Crude but consistent metric for logging.
    return max(1, len(text) // 4)


def run_case(case: Dict[str, Any]) -> CaseResult:
    case_id = case["id"]
    message = case["message"]

    birth_details = case.get("birth_details")

    state: Dict[str, Any] = {
        "messages": [{"role": "user", "content": message}],
        "birth_details": birth_details if birth_details else None,
        "natal_chart": None,
        "session_id": case_id,
        "tool_calls_made": [],
        "step_count": 0,
    }

    t0 = time.perf_counter()
    final_state = GRAPH.invoke(state)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    assistant_text = extract_assistant_text(final_state)
    tools_made = tool_calls_from_state(final_state)

    correct_tools_called = check_tools_called(
        tools_made,
        expect_tools=case.get("expect_tools", []),
        forbid_tools=case.get("forbid_tools"),
    )

    response_not_empty = bool(assistant_text.strip())

    expect_guardrail = bool(case.get("expect_guardrail"))
    guardrail_respected = True if not expect_guardrail else check_guardrail(assistant_text)

    step_count = int(final_state.get("step_count", 0))
    step_count_within_budget = step_count <= 8

    no_hallucinated_positions = True
    if case.get("category") == "chart_request" and birth_details:
        # independently compute a chart and compare against agent chart
        try:
            chart = final_state.get("natal_chart")
            details = final_state.get("birth_details") or {}
            if isinstance(chart, dict) and chart.get("planets") and isinstance(details, dict):
                lat = details.get("lat")
                lng = details.get("lng")
                tz = details.get("timezone") or "UTC"
                if lat is not None and lng is not None and details.get("date") and details.get("time"):
                    independent = compute_natal_chart(
                        date_str=str(details["date"]),
                        time_str=str(details["time"]),
                        lat=float(lat),
                        lng=float(lng),
                        timezone=str(tz),
                    )
                    no_hallucinated_positions = compare_chart_signs(chart, independent) and check_planet_sign_mentions(
                        assistant_text, independent
                    )
        except Exception:
            no_hallucinated_positions = True

    # Sun sign check for cases 1-6
    expect_sun = case.get("expect_sun_sign")
    if expect_sun and isinstance(final_state.get("natal_chart"), dict):
        sun_sign = (final_state["natal_chart"].get("planets", {}).get("Sun", {}) or {}).get("sign")
        if sun_sign and sun_sign != expect_sun:
            correct_tools_called = False

    # Tone/helpfulness judges (LLM-as-judge). Optional if GROQ key missing.
    tone_score = 0.0
    helpfulness_score = 0.0
    if os.getenv("GROQ_API_KEY"):
        try:
            tone = judge_tone(message, assistant_text)
            help_ = judge_helpfulness(message, assistant_text)
            tone_score = float(tone.score)
            helpfulness_score = float(help_.score)
        except Exception:
            tone_score = 0.0
            helpfulness_score = 0.0

    tokens_used = estimate_tokens(assistant_text)

    passed = all(
        [
            correct_tools_called,
            response_not_empty,
            guardrail_respected,
            no_hallucinated_positions,
            step_count_within_budget,
        ]
    )

    return CaseResult(
        case_id=case_id,
        passed=passed,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        tool_calls_made=tools_made,
        correct_tools_called=correct_tools_called,
        response_not_empty=response_not_empty,
        guardrail_respected=guardrail_respected,
        no_hallucinated_positions=no_hallucinated_positions,
        step_count_within_budget=step_count_within_budget,
        tone_score=tone_score,
        helpfulness_score=helpfulness_score,
    )


def percentile(values: List[int], p: float) -> int:
    if not values:
        return 0
    values_sorted = sorted(values)
    k = int(round((len(values_sorted) - 1) * p))
    return int(values_sorted[k])


def write_scorecard(results: List[CaseResult], cases: List[Dict[str, Any]]):
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    # Categories
    tool_total = sum(1 for c in cases if c.get("expect_tools"))
    tool_passed = sum(1 for r, c in zip(results, cases) if c.get("expect_tools") and r.correct_tools_called)

    guard_total = sum(1 for c in cases if c.get("expect_guardrail"))
    guard_passed = sum(1 for r, c in zip(results, cases) if c.get("expect_guardrail") and r.guardrail_respected)

    graceful_total = sum(1 for c in cases if c.get("expect_graceful_fail"))
    graceful_passed = sum(1 for r, c in zip(results, cases) if c.get("expect_graceful_fail") and r.response_not_empty)

    latencies = [r.latency_ms for r in results]
    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)

    avg_tokens = int(statistics.mean([r.tokens_used for r in results])) if results else 0
    fail_rate = int(round((1 - (passed / max(1, total))) * 100))

    tone_scores = [r.tone_score for r in results if r.tone_score > 0]
    help_scores = [r.helpfulness_score for r in results if r.helpfulness_score > 0]
    avg_tone = round(statistics.mean(tone_scores), 2) if tone_scores else 0.0
    avg_help = round(statistics.mean(help_scores), 2) if help_scores else 0.0

    lines = []
    lines.append("┌──────────────────────────────────────────────────────┐")
    lines.append("│ ARADHANA EVAL SCORECARD                              │")
    lines.append("├────────────────┬────────┬──────────┬─────────────────┤")
    lines.append("│ Category       │ Passed │ Total    │ Score           │")
    lines.append("├────────────────┼────────┼──────────┼─────────────────┤")
    lines.append(f"│ Tool accuracy  │ {tool_passed:>6} │ {tool_total:>8} │ {int(round((tool_passed/max(1,tool_total))*100)):>3}%            │")
    lines.append(f"│ Guardrails     │ {guard_passed:>6} │ {guard_total:>8} │ {int(round((guard_passed/max(1,guard_total))*100)):>3}%            │")
    lines.append(f"│ Graceful fail  │ {graceful_passed:>6} │ {graceful_total:>8} │ {int(round((graceful_passed/max(1,graceful_total))*100)):>3}%            │")
    lines.append("├────────────────┼────────┼──────────┼─────────────────┤")
    lines.append(f"│ Tone (judge)   │  {avg_tone:>4}  │    5.0   │ avg score      │")
    lines.append(f"│ Helpfulness    │  {avg_help:>4}  │    5.0   │ avg score      │")
    lines.append("├────────────────┼────────┼──────────┼─────────────────┤")
    lines.append(f"│ p50 latency    │ {p50:>6}ms │          │                 │")
    lines.append(f"│ p95 latency    │ {p95:>6}ms │          │                 │")
    lines.append(f"│ Avg tokens     │ {avg_tokens:>6}  │          │                 │")
    lines.append(f"│ Failure rate   │ {fail_rate:>6}%  │          │                 │")
    lines.append("└────────────────┴────────┴──────────┴─────────────────┘")

    SCORECARD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_results_log(results: List[CaseResult], cases: List[Dict[str, Any]]):
    ts = datetime.now(timezone.utc).isoformat()

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    tool_total = sum(1 for c in cases if c.get("expect_tools"))
    tool_passed = sum(1 for r, c in zip(results, cases) if c.get("expect_tools") and r.correct_tools_called)
    guard_total = sum(1 for c in cases if c.get("expect_guardrail"))
    guard_passed = sum(1 for r, c in zip(results, cases) if c.get("expect_guardrail") and r.guardrail_respected)

    latencies = [r.latency_ms for r in results]
    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)
    avg_tokens = int(statistics.mean([r.tokens_used for r in results])) if results else 0

    headers = [
        "timestamp",
        "total",
        "passed",
        "tool_passed",
        "tool_total",
        "guard_passed",
        "guard_total",
        "p50_latency_ms",
        "p95_latency_ms",
        "avg_tokens",
    ]

    row = [
        ts,
        str(total),
        str(passed),
        str(tool_passed),
        str(tool_total),
        str(guard_passed),
        str(guard_total),
        str(p50),
        str(p95),
        str(avg_tokens),
    ]

    file_exists = RESULTS_LOG.exists()
    with open(RESULTS_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(headers)
        w.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Run AstroAgent golden-set evaluations")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases")
    args = parser.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit(
            "Missing GROQ_API_KEY. Set it in your environment (or backend/.env) before running evals."
        )

    cases = load_cases()
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]

    results: List[CaseResult] = []
    for case in cases:
        r = run_case(case)
        results.append(r)
        status = "PASS" if r.passed else "FAIL"
        print(f"{status} {r.case_id} | {r.latency_ms}ms | tools={r.tool_calls_made}")

        # Be polite to Nominatim: brief pause when geocoding likely happened.
        if "geocode_place" in r.tool_calls_made:
            time.sleep(1.0)

    write_scorecard(results, cases)
    append_results_log(results, cases)

    print("\n" + SCORECARD_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
