from __future__ import annotations

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional

# Import from installed MCP package - no namespace conflict since we renamed our local module
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPDateMathClient:
    def __init__(self, server_script_path: Path):
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def __aenter__(self) -> "MCPDateMathClient":
        server_params = StdioServerParameters(
            command=sys.executable,  # Use same Python interpreter (ensures same venv)
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
    server_path = Path(__file__).resolve().parent / "date_server.py"
    async with MCPDateMathClient(server_path) as client:
        return await client.days_between_dates(date1, date2, absolute=absolute)


def call_days_between_dates(date1: str, date2: str, absolute: bool = True) -> int:
    # We're in a normal CLI app, so asyncio.run is fine.
    return asyncio.run(_call_days_between_dates(date1, date2, absolute=absolute))

