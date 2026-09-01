"""The repository: read files, write on the crew's own branch, open a pull request, read its checks.

The crew's branches all start with `infra-crew/` and it may write nowhere else: the branch prefix
is the only place its commits can land, and the pull request is the only way they move.
"""

from __future__ import annotations

import json

from crewai.tools import tool

from infra_crew.tools._client import full, github

BRANCH_PREFIX = "infra-crew/"


def _own(branch: str) -> str:
    if not branch.startswith(BRANCH_PREFIX):
        raise ValueError(f"the crew writes only on branches named {BRANCH_PREFIX}*, not '{branch}'")
    return branch


@tool("read_file")
def read_file(repo: str, path: str, ref: str = "main") -> str:
    """Read one file from a repository at a branch or commit."""
    return github().read_file(full(repo), path, ref)


@tool("list_directory")
def list_directory(repo: str, path: str = "", ref: str = "main") -> str:
    """List the entries of a directory in a repository."""
    entries = github().contents(full(repo), path, ref)
    if isinstance(entries, dict):
        entries = [entries]
    return "\n".join(f"{e['type']} {e['path']}" for e in entries)


@tool("create_branch")
def create_branch(repo: str, branch: str, from_branch: str = "main") -> str:
    """Create the crew's own branch (name must start with 'infra-crew/'). Returns the base commit."""
    return github().create_branch(full(repo), _own(branch), from_branch)


@tool("write_file")
def write_file(repo: str, branch: str, path: str, content: str, message: str) -> str:
    """Create or replace one file on the crew's own branch with a commit. Returns the commit sha."""
    return github().write_file(full(repo), _own(branch), path, content, message)


@tool("open_pull_request")
def open_pull_request(repo: str, branch: str, title: str, body: str, base: str = "main") -> str:
    """Open a pull request from the crew's branch. The founder merges; the crew never does."""
    return github().open_pull_request(full(repo), _own(branch), base, title, body)


@tool("read_pull_request_checks")
def read_pull_request_checks(repo: str, number: int) -> str:
    """Read a pull request's state and the result of every check on its head commit."""
    gh = github()
    pr = gh.pull_request(full(repo), number)
    checks = gh.check_runs(full(repo), pr["head"]["sha"])
    return json.dumps(
        {
            "url": pr["html_url"],
            "state": pr["state"],
            "merged": pr.get("merged", False),
            "head": pr["head"]["sha"],
            "checks": [
                {
                    "name": c["name"],
                    "status": c["status"],
                    "conclusion": c["conclusion"],
                    "url": c["html_url"],
                }
                for c in checks
            ],
        },
        indent=1,
    )
