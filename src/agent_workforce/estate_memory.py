"""Unified estate memory: the one store Otto, the voice and the operator's own sessions share.

The crew reads it at the start of a run (brief), may recall and remember while working, and
writes one outcome line at the end. It is reached through the estate's MCP gateway with the
gateway key, both named by the workload and never by this file (LAW 46):

    ESTATE_MCP_URL       the gateway's estate MCP endpoint
    ESTATE_MCP_KEY_FILE  a file holding its bearer key

Either missing, empty or unreadable and the whole module is off: every call returns None and the
run is exactly what it was before. Memory is advisory. An outage, a refusal or a slow answer is
logged and swallowed; it never fails a run.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

RUNTIME = "agent-workforce"
SOURCE = "crew-run"
TIMEOUT_S = 10
PROTOCOL_VERSION = "2025-03-26"


def _settings() -> tuple[str, str] | None:
    url = os.environ.get("ESTATE_MCP_URL", "").strip()
    key_file = os.environ.get("ESTATE_MCP_KEY_FILE", "").strip()
    if not url or not key_file:
        return None
    try:
        key = Path(key_file).read_text(encoding="utf-8").strip()
    except OSError as why:
        log.warning("estate memory off: key file unreadable (%s)", why)
        return None
    return (url, key) if key else None


def enabled() -> bool:
    return _settings() is not None


def _body(answer: requests.Response) -> dict:
    """A JSON body, or an event stream whose last `data:` line is the JSON-RPC answer."""
    text = answer.text
    if "text/event-stream" in answer.headers.get("content-type", ""):
        data = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        text = data[-1] if data else ""
    return json.loads(text) if text.strip() else {}


def _rpc(url: str, headers: dict, rid: int, method: str, params: dict) -> tuple[dict, requests.Response]:
    answer = requests.post(
        url,
        json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params},
        headers=headers,
        timeout=TIMEOUT_S,
    )
    answer.raise_for_status()
    return _body(answer), answer


def call(tool: str, arguments: dict[str, Any]) -> Any | None:
    """Call one memory tool. The decoded result, or None when off or on any failure."""
    settings = _settings()
    if settings is None:
        return None
    url, key = settings
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "authorization": f"Bearer {key}",
    }
    try:
        _, hello = _rpc(
            url,
            headers,
            1,
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": RUNTIME, "version": "1"},
            },
        )
        session = hello.headers.get("mcp-session-id")
        if session:
            headers["mcp-session-id"] = session
        reply, _ = _rpc(url, headers, 2, "tools/call", {"name": tool, "arguments": arguments})
        if "error" in reply:
            raise RuntimeError(reply["error"])
        result = reply.get("result") or {}
        text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise RuntimeError(text[:300])
        try:
            return json.loads(text)
        except ValueError:
            return text
    except Exception as why:  # noqa: BLE001 -- memory is advisory; nothing here may fail a run
        log.warning("estate memory %s failed: %s", tool, str(why)[:300])
        return None


def brief(task: str, limit: int = 8) -> str:
    """What the estate already knows about this task, as plain lines for the crew's context."""
    found = call("brief", {"task": task, "limit": limit})
    if not isinstance(found, dict):
        return ""
    items = found.get("relevant") or found.get("memories") or []
    lines = [f"- {item.get('text', '').strip()}" for item in items if isinstance(item, dict) and item.get("text")]
    return "\n".join(lines)


def recall(query: str, limit: int = 8) -> Any | None:
    return call("recall", {"query": query, "limit": limit})


def remember(content: str, subject: str = "", kind: str = "") -> bool:
    arguments: dict[str, Any] = {"content": content, "source": SOURCE, "runtime": RUNTIME}
    if subject:
        arguments["subject"] = subject
    if kind:
        arguments["kind"] = kind
    return call("remember", arguments) is not None
