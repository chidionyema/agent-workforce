"""The board: read a ticket, write a comment, file an incident. Plain English is enforced here."""

from __future__ import annotations

import json
import re

from crewai.tools import tool

from infra_crew.tools._client import full, github

# Words that never reach a founder surface (founder 2026-08-27 and 2026-08-31).
BANNED_ON_SURFACES = re.compile(r"\b(days?|weeks?|TODO|WIP|lgtm|ptal|nit)\b", re.IGNORECASE)


def _plain(body: str) -> str:
    hit = BANNED_ON_SURFACES.search(body)
    if hit:
        raise ValueError(f"'{hit.group(0)}' is not allowed on a founder surface; say what he can do instead.")
    return body


@tool("read_issue")
def read_issue(repo: str, number: int) -> str:
    """Read one board issue with its comments. repo is the repository name, e.g. 'crew' or 'idp'."""
    gh = github()
    issue = gh.issue(full(repo), number)
    comments = gh.issue_comments(full(repo), number)
    return json.dumps(
        {
            "title": issue["title"],
            "state": issue["state"],
            "labels": [label["name"] for label in issue.get("labels", [])],
            "body": issue.get("body") or "",
            "comments": [{"author": c["user"]["login"], "body": c["body"]} for c in comments],
        },
        indent=1,
    )


@tool("comment_on_issue")
def comment_on_issue(repo: str, number: int, body: str) -> str:
    """Write a plain-English comment on an issue or pull request. Returns the comment URL."""
    return github().comment(full(repo), number, _plain(body))


@tool("open_incident_issue")
def open_incident_issue(repo: str, title: str, body: str) -> str:
    """File an incident issue on the board (the watcher's only write). Returns the issue URL."""
    return github().open_issue(full(repo), _plain(title), _plain(body), labels=["incident", "lane:infra"])
