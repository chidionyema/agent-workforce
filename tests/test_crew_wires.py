"""The five roles and four tasks build from the YAML with the tools each role is allowed, nothing more."""

from __future__ import annotations

from pathlib import Path

import pytest

from infra_crew.estate import Estate

pytest.importorskip("crewai")


@pytest.fixture
def est(tmp_path: Path) -> Estate:
    from infra_crew.knowledge import LAW_FILES

    for name in LAW_FILES:
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    placeholders = dict.fromkeys(["router_key", "langfuse_secret_key", "github_token"], "placeholder")
    return Estate(
        router_base_url="http://router.test",
        model="builder-lane",
        verifier_model="verifier-lane",
        embed_model="embed-lane",
        otel_endpoint="http://collector.test",
        langfuse_base_url="http://langfuse.test",
        langfuse_public_key="pk",
        github_api="http://github.test",
        repo_owner="owner",
        laws_dir=tmp_path,
        storage_dir=tmp_path / "store",
        **placeholders,
    )


def test_roles_tools_and_lanes(est: Estate):
    from infra_crew.crew import InfraCrew

    crew = InfraCrew(est)
    names = lambda agent: {t.name for t in agent.tools}  # noqa: E731

    assert "open_pull_request" in names(crew.builder())
    assert "write_file" in names(crew.builder())
    assert names(crew.planner()) == names(crew.verifier())
    assert "write_file" not in names(crew.planner())
    assert names(crew.watcher()) & {"open_incident_issue", "read_deploy_log"} == {
        "open_incident_issue",
        "read_deploy_log",
    }
    assert "write_file" not in names(crew.watcher())
    assert crew.manager().tools == []

    assert crew.verifier().llm.model == "openai/verifier-lane"
    assert crew.builder().llm.model == "openai/builder-lane"
    assert crew.builder().llm.base_url == "http://router.test"


def test_tasks_chain_and_the_build_task_is_guarded(est: Estate):
    from infra_crew.crew import InfraCrew

    crew = InfraCrew(est)
    build = crew.build_task()
    assert build.agent.role == "Builder"
    assert build.guardrail is not None
    assert [t.agent.role for t in (crew.plan_task(), build, crew.verify_task(), crew.report_task())] == [
        "Planner",
        "Builder",
        "Verifier",
        "Builder",
    ]
    assert crew.verify_task().context == [build]
