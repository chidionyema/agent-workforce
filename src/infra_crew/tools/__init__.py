"""The crew's hands. Every tool is listed here; tests/test_no_deploy_hands.py reads this list.

There is no merge tool, no deploy tool, no workflow-dispatch tool and no cluster tool, and there
never will be: the founder merges and deploys (founder-only releases, 2026-09-01). A crew that
wants one of those has to ask him on the board, in words.
"""

from __future__ import annotations

from infra_crew.tools.board import comment_on_issue, open_incident_issue, read_issue
from infra_crew.tools.estate import read_deploy_log, read_estate_runs, read_job_log
from infra_crew.tools.repo import (
    create_branch,
    list_directory,
    open_pull_request,
    read_file,
    read_pull_request_checks,
    write_file,
)

READ_TOOLS = [
    read_issue,
    read_file,
    list_directory,
    read_pull_request_checks,
    read_estate_runs,
    read_deploy_log,
    read_job_log,
]
WRITE_TOOLS = [comment_on_issue, create_branch, write_file, open_pull_request]
WATCH_TOOLS = [open_incident_issue]

ALL_TOOLS = READ_TOOLS + WRITE_TOOLS + WATCH_TOOLS

__all__ = ["ALL_TOOLS", "READ_TOOLS", "WATCH_TOOLS", "WRITE_TOOLS"]
