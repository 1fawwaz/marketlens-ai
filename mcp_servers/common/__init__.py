"""Common MCP server bootstrap."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def json_result(payload: dict) -> str:
    return json.dumps(payload, default=str)
