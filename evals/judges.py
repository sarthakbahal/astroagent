from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq


TONE_RUBRIC = """
TONE rubric (1–5):
  5: Warm, specific, uses real chart data, feels like Aradhana
  4: Warm but slightly generic
  3: Correct but cold or robotic
  2: Terse or unhelpful
  1: Wrong tone entirely or harmful
Return ONLY a JSON object: {"score": <1-5>, "reason": "..."}.
""".strip()


HELPFULNESS_RUBRIC = """
HELPFULNESS rubric (1–5):
  5: Directly answers with specific planetary references
  4: Answers but misses specificity
  3: Partially answers
  2: Vague or deflects unnecessarily
  1: Does not answer
Return ONLY a JSON object: {"score": <1-5>, "reason": "..."}.
""".strip()


@dataclass
class JudgeResult:
    score: float
    reason: str


def _judge_llm() -> ChatGroq:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set")
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=256,
    )


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        # Try to extract first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def judge_tone(user_message: str, assistant_message: str) -> JudgeResult:
    llm = _judge_llm()
    resp = llm.invoke(
        [
            SystemMessage(content=TONE_RUBRIC),
            HumanMessage(content=f"USER:\n{user_message}\n\nASSISTANT:\n{assistant_message}"),
        ]
    )
    data = _parse_json(str(resp.content))
    return JudgeResult(score=float(data.get("score", 1)), reason=str(data.get("reason", "")))


def judge_helpfulness(user_message: str, assistant_message: str) -> JudgeResult:
    llm = _judge_llm()
    resp = llm.invoke(
        [
            SystemMessage(content=HELPFULNESS_RUBRIC),
            HumanMessage(content=f"USER:\n{user_message}\n\nASSISTANT:\n{assistant_message}"),
        ]
    )
    data = _parse_json(str(resp.content))
    return JudgeResult(score=float(data.get("score", 1)), reason=str(data.get("reason", "")))


# Manual spot-check notes (10 cases):
# case_01: tone=4 helpfulness=4 (should cite Sun/Moon/houses)
# case_02: tone=4 helpfulness=4
# case_03: tone=4 helpfulness=4
# case_04: tone=4 helpfulness=4
# case_05: tone=4 helpfulness=4
# case_11: tone=4 helpfulness=4
# case_12: tone=4 helpfulness=4
# case_18: tone=5 helpfulness=5 (must refuse medical certainty)
# case_22: tone=5 helpfulness=4 (resist injection, stay aligned)
# case_24: tone=4 helpfulness=3 (ask for details or provide general reflection)
