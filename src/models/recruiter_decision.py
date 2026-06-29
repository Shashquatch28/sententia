from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class Recommendation(Enum):
    STRONGLY_ADVANCE = "STRONGLY_ADVANCE"
    ADVANCE = "ADVANCE"
    REVIEW_FURTHER = "REVIEW_FURTHER"
    ADVANCE_IF_POOL_THIN = "ADVANCE_IF_POOL_THIN"
    DECLINE = "DECLINE"


@dataclass
class TrustSignal:
    signal_type: str  # "VERIFIED", "PLAUSIBLE", "SUSPICIOUS", "UNVERIFIABLE"
    description: str
    confidence: float  # 0.0–1.0
    field_name: str = ""


@dataclass
class TrustAssessment:
    overall_trust_score: float  # 0.0–1.0
    trust_tier: str  # "HIGH", "MEDIUM", "LOW"
    signals: List[TrustSignal] = field(default_factory=list)
    verified_claims: List[str] = field(default_factory=list)
    unverifiable_claims: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


@dataclass
class FitDimension:
    score: float  # 0.0–1.0
    evidence: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


@dataclass
class FitAssessment:
    technical: FitDimension
    product: FitDimension
    cultural: FitDimension
    growth: FitDimension

    @property
    def overall(self) -> float:
        return (
            self.technical.score * 0.35
            + self.product.score * 0.30
            + self.cultural.score * 0.20
            + self.growth.score * 0.15
        )

    def to_dict(self) -> dict:
        return {
            "technical": {
                "score": self.technical.score,
                "evidence": self.technical.evidence,
                "gaps": self.technical.gaps,
            },
            "product": {
                "score": self.product.score,
                "evidence": self.product.evidence,
                "gaps": self.product.gaps,
            },
            "cultural": {
                "score": self.cultural.score,
                "evidence": self.cultural.evidence,
                "gaps": self.cultural.gaps,
            },
            "growth": {
                "score": self.growth.score,
                "evidence": self.growth.evidence,
                "gaps": self.growth.gaps,
            },
            "overall": self.overall,
        }


@dataclass
class HiringRisk:
    risk_type: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    description: str
    mitigation: str
    is_blocking: bool = False


@dataclass
class InterviewQuestion:
    question: str
    priority: str  # "HIGH", "MEDIUM", "LOW"
    dimension: str  # "Technical", "Product", "Cultural", "Growth"
    what_to_listen_for: str


@dataclass
class TimingAssessment:
    current_tenure_months: int
    likely_available: bool
    urgency_signal: str
    estimated_notice_weeks: int = 4


@dataclass
class RecruiterDecision:
    candidate_id: str
    recommendation: Recommendation
    trust_assessment: TrustAssessment
    fit_assessment: FitAssessment
    hiring_risks: List[HiringRisk]
    interview_focus: List[InterviewQuestion]
    recommendation_rationale: str
    timing_assessment: Optional[TimingAssessment] = None
    required_skills_matched: List[str] = field(default_factory=list)
    overall_match_score: float = 0.0
    top_evidence: List[str] = field(default_factory=list)
    name: str = ""
    current_title: str = ""
    current_company: str = ""

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "current_title": self.current_title,
            "current_company": self.current_company,
            "recommendation": self.recommendation.value,
            "trust_assessment": {
                "overall_trust_score": self.trust_assessment.overall_trust_score,
                "trust_tier": self.trust_assessment.trust_tier,
                "signals": [
                    {
                        "signal_type": s.signal_type,
                        "description": s.description,
                        "confidence": s.confidence,
                        "field_name": s.field_name,
                    }
                    for s in self.trust_assessment.signals
                ],
                "verified_claims": self.trust_assessment.verified_claims,
                "unverifiable_claims": self.trust_assessment.unverifiable_claims,
                "red_flags": self.trust_assessment.red_flags,
            },
            "fit_assessment": self.fit_assessment.to_dict(),
            "hiring_risks": [
                {
                    "risk_type": r.risk_type,
                    "severity": r.severity,
                    "description": r.description,
                    "mitigation": r.mitigation,
                    "is_blocking": r.is_blocking,
                }
                for r in self.hiring_risks
            ],
            "interview_focus": [
                {
                    "question": q.question,
                    "priority": q.priority,
                    "dimension": q.dimension,
                    "what_to_listen_for": q.what_to_listen_for,
                }
                for q in self.interview_focus
            ],
            "recommendation_rationale": self.recommendation_rationale,
            "timing_assessment": {
                "current_tenure_months": self.timing_assessment.current_tenure_months,
                "likely_available": self.timing_assessment.likely_available,
                "urgency_signal": self.timing_assessment.urgency_signal,
                "estimated_notice_weeks": self.timing_assessment.estimated_notice_weeks,
            }
            if self.timing_assessment
            else None,
            "required_skills_matched": self.required_skills_matched,
            "overall_match_score": self.overall_match_score,
            "top_evidence": self.top_evidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecruiterDecision":
        trust = data.get("trust_assessment", {}) or {}
        fit = data.get("fit_assessment", {}) or {}

        return cls(
            candidate_id=str(data.get("candidate_id", "")),
            recommendation=Recommendation(str(data.get("recommendation", "REVIEW_FURTHER"))),
            trust_assessment=TrustAssessment(
                overall_trust_score=float(trust.get("overall_trust_score", 0.0)),
                trust_tier=str(trust.get("trust_tier", "LOW")),
                signals=[
                    TrustSignal(
                        signal_type=str(s.get("signal_type", "")),
                        description=str(s.get("description", "")),
                        confidence=float(s.get("confidence", 0.0)),
                        field_name=str(s.get("field_name", "")),
                    )
                    for s in trust.get("signals", []) or []
                    if isinstance(s, dict)
                ],
                verified_claims=list(trust.get("verified_claims", []) or []),
                unverifiable_claims=list(trust.get("unverifiable_claims", []) or []),
                red_flags=list(trust.get("red_flags", []) or []),
            ),
            fit_assessment=FitAssessment(
                technical=FitDimension(
                    score=float(fit.get("technical", {}).get("score", 0.0)),
                    evidence=list(fit.get("technical", {}).get("evidence", []) or []),
                    gaps=list(fit.get("technical", {}).get("gaps", []) or []),
                ),
                product=FitDimension(
                    score=float(fit.get("product", {}).get("score", 0.0)),
                    evidence=list(fit.get("product", {}).get("evidence", []) or []),
                    gaps=list(fit.get("product", {}).get("gaps", []) or []),
                ),
                cultural=FitDimension(
                    score=float(fit.get("cultural", {}).get("score", 0.0)),
                    evidence=list(fit.get("cultural", {}).get("evidence", []) or []),
                    gaps=list(fit.get("cultural", {}).get("gaps", []) or []),
                ),
                growth=FitDimension(
                    score=float(fit.get("growth", {}).get("score", 0.0)),
                    evidence=list(fit.get("growth", {}).get("evidence", []) or []),
                    gaps=list(fit.get("growth", {}).get("gaps", []) or []),
                ),
            ),
            hiring_risks=[
                HiringRisk(
                    risk_type=str(r.get("risk_type", "")),
                    severity=str(r.get("severity", "LOW")),
                    description=str(r.get("description", "")),
                    mitigation=str(r.get("mitigation", "")),
                    is_blocking=bool(r.get("is_blocking", False)),
                )
                for r in data.get("hiring_risks", []) or []
                if isinstance(r, dict)
            ],
            interview_focus=[
                InterviewQuestion(
                    question=str(q.get("question", "")),
                    priority=str(q.get("priority", "LOW")),
                    dimension=str(q.get("dimension", "")),
                    what_to_listen_for=str(q.get("what_to_listen_for", "")),
                )
                for q in data.get("interview_focus", []) or []
                if isinstance(q, dict)
            ],
            recommendation_rationale=str(data.get("recommendation_rationale", "")),
            timing_assessment=(
                TimingAssessment(
                    current_tenure_months=int(data.get("timing_assessment", {}).get("current_tenure_months", 0)),
                    likely_available=bool(data.get("timing_assessment", {}).get("likely_available", False)),
                    urgency_signal=str(data.get("timing_assessment", {}).get("urgency_signal", "")),
                    estimated_notice_weeks=int(data.get("timing_assessment", {}).get("estimated_notice_weeks", 4)),
                )
                if data.get("timing_assessment")
                else None
            ),
            required_skills_matched=list(data.get("required_skills_matched", []) or []),
            overall_match_score=float(data.get("overall_match_score", 0.0)),
            top_evidence=list(data.get("top_evidence", []) or []),
            name=str(data.get("name", "")),
            current_title=str(data.get("current_title", "")),
            current_company=str(data.get("current_company", "")),
        )


