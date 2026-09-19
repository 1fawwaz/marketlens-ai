"""MCP server: rag_search."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from backend.app.tools.handlers import handle_rag_search

mcp = MCPServer("marketlens-rag-search")


@mcp.tool(name="rag_search", description="Hybrid search over synthetic policy/SOP docs")
def rag_search(query: str, top_k: int = 5) -> str:
    result = handle_rag_search(query, top_k=top_k)
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run()
