from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


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
        }
