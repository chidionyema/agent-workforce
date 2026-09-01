"""Entry point: `infra-crew <issue-number>` takes one board ticket to a green pull request.

Order at boot: read the estate (refuse dark), point crewAI's stores at the volume, install the
two trace exporters, check the laws are present, run, then prove the trace landed by querying
Langfuse and printing the answer in the run log.
"""

from __future__ import annotations

import os
import sys
import uuid

import requests

from infra_crew import estate as estate_mod
from infra_crew.estate import EXIT_DARK, Dark


def _langfuse_trace_count(est: estate_mod.Estate, run_id: str) -> int:
    """Ask Langfuse for this run's traces. The number printed in the log is the acceptance receipt."""
    answer = requests.get(
        f"{est.langfuse_base_url.rstrip('/')}/api/public/traces",
        params={"sessionId": run_id, "limit": 1},
        auth=(est.langfuse_public_key, est.langfuse_secret_key),
        timeout=30,
    )
    answer.raise_for_status()
    return int(answer.json().get("meta", {}).get("totalItems", 0))


def run(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or not argv[0].isdigit():
        print("usage: infra-crew <board issue number>", file=sys.stderr)
        return 2
    issue_number = int(argv[0])
    board_repo = os.environ.get("INFRA_CREW_BOARD_REPO", "crew")

    try:
        est = estate_mod.load()
        os.environ.setdefault("CREWAI_STORAGE_DIR", str(est.storage_dir))
        os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")  # the vendor's phone-home, not ours
        run_id = f"infra-crew-{issue_number}-{uuid.uuid4().hex[:8]}"

        from infra_crew import knowledge, observability

        knowledge.law_paths(est.laws_dir)
        provider = observability.install(est, run_id)
    except Dark as why:
        print(f"REFUSED: {why}", file=sys.stderr)
        return EXIT_DARK

    from opentelemetry import trace

    from infra_crew.crew import InfraCrew

    tracer = trace.get_tracer("infra_crew")
    with tracer.start_as_current_span(
        "infra-crew.run",
        attributes={"langfuse.session.id": run_id, "session.id": run_id, "board.issue": issue_number},
    ):
        result = (
            InfraCrew(est).crew().kickoff(inputs={"issue_number": issue_number, "board_repo": board_repo})
        )
    provider.force_flush()
    print(result.raw)

    traces = _langfuse_trace_count(est, run_id)
    print(f"langfuse traces for session {run_id}: {traces}")
    return 0 if traces > 0 else 4


if __name__ == "__main__":
    sys.exit(run())
