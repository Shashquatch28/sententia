"""
Comparative Reasoning Engine
Compares two candidates across all fit dimensions and generates a structured comparison.
Used by Agent 5 and the Streamlit UI for on-demand comparisons.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import anthropic


@dataclass
class DimensionResult:
    winner: str  # "A", "B", or "TIE"
    a_score: float
    b_score: float
    rationale: str


@dataclass
class ComparisonResult:
    pair_key: str
    candidate_a_id: str
    candidate_b_id: str
    candidate_a_name: str
    candidate_b_name: str
    dimension_comparison: dict[str, DimensionResult]
    why_a_over_b: str
    b_salvage_scenario: str
    overall_winner: str  # "A", "B", or "TIE"

    def to_dict(self) -> dict:
        return {
            "pair_key": self.pair_key,
            "candidate_a_id": self.candidate_a_id,
            "candidate_b_id": self.candidate_b_id,
            "candidate_a_name": self.candidate_a_name,
            "candidate_b_name": self.candidate_b_name,
            "dimension_comparison": {
                dim: {
                    "winner": r.winner,
                    "a_score": r.a_score,
                    "b_score": r.b_score,
                    "rationale": r.rationale,
                }
                for dim, r in self.dimension_comparison.items()
            },
            "why_a_over_b": self.why_a_over_b,
            "b_salvage_scenario": self.b_salvage_scenario,
            "overall_winner": self.overall_winner,
        }


class ComparativeEngine:
    DIMENSIONS = ["Technical", "Product", "Cultural", "Growth"]
    DIMENSION_WEIGHTS = {"Technical": 0.35, "Product": 0.30, "Cultural": 0.20, "Growth": 0.15}

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self._model = model
        self._client: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def _extract_fit_scores(self, decision: dict) -> dict[str, float]:
        fit = decision.get("fit_assessment", {})
        return {
            "Technical": fit.get("technical", {}).get("score", 0.5),
            "Product": fit.get("product", {}).get("score", 0.5),
            "Cultural": fit.get("cultural", {}).get("score", 0.5),
            "Growth": fit.get("growth", {}).get("score", 0.5),
        }

    def _heuristic_comparison(
        self,
        decision_a: dict,
        decision_b: dict,
        profile_a: dict,
        profile_b: dict,
    ) -> ComparisonResult:
        """Fast heuristic comparison without LLM — used as fallback."""
        cid_a = decision_a["candidate_id"]
        cid_b = decision_b["candidate_id"]
        name_a = decision_a.get("name") or profile_a.get("name", cid_a)
        name_b = decision_b.get("name") or profile_b.get("name", cid_b)
        scores_a = self._extract_fit_scores(decision_a)
        scores_b = self._extract_fit_scores(decision_b)

        dimension_comparison = {}
        weighted_diff = 0.0
        for dim in self.DIMENSIONS:
            sa = scores_a[dim]
            sb = scores_b[dim]
            diff = sa - sb
            weighted_diff += diff * self.DIMENSION_WEIGHTS[dim]
            winner = "A" if diff > 0.05 else ("B" if diff < -0.05 else "TIE")
            dimension_comparison[dim] = DimensionResult(
                winner=winner,
                a_score=sa,
                b_score=sb,
                rationale=f"{name_a} scores {sa:.2f} vs {name_b} {sb:.2f} on {dim}.",
            )

        overall_winner = "A" if weighted_diff > 0.05 else ("B" if weighted_diff < -0.05 else "TIE")
        score_a = round(decision_a.get("overall_match_score", 0) * 100)
        score_b = round(decision_b.get("overall_match_score", 0) * 100)

        return ComparisonResult(
            pair_key=f"{cid_a}_{cid_b}",
            candidate_a_id=cid_a,
            candidate_b_id=cid_b,
            candidate_a_name=name_a,
            candidate_b_name=name_b,
            dimension_comparison=dimension_comparison,
            why_a_over_b=(
                f"{name_a} ({decision_a.get('current_title', '')} at {decision_a.get('current_company', '')}) "
                f"outscores {name_b} overall ({score_a} vs {score_b}) with stronger weighted fit across "
                f"the top dimensions."
            ),
            b_salvage_scenario=(
                f"{name_b} would be the stronger hire if the role prioritises "
                f"{'Product' if scores_b['Product'] > scores_a['Product'] else 'Technical'} depth "
                f"over the current discriminator weighting."
            ),
            overall_winner=overall_winner,
        )

    def compare(
        self,
        decision_a: dict,
        decision_b: dict,
        profile_a: dict,
        profile_b: dict,
        job_intel: Optional[dict] = None,
        use_llm: bool = True,
    ) -> ComparisonResult:
        """
        Compare two candidates. Uses LLM for richer analysis when use_llm=True.
        Falls back to heuristic comparison on failure.
        """
        if not use_llm:
            return self._heuristic_comparison(decision_a, decision_b, profile_a, profile_b)

        cid_a = decision_a["candidate_id"]
        cid_b = decision_b["candidate_id"]
        name_a = decision_a.get("name") or profile_a.get("name", cid_a)
        name_b = decision_b.get("name") or profile_b.get("name", cid_b)

        context = {
            "candidate_a": {
                "candidate_id": cid_a,
                "name": name_a,
                "title": decision_a.get("current_title") or profile_a.get("current_title", ""),
                "company": decision_a.get("current_company") or profile_a.get("current_company", ""),
                "recommendation": decision_a.get("recommendation", ""),
                "match_score": decision_a.get("overall_match_score", 0),
                "fit": decision_a.get("fit_assessment", {}),
                "skills": profile_a.get("top_skills", [])[:6],
                "required_skills_matched": decision_a.get("required_skills_matched", []),
                "rationale": decision_a.get("recommendation_rationale", ""),
            },
            "candidate_b": {
                "candidate_id": cid_b,
                "name": name_b,
                "title": decision_b.get("current_title") or profile_b.get("current_title", ""),
                "company": decision_b.get("current_company") or profile_b.get("current_company", ""),
                "recommendation": decision_b.get("recommendation", ""),
                "match_score": decision_b.get("overall_match_score", 0),
                "fit": decision_b.get("fit_assessment", {}),
                "skills": profile_b.get("top_skills", [])[:6],
                "required_skills_matched": decision_b.get("required_skills_matched", []),
                "rationale": decision_b.get("recommendation_rationale", ""),
            },
        }

        role_context = job_intel.get("role_summary", "") if job_intel else ""

        prompt = f"""Compare these two candidates for this role: {role_context}

