from datetime import date


def safe_lower(value):
    """Safely lowercase strings."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def clamp(value, minimum, maximum):
    """Clamp a value between min and max."""
    return max(minimum, min(value, maximum))


def company_is_consulting(company: str, consulting_companies: set[str]) -> bool:
    """Check whether a company belongs to the consulting blacklist."""
    company = safe_lower(company)
    return any(c in company for c in consulting_companies)


def years_to_months(years: float) -> int:
    return int(years * 12)


def months_to_years(months: int) -> float:
    return months / 12


def days_since(date_string: str) -> int:
    """
    Calculate days since YYYY-MM-DD.
    """
    dt = date.fromisoformat(date_string)
    return (date.today() - dt).days