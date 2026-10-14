"""Shared memory is advisory: off unless the workload names it, and no failure of it fails a run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from agent_workforce import estate_memory

URL = "http://gateway.test/estate/mcp"


class Answer:
    def __init__(self, body: str, content_type: str = "application/json", session: str | None = None):
        self.text = body
        self.headers = {"content-type": content_type}
        if session:
            self.headers["mcp-session-id"] = session

    def raise_for_status(self) -> None:
        return None


def _tool_reply(payload: object, is_error: bool = False) -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return json.dumps(
        {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}
    )


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    key = tmp_path / "ESTATE_MCP_KEY"
    key.write_text("k3y\n", encoding="utf-8")
    monkeypatch.setenv("ESTATE_MCP_URL", URL)
    monkeypatch.setenv("ESTATE_MCP_KEY_FILE", str(key))
    return key


def _gateway(monkeypatch: pytest.MonkeyPatch, tool_answer: Answer) -> list[dict]:
    sent: list[dict] = []

    def post(url, json, headers, timeout):  # noqa: A002 -- requests' own keyword
        sent.append({"url": url, "body": json, "headers": dict(headers), "timeout": timeout})
        if json["method"] == "initialize":
            return Answer('{"jsonrpc":"2.0","id":1,"result":{}}', session="s-1")
        return tool_answer

    monkeypatch.setattr(requests, "post", post)
    return sent


@pytest.mark.parametrize("missing", ["ESTATE_MCP_URL", "ESTATE_MCP_KEY_FILE"])
def test_off_without_either_setting_and_nothing_is_sent(monkeypatch, wired, missing):
    monkeypatch.delenv(missing)
    sent = _gateway(monkeypatch, Answer(_tool_reply({})))
    assert not estate_memory.enabled()
    assert estate_memory.brief("anything") == ""
    assert estate_memory.recall("anything") is None
    assert estate_memory.remember("a fact") is False
    assert sent == []


def test_off_when_the_key_file_cannot_be_read(monkeypatch, wired):
    wired.unlink()
    sent = _gateway(monkeypatch, Answer(_tool_reply({})))
    assert not estate_memory.enabled()
    assert estate_memory.recall("anything") is None
    assert sent == []


def test_brief_over_an_event_stream_carries_the_key_and_the_session(monkeypatch, wired):
    stream = "event: message\ndata: " + _tool_reply({"relevant": [{"text": "laws live in crew"}]}) + "\n\n"
    sent = _gateway(monkeypatch, Answer(stream, content_type="text/event-stream", session=None))

    assert estate_memory.brief("plan crew#9") == "- laws live in crew"
    init, call = sent
    assert init["body"]["method"] == "initialize"
    assert call["body"]["params"] == {"name": "brief", "arguments": {"task": "plan crew#9", "limit": 8}}
    assert call["headers"]["authorization"] == "Bearer k3y"
    assert call["headers"]["mcp-session-id"] == "s-1"
    assert "text/event-stream" in call["headers"]["accept"]
    assert all(s["timeout"] == estate_memory.TIMEOUT_S for s in sent)


def test_remember_names_this_runtime(monkeypatch, wired):
    sent = _gateway(monkeypatch, Answer(_tool_reply({"id": "m1"})))
    assert estate_memory.remember("run done", subject="owner/crew#9", kind="outcome") is True
    assert sent[-1]["body"]["params"]["arguments"] == {
        "content": "run done",
        "source": "crew-run",
        "runtime": "agent-workforce",
        "subject": "owner/crew#9",
        "kind": "outcome",
    }


@pytest.mark.parametrize(
    "failure",
    [
        requests.ConnectionError("gateway down"),
        requests.Timeout("slow"),
        Answer(_tool_reply("refused", is_error=True)),
        Answer('{"jsonrpc":"2.0","id":2,"error":{"code":-32000,"message":"unauthorised"}}'),
        Answer("not json"),
    ],
)
def test_every_failure_is_swallowed(monkeypatch, wired, failure):
    if isinstance(failure, Exception):

        def post(*_args, **_kwargs):
            raise failure

        monkeypatch.setattr(requests, "post", post)
    else:
        _gateway(monkeypatch, failure)
    assert estate_memory.recall("anything") is None
    assert estate_memory.brief("anything") == ""
    assert estate_memory.remember("a fact") is False


def test_the_tools_say_when_memory_is_absent(monkeypatch):
    pytest.importorskip("crewai")
    monkeypatch.delenv("ESTATE_MCP_URL", raising=False)
    from agent_workforce.tools.memory import UNAVAILABLE, recall, remember

    assert recall.run(query="x") == UNAVAILABLE
    assert remember.run(content="x") == UNAVAILABLE


def test_a_run_without_memory_briefs_the_plan_with_a_plain_placeholder(monkeypatch, tmp_path):
    from agent_workforce import main

    monkeypatch.delenv("ESTATE_MCP_URL", raising=False)
    assert main.recall_for_run(object(), "crew", 9) == main.NO_MEMORY  # type: ignore[arg-type]
