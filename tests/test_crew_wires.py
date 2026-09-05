"""The five roles and four tasks build from the YAML with the tools each role is allowed, nothing more."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_workforce.estate import Estate

pytest.importorskip("crewai")


@pytest.fixture
def est(tmp_path: Path) -> Estate:
    from agent_workforce.knowledge import LAW_FILES

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
    from agent_workforce.crew import AgentWorkforce

    crew = AgentWorkforce(est)
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

    assert crew.verifier().llm.model == "verifier-lane"
    assert crew.builder().llm.model == "builder-lane"
    assert crew.builder().llm.base_url == "http://router.test"


def test_every_lane_is_the_native_openai_client_with_no_litellm(est: Estate, monkeypatch: pytest.MonkeyPatch):
    """The image ships no LiteLLM. A lane crewAI cannot place natively raised ImportError at boot (crew#850)."""
    import crewai.llm as crewai_llm

    from agent_workforce.crew import AgentWorkforce

    monkeypatch.setattr(crewai_llm, "LITELLM_AVAILABLE", False)
    crew = AgentWorkforce(est)
    for lane in (crew.llm, crew.verifier_llm):
        assert lane.provider == "openai"
        assert not lane.is_litellm


def test_tasks_chain_and_the_build_task_is_guarded(est: Estate):
    from agent_workforce.crew import AgentWorkforce

    crew = AgentWorkforce(est)
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


def test_embedder_names_the_router_lane_by_the_key_crewai_reads(est: Estate):
    """crewAI reads model_name; a config carrying only "model" embeds with text-embedding-ada-002 (crew#850)."""
    from crewai.rag.embeddings.providers.openai.types import OpenAIProviderConfig

    from agent_workforce.knowledge import embedder

    cfg = embedder(est)["config"]
    assert set(cfg) <= set(OpenAIProviderConfig.__annotations__), "a key crewAI does not read"
    assert cfg["model_name"] == "embed-lane"
    assert cfg["api_base"] == "http://router.test"
