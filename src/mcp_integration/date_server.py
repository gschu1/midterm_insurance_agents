from __future__ import annotations

import logging
from datetime import datetime, date

# Import from installed MCP package - no namespace conflict since we renamed our local module
from mcp.server.fastmcp import FastMCP

# IMPORTANT: STDIO MCP servers must not print to stdout; use logging (stderr) instead.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("date-math")


def _parse_iso_date(s: str) -> date:
    """
    Accepts 'YYYY-MM-DD' or ISO datetime like '2024-01-03T19:40:00' (optionally with Z).
    Returns a date() (day resolution), which is exactly what we need for day-diff.
    """
    s = s.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return datetime.strptime(s, "%Y-%m-%d").date()


@mcp.tool()
async def days_between_dates(date1: str, date2: str, absolute: bool = True) -> int:
    """
    Compute day difference between two ISO dates/datetimes.

    Args:
        date1: ISO date or datetime string (e.g., '2024-01-03' or '2024-01-03T19:40:00')
        date2: ISO date or datetime string
        absolute: If true, return abs(date2 - date1). If false, return signed difference.
    """
    d1 = _parse_iso_date(date1)
    d2 = _parse_iso_date(date2)
    delta = (d2 - d1).days
    return abs(delta) if absolute else delta


def main() -> None:
    mcp.run(transport="stdio")  # canonical way to run FastMCP over STDIO


if __name__ == "__main__":
    main()

