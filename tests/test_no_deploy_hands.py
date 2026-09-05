"""The crew has no merge, deploy, dispatch, secret, admin or cluster hand. This test is the proof.

Three angles (evidence converges): the route allow-list, the registered tools, and the source
tree itself. A change that adds any hand goes red here before it reaches a pull request.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "agent_workforce"

# Route shapes a crew must never have. Each one is a hand the founder kept for himself.
FORBIDDEN_ROUTE_PARTS = (
    "/merge",  # PUT /repos/{r}/pulls/{n}/merge
    "/dispatches",  # workflow_dispatch and repository_dispatch
    "/actions/secrets",
    "/actions/variables",
    "/actions/runs/",  # re-run, cancel, approve deployments (writes)
    "/deployments",
    "/environments",
    "/hooks",
    "/collaborators",
    "/branches/",  # protection rules
    "/keys",
    "/installations",
    "/app/",
)

# Identifiers no file in the package may use. Strings and comments may mention them (a prompt
# telling the verifier to fail on kubectl is fine); code may not name them, and there is no way
# to run a shell because the modules that could are banned imports.
FORBIDDEN_NAMES = {
    "kubectl",
    "kubeconfig",
    "helm",
    "flux",
    "oci",
    "tofu",
    "terraform",
    "ssh",
    "scp",
    "system",
    "popen",
    "execv",
    "execvp",
    "execve",
    "spawn",
    "spawnv",
    "run_shell",
    "workflow_dispatch",
    "repository_dispatch",
    "merge",
    "deploy",
    "dispatch",
}

FORBIDDEN_IMPORTS = re.compile(
    r"^\s*(import|from)\s+(subprocess|kubernetes|oci|boto3|google\.cloud|paramiko|fabric|hvac|pexpect|pty|shlex)\b",
    re.MULTILINE,
)


def _sources() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.py"))


def _identifiers(path: Path) -> set[str]:
    import io
    import tokenize

    with io.open(path, encoding="utf-8") as handle:
        return {tok.string for tok in tokenize.generate_tokens(handle.readline) if tok.type == tokenize.NAME}


def test_route_allow_list_has_no_forbidden_hand():
    from agent_workforce.tools.github_client import ALLOWED_ROUTES

    for method, path, _ in ALLOWED_ROUTES:
        for part in FORBIDDEN_ROUTE_PARTS:
            if part == "/actions/runs/":
                assert not (method != "GET" and part in path), f"{method} {path} writes to a run"
            else:
                assert part not in path, f"{method} {path} carries the forbidden '{part}'"
        assert method in {"GET", "POST", "PUT"}, (
            f"{method} {path}: DELETE and PATCH are not hands the crew has"
        )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("PUT", "/repos/o/r/pulls/1/merge"),
        ("POST", "/repos/o/r/actions/workflows/deploy.yml/dispatches"),
        ("POST", "/repos/o/r/dispatches"),
        ("POST", "/repos/o/r/actions/runs/1/rerun"),
        ("POST", "/repos/o/r/actions/runs/1/cancel"),
        ("POST", "/repos/o/r/deployments"),
        ("PUT", "/repos/o/r/actions/secrets/X"),
        ("DELETE", "/repos/o/r/git/refs/heads/main"),
        ("PATCH", "/repos/o/r/pulls/1"),
        ("PUT", "/repos/o/r/branches/main/protection"),
    ],
)
def test_client_refuses_forbidden_routes(method: str, path: str):
    from agent_workforce.tools.github_client import GitHub, RouteRefused, route_allowed

    assert not route_allowed(method, path)
    no_token = str(len(path))
    with pytest.raises(RouteRefused):
        GitHub(api="http://unused.invalid", token=no_token)._call(method, path)


def test_registered_tools_carry_no_forbidden_verb():
    from agent_workforce.tools import ALL_TOOLS

    names = {t.name for t in ALL_TOOLS}
    assert names == {
        "read_issue",
        "read_file",
        "list_directory",
        "read_pull_request_checks",
        "read_estate_runs",
        "read_deploy_log",
        "read_job_log",
        "comment_on_issue",
        "create_branch",
        "write_file",
        "open_pull_request",
        "open_incident_issue",
    }, f"the tool list changed: {sorted(names)}; this test is the record of every hand the crew has"
    for t in ALL_TOOLS:
        text = f"{t.name} {t.description}"
        assert not re.search(
            r"\b(merge|deploy|dispatch|apply|rollout|scale|delete)\b", text, re.IGNORECASE
        ), text


def test_no_source_file_names_a_cluster_or_deploy_verb():
    for path in _sources():
        hits = _identifiers(path) & FORBIDDEN_NAMES
        assert not hits, f"{path.relative_to(SRC.parent)} uses {sorted(hits)}"
        imp = FORBIDDEN_IMPORTS.search(path.read_text(encoding="utf-8"))
        assert imp is None, f"{path.relative_to(SRC.parent)}: '{imp.group(0).strip()}'"


def test_no_dependency_gives_a_cluster_hand():
    pyproject = (SRC.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    for bad in ("kubernetes", "oci", "boto3", "paramiko", "hvac", "docker", "ansible"):
        assert not re.search(rf'"{bad}[>=<\[]', pyproject), f"pyproject.toml pulls in {bad}"
