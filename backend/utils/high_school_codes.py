"""Shared high-school budget code set for per-institution attribution."""

HIGH_SCHOOL_CODES = {
    "001",
    "035",
    "071",
    "173",
    "237",
    "361",
    "456",
    "611",
    "654",
    "660",
    "707",
}


def is_high_school_code(topic_code: str) -> bool:
    return str(topic_code).strip() in HIGH_SCHOOL_CODES
