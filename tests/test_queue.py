"""With no argument the crew takes the oldest queued ticket that nobody has planned yet, or stays idle."""

from __future__ import annotations

from agent_workforce import main
from agent_workforce.estate import Estate
from agent_workforce.tools.github_client import GitHub


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
    """Every queued lane is asked, and the board's own creation order decides which ticket is oldest."""
    asked: list[str] = []
    tickets = {
        "lane:platform": [{"number": 7, "created_at": "2026-09-01T00:00:00Z"}],
        "lane:agents": [{"number": 9, "created_at": "2026-09-02T00:00:00Z"}],
    }
    monkeypatch.setattr(
        GitHub,
        "open_issues",
        lambda self, repo, label: asked.append(f"{repo} {label}") or tickets.get(label, []),
    )
    monkeypatch.setattr(
        GitHub,
        "issue_comments",
        lambda self, repo, n: [{"body": "plan ... Optimised: 9 -> 3"}] if n == 7 else [],
    )
    assert main.next_ticket(_estate(tmp_path), "crew") == 9
    assert asked == [f"owner/crew {label}" for label in main.QUEUE_LABELS]


def test_every_queued_lane_exists_on_the_board():
    """A label the board does not carry matches nothing, and the crew idles forever (crew#850 CP0)."""
    assert "lane:infra" not in main.QUEUE_LABELS
    assert set(main.QUEUE_LABELS) <= {
        "lane:agents",
        "lane:platform",
        "lane:security",
        "lane:money",
        "lane:observability",
        "lane:process",
        "lane:science",
        "lane:dr",
        "lane:unsorted",
    }


def test_idle_when_every_ticket_is_planned(monkeypatch, tmp_path):
    monkeypatch.setattr(
        GitHub, "open_issues", lambda self, repo, label: [{"number": 7, "created_at": "2026-09-01T00:00:00Z"}]
    )
    monkeypatch.setattr(GitHub, "issue_comments", lambda self, repo, n: [{"body": "Optimised: done"}])
    assert main.next_ticket(_estate(tmp_path), "crew") is None
