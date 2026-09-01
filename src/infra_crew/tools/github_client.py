"""The only door to GitHub, and it only opens on the routes listed here.

The crew has no merge, deploy, dispatch, secret or admin hand because the client does not know
those routes exist (remove the bad input, never guard it). A tool that asks for any other route
is refused before a byte leaves the pod. tests/test_no_deploy_hands.py grades this list forever.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

import requests

# method, path pattern (relative to the API root, no query string), plain-English purpose.
ALLOWED_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", r"/repos/[^/]+/[^/]+/issues/\d+", "read one board issue"),
    ("GET", r"/repos/[^/]+/[^/]+/issues/\d+/comments", "read the comments on an issue"),
    ("POST", r"/repos/[^/]+/[^/]+/issues/\d+/comments", "write a comment on an issue or pull request"),
    ("POST", r"/repos/[^/]+/[^/]+/issues", "open an incident issue (the watcher)"),
    ("GET", r"/repos/[^/]+/[^/]+/contents/.*", "read a file or list a directory"),
    ("PUT", r"/repos/[^/]+/[^/]+/contents/.*", "write a file on the crew's own branch"),
    ("GET", r"/repos/[^/]+/[^/]+/git/ref/heads/[^/]+", "read a branch head"),
    ("POST", r"/repos/[^/]+/[^/]+/git/refs", "create the crew's own branch"),
    ("GET", r"/repos/[^/]+/[^/]+/pulls", "list open pull requests"),
    ("POST", r"/repos/[^/]+/[^/]+/pulls", "open a pull request"),
    ("GET", r"/repos/[^/]+/[^/]+/pulls/\d+", "read a pull request"),
    ("GET", r"/repos/[^/]+/[^/]+/commits/[^/]+/check-runs", "read the checks on a commit"),
    (
        "GET",
        r"/repos/[^/]+/[^/]+/actions/workflows/[^/]+/runs",
        "list runs of a workflow (deploy logs, drills)",
    ),
    ("GET", r"/repos/[^/]+/[^/]+/actions/runs/\d+", "read one workflow run"),
    ("GET", r"/repos/[^/]+/[^/]+/actions/runs/\d+/jobs", "read the jobs of a run"),
    ("GET", r"/repos/[^/]+/[^/]+/actions/jobs/\d+/logs", "read the log of one job"),
)

_COMPILED = tuple((m, re.compile(f"^{p}$"), why) for m, p, why in ALLOWED_ROUTES)


class RouteRefused(PermissionError):
    """The crew asked for a route it does not have. This is by design, not a bug to fix."""


def route_allowed(method: str, path: str) -> bool:
    return any(m == method.upper() and rx.match(path) for m, rx, _ in _COMPILED)


@dataclass
class GitHub:
    api: str
    token: str
    timeout: float = 30.0

    def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        if not route_allowed(method, path):
            raise RouteRefused(f"{method.upper()} {path} is not a route this crew has.")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = requests.request(
            method.upper(), f"{self.api}{path}", headers=headers, timeout=self.timeout, **kwargs
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"GitHub {method.upper()} {path} answered {response.status_code}: {response.text[:400]}"
            )
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    # -- read -------------------------------------------------------------------------------
    def issue(self, repo: str, number: int) -> dict:
        return self._call("GET", f"/repos/{repo}/issues/{number}")

    def issue_comments(self, repo: str, number: int) -> list[dict]:
        return self._call("GET", f"/repos/{repo}/issues/{number}/comments", params={"per_page": 100})

    def contents(self, repo: str, path: str, ref: str) -> Any:
        return self._call("GET", f"/repos/{repo}/contents/{path}", params={"ref": ref})

    def read_file(self, repo: str, path: str, ref: str) -> str:
        data = self.contents(repo, path, ref)
        if isinstance(data, list):
            raise IsADirectoryError(path)
        return base64.b64decode(data["content"]).decode("utf-8")

    def branch_sha(self, repo: str, branch: str) -> str:
        return self._call("GET", f"/repos/{repo}/git/ref/heads/{branch}")["object"]["sha"]

    def pull_request(self, repo: str, number: int) -> dict:
        return self._call("GET", f"/repos/{repo}/pulls/{number}")

    def check_runs(self, repo: str, sha: str) -> list[dict]:
        return self._call("GET", f"/repos/{repo}/commits/{sha}/check-runs", params={"per_page": 100})[
            "check_runs"
        ]

    def workflow_runs(self, repo: str, workflow_file: str, limit: int = 10) -> list[dict]:
        data = self._call(
            "GET", f"/repos/{repo}/actions/workflows/{workflow_file}/runs", params={"per_page": limit}
        )
        return data["workflow_runs"]

    def run(self, repo: str, run_id: int) -> dict:
        return self._call("GET", f"/repos/{repo}/actions/runs/{run_id}")

    def run_jobs(self, repo: str, run_id: int) -> list[dict]:
        return self._call("GET", f"/repos/{repo}/actions/runs/{run_id}/jobs", params={"per_page": 100})[
            "jobs"
        ]

    def job_log(self, repo: str, job_id: int, tail: int = 200) -> str:
        text = self._call("GET", f"/repos/{repo}/actions/jobs/{job_id}/logs")
        lines = str(text).splitlines()
        return "\n".join(lines[-tail:])

    # -- write, on the crew's own branch and the board only ---------------------------------
    def create_branch(self, repo: str, branch: str, from_branch: str) -> str:
        sha = self.branch_sha(repo, from_branch)
        self._call("POST", f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": sha})
        return sha

    def write_file(self, repo: str, branch: str, path: str, content: str, message: str) -> str:
        body: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode(),
            "branch": branch,
        }
        try:
            existing = self.contents(repo, path, branch)
            if isinstance(existing, dict):
                body["sha"] = existing["sha"]
        except RuntimeError as err:
            if "404" not in str(err):
                raise
        return self._call("PUT", f"/repos/{repo}/contents/{path}", json=body)["commit"]["sha"]

    def open_pull_request(self, repo: str, head: str, base: str, title: str, body: str) -> str:
        return self._call(
            "POST", f"/repos/{repo}/pulls", json={"head": head, "base": base, "title": title, "body": body}
        )["html_url"]

    def comment(self, repo: str, number: int, body: str) -> str:
        return self._call("POST", f"/repos/{repo}/issues/{number}/comments", json={"body": body})["html_url"]

    def open_issue(self, repo: str, title: str, body: str, labels: list[str]) -> str:
        return self._call(
            "POST", f"/repos/{repo}/issues", json={"title": title, "body": body, "labels": labels}
        )["html_url"]
