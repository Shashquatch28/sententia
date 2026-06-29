from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline.runner import load_jd_requirements
from src.pipeline.stream_parser import stream_candidates
from src.scoring.common import candidate_text, clamp, text


DEFAULT_CANDIDATES = ROOT / "datasets" / "candidates" / "candidates.jsonl"
DEFAULT_JD = ROOT / "config" / "jd_requirements.json"
DEFAULT_OUT = ROOT / "precomputed" / "semantic_scores.json"

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic semantic matching scores for rank.py."
    )
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--jd", default=str(DEFAULT_JD))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional smoke-test limit. 0 means all candidates.",
    )
    return parser.parse_args()


def _tokens(value: str) -> list[str]:
    return [tok for tok in TOKEN_RE.findall(text(value)) if len(tok) > 1]


def _candidate_document(candidate: dict[str, Any]) -> str:
    skill_text = " ".join(
        str(skill.get("name", ""))
        for skill in candidate.get("skills", []) or []
        if isinstance(skill, dict)
    )
    return f"{candidate_text(candidate)} {skill_text}"


def _jd_terms(jd: dict[str, Any]) -> tuple[Counter[str], list[str]]:
    phrases: list[str] = []
    weighted_tokens: Counter[str] = Counter()

    for skill, aliases in (jd.get("required_skill_aliases", {}) or {}).items():
        weighted_tokens.update(_tokens(skill))
        for alias in aliases:
            alias_l = text(alias)
            if alias_l:
                phrases.append(alias_l)
                weighted_tokens.update(_tokens(alias_l))

    for value in jd.get("nice_to_have_skills", []) or []:
        value_l = text(value)
        if value_l:
            phrases.append(value_l)
            weighted_tokens.update({token: 0.35 for token in _tokens(value_l)})

    for value in jd.get("hiring_manager_priorities", []) or []:
        weighted_tokens.update({token: 0.5 for token in _tokens(value)})

    return weighted_tokens, list(dict.fromkeys(phrases))


def _cosine(query: Counter[str], doc: Counter[str]) -> float:
    if not query or not doc:
        return 0.0
    numerator = sum(weight * doc.get(token, 0.0) for token, weight in query.items())
    q_norm = math.sqrt(sum(weight * weight for weight in query.values()))
    d_norm = math.sqrt(sum(weight * weight for weight in doc.values()))
    if not q_norm or not d_norm:
        return 0.0
    return numerator / (q_norm * d_norm)


def semantic_match_score(candidate: dict[str, Any], query: Counter[str], phrases: list[str], jd: dict[str, Any]) -> float:
    document = text(_candidate_document(candidate))
    doc_tokens = Counter(_tokens(document))
    cosine = _cosine(query, doc_tokens)

    phrase_hits = sum(1 for phrase in phrases if phrase and phrase in document)
    phrase_score = min(phrase_hits / 10.0, 1.0)

    title = text((candidate.get("profile", {}) or {}).get("current_title", ""))
    strong_titles = jd.get("strong_ai_titles", []) or []
    medium_titles = jd.get("medium_titles", []) or []
    title_score = 0.0
    if any(text(title_hint) in title for title_hint in strong_titles):
        title_score = 1.0
    elif any(text(title_hint) in title for title_hint in medium_titles):
        title_score = 0.55

    score = 0.65 * cosine + 0.25 * phrase_score + 0.10 * title_score
    return round(clamp(score), 6)


def main() -> int:
    args = _parse_args()
    jd = load_jd_requirements(args.jd)
    query, phrases = _jd_terms(jd)

    scores: dict[str, float] = {}
    for index, candidate in enumerate(stream_candidates(args.candidates), start=1):
        cid = str(candidate.get("candidate_id", ""))
        if cid:
            scores[cid] = semantic_match_score(candidate, query, phrases, jd)
        if args.limit and index >= args.limit:
            break

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, sort_keys=True)

    print(f"wrote {len(scores)} semantic scores to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