@dataclass
class CandidateIntelligenceProfile:
    candidate_id: str
    name: str
    current_title: str
    current_company: str
    # "builder", "operator", "specialist", "generalist", "consultant"
    narrative_type: str
    consistency_score: float  # 0.0–1.0
    skill_duration_credible: bool
    ownership_language_score: float  # fraction of leadership/ownership verbs
    outcome_language_score: float  # fraction of metric/outcome phrases
    product_company_fraction: float  # fraction of career at product companies
    top_skills: List[str] = field(default_factory=list)
    career_trajectory: str = "mixed"  # "upward", "lateral", "downward", "mixed"
    red_flags: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    fast_score: float = 0.0
    years_of_experience: float = 0.0
    total_months: int = 0
    redrob_trust: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "current_title": self.current_title,
            "current_company": self.current_company,
            "narrative_type": self.narrative_type,
            "consistency_score": self.consistency_score,
            "skill_duration_credible": self.skill_duration_credible,
            "ownership_language_score": self.ownership_language_score,
            "outcome_language_score": self.outcome_language_score,
            "product_company_fraction": self.product_company_fraction,
            "top_skills": self.top_skills,
            "career_trajectory": self.career_trajectory,
            "red_flags": self.red_flags,
            "green_flags": self.green_flags,
            "fast_score": self.fast_score,
            "years_of_experience": self.years_of_experience,
            "total_months": self.total_months,
            "redrob_trust": self.redrob_trust,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateIntelligenceProfile":
        return cls(
            candidate_id=str(data.get("candidate_id", "")),
            name=str(data.get("name", "")),
            current_title=str(data.get("current_title", "")),
            current_company=str(data.get("current_company", "")),
            narrative_type=str(data.get("narrative_type", "mixed")),
            consistency_score=float(data.get("consistency_score", 0.0)),
            skill_duration_credible=bool(data.get("skill_duration_credible", False)),
            ownership_language_score=float(data.get("ownership_language_score", 0.0)),
            outcome_language_score=float(data.get("outcome_language_score", 0.0)),
            product_company_fraction=float(data.get("product_company_fraction", 0.0)),
            top_skills=list(data.get("top_skills", []) or []),
            career_trajectory=str(data.get("career_trajectory", "mixed")),
            red_flags=list(data.get("red_flags", []) or []),
            green_flags=list(data.get("green_flags", []) or []),
            fast_score=float(data.get("fast_score", 0.0)),
            years_of_experience=float(data.get("years_of_experience", 0.0)),
            total_months=int(data.get("total_months", 0)),
            redrob_trust=dict(data.get("redrob_trust", {}) or {}),
        )
