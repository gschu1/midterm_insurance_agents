from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional

# Import from installed MCP package, not local src/mcp directory
# Find and load directly from site-packages to avoid conflicts
try:
    import site
    _site_packages = site.getsitepackages()
    _mcp_installed_path = None
    for sp in _site_packages:
        mcp_init = Path(sp) / 'mcp' / '__init__.py'
        if mcp_init.exists():
            _mcp_installed_path = sp
            break
    
    if _mcp_installed_path:
        # Import from installed package by temporarily prioritizing site-packages
        # Don't delete modules - just ensure we import from the right place
        _original_path = sys.path[:]
        
        # Temporarily move site-packages to front, move conflicting paths to back
        _conflicting_paths = [p for p in _original_path if any(x in str(p).lower() for x in ['src', 'midterm_insurance_agents']) and 'site-packages' not in str(p) and 'dist-packages' not in str(p)]
        _other_paths = [p for p in _original_path if p not in _conflicting_paths]
        sys.path = [_mcp_installed_path] + _other_paths + _conflicting_paths
        
        try:
            # Use importlib to force import from current sys.path (which prioritizes site-packages)
            # ClientSession is in mcp.client.session, StdioServerParameters is in mcp.client.stdio
            _mcp_client_session = importlib.import_module('mcp.client.session')
            ClientSession = _mcp_client_session.ClientSession
            
            _mcp_client_stdio = importlib.import_module('mcp.client.stdio')
            StdioServerParameters = _mcp_client_stdio.StdioServerParameters
            stdio_client = _mcp_client_stdio.stdio_client
        finally:
            # Restore original path
            sys.path[:] = _original_path
    else:
        raise ImportError("Could not find installed mcp package")
except Exception as e:
    # If import fails due to namespace conflict, that's OK - legacy mode will be used
    # The MCP SDK import is optional; if it fails, real MCP won't be available
    # but the system will fall back to legacy mode automatically
    ClientSession = None
    StdioServerParameters = None  
    stdio_client = None
    _mcp_import_error = e

logger = logging.getLogger(__name__)


class MCPDateMathClient:
    def __init__(self, server_script_path: Path):
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def __aenter__(self) -> "MCPDateMathClient":
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script_path)],
            env=None,
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.exit_stack.aclose()

    async def days_between_dates(self, date1: str, date2: str, absolute: bool = True) -> int:
        if not self.session:
            raise RuntimeError("MCP session not initialized")

        result = await self.session.call_tool(
            "days_between_dates",
            {"date1": date1, "date2": date2, "absolute": absolute},
        )

        # MCP SDK returns "content" blocks; be forgiving about shape.
        if getattr(result, "content", None):
            block = result.content[0]
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text")

            if text is not None:
                text = str(text).strip()
                # 1) plain int
                try:
                    return int(text)
                except ValueError:
                    pass
                # 2) maybe JSON like {"days": 138}
                try:
                    obj = json.loads(text)
                    return int(obj["days"])
                except Exception:
                    pass

        # Last resort
        return int(str(result).strip())


async def _call_days_between_dates(date1: str, date2: str, absolute: bool = True) -> int:
    if ClientSession is None or stdio_client is None:
        raise ImportError("MCP SDK not available. This usually means there's a namespace conflict "
                         "between src/mcp and the installed mcp package. Use legacy mode instead.")
    server_path = Path(__file__).resolve().parent / "date_server.py"
    async with MCPDateMathClient(server_path) as client:
        return await client.days_between_dates(date1, date2, absolute=absolute)


def call_days_between_dates(date1: str, date2: str, absolute: bool = True) -> int:
    # We're in a normal CLI app, so asyncio.run is fine.
    return asyncio.run(_call_days_between_dates(date1, date2, absolute=absolute))

