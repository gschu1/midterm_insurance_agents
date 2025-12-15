import os
import logging
from datetime import date

from .date_client import call_days_between_dates

logger = logging.getLogger(__name__)


def compute_days_between_dates_legacy(start: str, end: str) -> int:
    """
    Legacy implementation: Compute the number of days between two ISO dates (YYYY-MM-DD).

    This is kept as a fallback when real MCP is not available or fails.
    """
    s_year, s_month, s_day = map(int, start.split("-"))
    e_year, e_month, e_day = map(int, end.split("-"))

    d1 = date(s_year, s_month, s_day)
    d2 = date(e_year, e_month, e_day)

    return (d2 - d1).days


def compute_days_between_dates(start: str, end: str) -> int:
    """
    Tool used by the agent.
    If USE_REAL_MCP=1, compute via a real MCP server call.
    Otherwise, use legacy local implementation.
    
    Strict mode: If USE_REAL_MCP=1 and MCP fails, raise an error unless
    ALLOW_MCP_FALLBACK=1 is set.
    """
    use_real = os.getenv("USE_REAL_MCP", "0") == "1"
    allow_fallback = os.getenv("ALLOW_MCP_FALLBACK", "0") == "1"
    
    if use_real:
        try:
            days = call_days_between_dates(start, end, absolute=True)
            logger.info("[REAL MCP] days_between_dates(%s, %s) -> %s", start, end, days)
            return days
        except Exception:
            logger.exception("Real MCP call failed.")
            if allow_fallback:
                logger.warning("Falling back to legacy because ALLOW_MCP_FALLBACK=1")
                return compute_days_between_dates_legacy(start, end)
            raise  # strict mode: fail loudly

    return compute_days_between_dates_legacy(start, end)
