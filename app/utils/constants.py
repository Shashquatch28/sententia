"""
Application-wide constants.

This file contains every configurable/static value used by the ranking
pipeline. No magic numbers should appear anywhere else in the codebase.
"""

# -------------------------------
# COMPANY LISTS
# -------------------------------

CONSULTING_COMPANIES = {
    "tcs",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "tech mahindra",
    "mphasis",
    "hexaware",
}

# -------------------------------
# TITLE KEYWORDS
# -------------------------------

AI_TITLES = {
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "nlp engineer",
    "search engineer",
    "recommendation engineer",
    "applied scientist",
    "data scientist",
}

NEGATIVE_TITLES = {
    "marketing manager",
    "operations manager",
    "accountant",
    "civil engineer",
    "hr manager",
    "content writer",
}

# -------------------------------
# PROFICIENCY
# -------------------------------

PROFICIENCY_WEIGHTS = {
    "beginner": 0.25,
    "intermediate": 0.50,
    "advanced": 0.80,
    "expert": 1.00,
}

# -------------------------------
# EDUCATION
# -------------------------------

TIER_SCORES = {
    "tier_1": 1.00,
    "tier_2": 0.75,
    "tier_3": 0.50,
    "tier_4": 0.25,
    "unknown": 0.35,
}