from app.models.candidate import Candidate


class CandidateParser:
    """Converts raw JSON dictionaries into Candidate objects."""

    @staticmethod
    def parse(data: dict) -> Candidate:
        return Candidate(
            candidate_id=data["candidate_id"],
            profile=data.get("profile", {}),
            career_history=data.get("career_history", []),
            education=data.get("education", []),
            skills=data.get("skills", []),
            redrob_signals=data.get("redrob_signals", {}),
        )