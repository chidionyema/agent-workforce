"""With no argument the crew takes the oldest queued ticket that nobody has planned yet, or stays idle."""

from __future__ import annotations

from infra_crew import main
from infra_crew.estate import Estate
from infra_crew.tools.github_client import GitHub


def _estate(tmp_path) -> Estate:
    placeholders = dict.fromkeys(["router_key", "langfuse_secret_key", "github_token"], "placeholder")
    return Estate(
        router_base_url="http://router.test",
        model="m",
        verifier_model="v",
        embed_model="e",
        otel_endpoint="http://collector.test",
        langfuse_base_url="http://langfuse.test",
        langfuse_public_key="pk",
        github_api="http://github.test",
        repo_owner="owner",
        laws_dir=tmp_path,
        storage_dir=tmp_path,
        **placeholders,
    )


def test_oldest_unplanned_ticket_wins(monkeypatch, tmp_path):
    seen: list[str] = []
    monkeypatch.setattr(
        GitHub,
        "open_issues",
        lambda self, repo, label: seen.append(f"{repo} {label}") or [{"number": 7}, {"number": 9}],
    )
    monkeypatch.setattr(
        GitHub,
        "issue_comments",
        lambda self, repo, n: [{"body": "plan ... Optimised: 9 -> 3"}] if n == 7 else [],
    )
    assert main.next_ticket(_estate(tmp_path), "crew") == 9
    assert seen == ["owner/crew lane:infra"]


def test_idle_when_every_ticket_is_planned(monkeypatch, tmp_path):
    monkeypatch.setattr(GitHub, "open_issues", lambda self, repo, label: [{"number": 7}])
    monkeypatch.setattr(GitHub, "issue_comments", lambda self, repo, n: [{"body": "Optimised: done"}])
    assert main.next_ticket(_estate(tmp_path), "crew") is None
