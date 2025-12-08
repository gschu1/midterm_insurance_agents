from datetime import date


def compute_days_between_dates(start: str, end: str) -> int:
    """
    Compute the number of days between two ISO dates (YYYY-MM-DD).

    In a full system this would be exposed as an MCP tool so the LLM
    can offload precise date arithmetic. For the midterm we call it
    directly from the agent layer to demonstrate 'LLM + tool' behavior.
    """
    s_year, s_month, s_day = map(int, start.split("-"))
    e_year, e_month, e_day = map(int, end.split("-"))

    d1 = date(s_year, s_month, s_day)
    d2 = date(e_year, e_month, e_day)

    return (d2 - d1).days
