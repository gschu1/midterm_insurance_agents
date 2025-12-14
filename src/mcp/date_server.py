from __future__ import annotations

import logging
import sys
from datetime import datetime, date
from pathlib import Path

# Import from installed MCP package, not local src/mcp directory
# Note: The MCP server runs as a separate process, so it typically won't have namespace conflicts.
# But we handle the import gracefully just in case.
try:
    # Try importing directly first
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # If that fails, try to import from site-packages directly
    try:
        import site
        _site_packages = site.getsitepackages()
        for sp in _site_packages:
            fastmcp_path = Path(sp) / 'mcp' / 'server' / 'fastmcp.py'
            if fastmcp_path.exists():
                # Temporarily prioritize this site-packages path
                _original_path = sys.path[:]
                _conflicting = [p for p in _original_path if 'src' in str(p) and 'site-packages' not in str(p)]
                for cp in _conflicting:
                    if cp in sys.path:
                        sys.path.remove(cp)
                sys.path.insert(0, sp)
                try:
                    from mcp.server.fastmcp import FastMCP
                finally:
                    sys.path[:] = _original_path
                break
        else:
            raise ImportError("Could not find installed mcp package")
    except Exception as e:
        raise ImportError(f"Failed to import MCP SDK. Make sure 'mcp' package is installed. Error: {e}")

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

