from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import List, Tuple


NOTES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "astrology_notes.txt")


def _tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s♈♉♊♋♌♍♎♏♐♑♒♓]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return text.split(" ")


@lru_cache(maxsize=1)
def _load_paragraphs() -> List[str]:
    if not os.path.exists(NOTES_PATH):
        return []

    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    paras = [p.strip() for p in raw.split("\n\n")]
    return [p for p in paras if p]


def _score_chunk(query_tokens: List[str], chunk_tokens: List[str]) -> int:
    if not query_tokens or not chunk_tokens:
        return 0

    qset = set(query_tokens)
    cset = set(chunk_tokens)
    return len(qset.intersection(cset))


def keyword_rag_lookup(query: str, top_k: int = 2) -> List[str]:
    """Simple, honest keyword-overlap retrieval.

    Splits reference notes into paragraphs and scores each by keyword overlap.
    Returns the top_k paragraphs.
    """

    paragraphs = _load_paragraphs()
    if not paragraphs:
        return ["No reference notes are available."]

    qtoks = _tokenize(query)

    scored: List[Tuple[int, int, str]] = []
    for idx, para in enumerate(paragraphs):
        score = _score_chunk(qtoks, _tokenize(para))
        scored.append((score, idx, para))

    scored.sort(key=lambda t: (t[0], -t[1]), reverse=True)

    best = [para for score, _, para in scored if score > 0][:top_k]
    if best:
        return best

    # Fallback: return the most generally useful intro sections
    return paragraphs[:top_k]
