"""The estate, read from outside: the deploy log rows and drill runs the founder himself reads.

No kubeconfig, no cluster API, no cloud API. The crew learns what the cluster did from the same
workflow runs the founder is sent, and nothing else.
"""

from __future__ import annotations

import json
import os

from crewai.tools import tool

from infra_crew.tools._client import full, github

PLATFORM_REPO = os.environ.get("INFRA_CREW_PLATFORM_REPO", "idp")
DEPLOY_LOG_WORKFLOW = os.environ.get("INFRA_CREW_DEPLOY_LOG_WORKFLOW", "flux-events.yml")


@tool("read_estate_runs")
def read_estate_runs(workflow_file: str = DEPLOY_LOG_WORKFLOW, limit: int = 10) -> str:
    """List recent runs of an estate workflow in the platform repository (release log, drills, verdicts)."""
    runs = github().workflow_runs(full(PLATFORM_REPO), workflow_file, limit)
    return json.dumps(
        [
            {
                "id": r["id"],
                "name": r.get("display_title") or r["name"],
                "status": r["status"],
                "conclusion": r["conclusion"],
                "started": r["run_started_at"],
                "url": r["html_url"],
            }
            for r in runs
        ],
        indent=1,
    )


@tool("read_deploy_log")
def read_deploy_log(run_id: int) -> str:
    """Read one estate workflow run: every job, its conclusion and its failed steps."""
    gh = github()
    run = gh.run(full(PLATFORM_REPO), run_id)
    jobs = gh.run_jobs(full(PLATFORM_REPO), run_id)
    return json.dumps(
        {
            "url": run["html_url"],
            "status": run["status"],
            "conclusion": run["conclusion"],
            "jobs": [
                {
                    "id": j["id"],
                    "name": j["name"],
                    "conclusion": j["conclusion"],
                    "failed_steps": [
                        s["name"] for s in j.get("steps", []) if s.get("conclusion") == "failure"
                    ],
                }
                for j in jobs
            ],
        },
        indent=1,
    )


@tool("read_job_log")
def read_job_log(job_id: int, tail: int = 200) -> str:
    """Read the last lines of one job's log from an estate workflow run."""
    return github().job_log(full(PLATFORM_REPO), job_id, tail)