{json.dumps(context, indent=2)}

Return ONLY valid JSON:
{{
  "dimension_comparison": {{
    "Technical": {{"winner": "A|B|TIE", "a_score": 0.0_to_1.0, "b_score": 0.0_to_1.0, "rationale": "specific reason citing their actual skills/companies"}},
    "Product":   {{"winner": "A|B|TIE", "a_score": 0.0, "b_score": 0.0, "rationale": "..."}},
    "Cultural":  {{"winner": "A|B|TIE", "a_score": 0.0, "b_score": 0.0, "rationale": "..."}},
    "Growth":    {{"winner": "A|B|TIE", "a_score": 0.0, "b_score": 0.0, "rationale": "..."}}
  }},
  "why_a_over_b": "2-3 sentences: why {name_a} ranks ahead of {name_b} — cite their actual titles, companies, skills",
  "b_salvage_scenario": "1-2 sentences: specific circumstances where {name_b} would be the better hire"
}}"""

        try:
            message = self.client.messages.create(
                model=self._model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text.strip()
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())

            dim_results = {}
            for dim in self.DIMENSIONS:
                d = data["dimension_comparison"].get(dim, {})
                dim_results[dim] = DimensionResult(
                    winner=d.get("winner", "TIE"),
                    a_score=float(d.get("a_score", 0.5)),
                    b_score=float(d.get("b_score", 0.5)),
                    rationale=d.get("rationale", ""),
                )

            # Determine overall winner from weighted scores
            weighted_a = sum(
                dim_results[dim].a_score * self.DIMENSION_WEIGHTS[dim]
                for dim in self.DIMENSIONS
            )
            weighted_b = sum(
                dim_results[dim].b_score * self.DIMENSION_WEIGHTS[dim]
                for dim in self.DIMENSIONS
            )
            overall_winner = "A" if weighted_a > weighted_b + 0.03 else (
                "B" if weighted_b > weighted_a + 0.03 else "TIE"
            )

            return ComparisonResult(
                pair_key=f"{cid_a}_{cid_b}",
                candidate_a_id=cid_a,
                candidate_b_id=cid_b,
                candidate_a_name=name_a,
                candidate_b_name=name_b,
                dimension_comparison=dim_results,
                why_a_over_b=data.get("why_a_over_b", ""),
                b_salvage_scenario=data.get("b_salvage_scenario", ""),
                overall_winner=overall_winner,
            )

        except Exception:
            return self._heuristic_comparison(decision_a, decision_b, profile_a, profile_b)

    def compare_from_files(
        self,
        candidate_id_a: str,
        candidate_id_b: str,
        precomputed_root: Optional[Path] = None,
        job_intel: Optional[dict] = None,
        use_llm: bool = True,
    ) -> ComparisonResult:
        """Convenience method that loads files by candidate ID."""
        root = precomputed_root or Path(__file__).resolve().parents[4] / "precomputed"

        def load(subdir: str, cid: str) -> dict:
            path = root / subdir / f"{cid}.json"
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")
            with open(path, encoding="utf-8") as f:
                return json.load(f)

        # Check comparisons.json cache first
        comp_file = root / "comparisons.json"
        if comp_file.exists():
            with open(comp_file, encoding="utf-8") as f:
                cached = json.load(f)
            key = f"{candidate_id_a}_{candidate_id_b}"
            if key in cached:
                cached_data = cached[key]
                dim_results = {}
                for dim in self.DIMENSIONS:
                    d = cached_data.get("dimension_comparison", {}).get(dim, {})
                    dim_results[dim] = DimensionResult(
                        winner=d.get("winner", "TIE"),
                        a_score=d.get("a_score", 0.5),
                        b_score=d.get("b_score", 0.5),
                        rationale=d.get("rationale", ""),
                    )
                return ComparisonResult(
                    pair_key=key,
                    candidate_a_id=candidate_id_a,
                    candidate_b_id=candidate_id_b,
                    candidate_a_name=cached_data.get("candidate_a", {}).get("name", candidate_id_a),
                    candidate_b_name=cached_data.get("candidate_b", {}).get("name", candidate_id_b),
                    dimension_comparison=dim_results,
                    why_a_over_b=cached_data.get("why_a_over_b", ""),
                    b_salvage_scenario=cached_data.get("b_salvage_scenario", ""),
                    overall_winner=cached_data.get("overall_winner", "TIE"),
                )

        decision_a = load("recruiter_decisions", candidate_id_a)
        decision_b = load("recruiter_decisions", candidate_id_b)
        profile_a = load("candidate_profiles", candidate_id_a)
        profile_b = load("candidate_profiles", candidate_id_b)

        return self.compare(decision_a, decision_b, profile_a, profile_b, job_intel, use_llm)
