"""The crew: five roles, one hierarchical process, the laws as knowledge, a verifier on its own lane."""

from __future__ import annotations

from crewai import LLM, Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tasks.llm_guardrail import LLMGuardrail

from infra_crew import knowledge
from infra_crew.estate import Estate
from infra_crew.tools import READ_TOOLS, WATCH_TOOLS, WRITE_TOOLS

VERIFIER_GUARDRAIL = (
    "The result names a pull request URL and reports check results verbatim. It does not claim a "
    "check is green unless the returned conclusion is 'success'. It contains no merge, deploy, "
    "dispatch, kubectl, flux or cluster action and does not ask the founder to run a script."
)


def router_llm(estate: Estate, alias: str) -> LLM:
    """Every model call goes through the estate router; the alias picks the lane, the router picks the vendor."""
    return LLM(
        model=f"openai/{alias}", base_url=estate.router_base_url, api_key=estate.router_key, temperature=0
    )


@CrewBase
class InfraCrew:
    """Plans, builds and verifies one board ticket to a green pull request, then stops."""

    agents: list[BaseAgent]
    tasks: list[Task]

    def __init__(self, estate: Estate) -> None:
        self.estate = estate
        self.llm = router_llm(estate, estate.model)
        self.verifier_llm = router_llm(estate, estate.verifier_model)
        self.knowledge_sources = knowledge.sources(estate)
        self.embedder = knowledge.embedder(estate)

    def manager(self) -> Agent:
        """The chair. Not an @agent: crewAI keeps the manager out of the worker list."""
        if not hasattr(self, "_manager"):
            self._manager = Agent(
                config=self.agents_config["manager"], llm=self.llm, allow_delegation=True, tools=[]
            )
        return self._manager

    @agent
    def planner(self) -> Agent:
        return Agent(config=self.agents_config["planner"], llm=self.llm, tools=READ_TOOLS + WRITE_TOOLS[:1])

    @agent
    def builder(self) -> Agent:
        return Agent(config=self.agents_config["builder"], llm=self.llm, tools=READ_TOOLS + WRITE_TOOLS)

    @agent
    def verifier(self) -> Agent:
        return Agent(
            config=self.agents_config["verifier"], llm=self.verifier_llm, tools=READ_TOOLS + WRITE_TOOLS[:1]
        )

    @agent
    def watcher(self) -> Agent:
        return Agent(config=self.agents_config["watcher"], llm=self.llm, tools=READ_TOOLS + WATCH_TOOLS)

    @task
    def plan_task(self) -> Task:
        return Task(config=self.tasks_config["plan_task"])

    @task
    def build_task(self) -> Task:
        return Task(
            config=self.tasks_config["build_task"],
            guardrail=LLMGuardrail(description=VERIFIER_GUARDRAIL, llm=self.verifier_llm),
            guardrail_max_retries=2,
        )

    @task
    def verify_task(self) -> Task:
        return Task(config=self.tasks_config["verify_task"])

    @task
    def report_task(self) -> Task:
        return Task(config=self.tasks_config["report_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=self.manager(),
            knowledge_sources=self.knowledge_sources,
            embedder=self.embedder,
            memory=True,
            verbose=True,
        )
