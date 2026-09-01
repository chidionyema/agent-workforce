"""Where the crew finds the estate: every address, name and credential comes from the environment.

Nothing in this repository names a zone, a host, a port, a path on a machine or a key. The values
are injected by the workload's manifest (secrets through the estate's secret store) or, in CI, by
the workflow. A missing value is a refusal at boot with a plain-English line, never a default that
silently points somewhere else.

No prompt text lives here or anywhere in this package; DSPy is not required because the crew
holds no hand-written prompts of its own — agent and task wording sits in config/*.yaml and is
graded by the verifier lane, not tuned by hand.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

EXIT_DARK = 3  # the crew refuses to boot when it cannot be seen


class Dark(RuntimeError):
    """Raised when a value the crew needs to run visibly is missing."""


def _need(name: str, why: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise Dark(f"{name} is not set; it is {why}. The crew refuses to boot dark.")
    return value


def _secret(name: str) -> str:
    """A secret comes from NAME, or from the file named by NAME_FILE (the mounted-secret pattern)."""
    direct = os.environ.get(name, "").strip()
    if direct:
        return direct
    path = os.environ.get(f"{name}_FILE", "").strip()
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8").strip()
    raise Dark(f"{name} (or {name}_FILE) is not set; the crew has no credential and will not guess one.")


@dataclass(frozen=True)
class Estate:
    router_base_url: str  # the one model router; every model call goes through it (LAW 34)
    router_key: str
    model: str  # e.g. "openai/<router alias>" — the router decides the vendor
    verifier_model: str  # a different lane so the verifier never grades with the builder's brain
    embed_model: str
    otel_endpoint: str  # the estate collector (LAW 50)
    langfuse_base_url: str
    langfuse_public_key: str
    langfuse_secret_key: str
    github_api: str
    github_token: str  # an installation token narrowed to the infra-crew lane; never a person's login
    repo_owner: str
    laws_dir: Path  # the checked-out law and standards files the knowledge base is built from
    storage_dir: Path  # crewAI memory and knowledge stores (a volume in the pod)


def load() -> Estate:
    """Read the estate from the environment, or refuse. Called once at boot."""
    return Estate(
        router_base_url=_need("LITELLM_BASE_URL", "the address of the estate's model router"),
        router_key=_secret("LITELLM_API_KEY"),
        model=_need("INFRA_CREW_MODEL", "the router alias the builder and planner use"),
        verifier_model=_need("INFRA_CREW_VERIFIER_MODEL", "the router alias the verifier uses"),
        embed_model=_need("INFRA_CREW_EMBED_MODEL", "the router alias for embeddings"),
        otel_endpoint=_need("OTEL_EXPORTER_OTLP_ENDPOINT", "the estate collector every workload emits to"),
        langfuse_base_url=_need("LANGFUSE_BASE_URL", "the tracing tool the founder reads"),
        langfuse_public_key=_secret("LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=_secret("LANGFUSE_SECRET_KEY"),
        github_api=os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/"),
        github_token=_secret("INFRA_CREW_GITHUB_TOKEN"),
        repo_owner=_need("INFRA_CREW_REPO_OWNER", "the GitHub account that owns the estate repositories"),
        laws_dir=Path(_need("INFRA_CREW_LAWS_DIR", "the directory holding the law and standards files")),
        storage_dir=Path(
            os.environ.get("CREWAI_STORAGE_DIR", "")
            or _need("INFRA_CREW_STORAGE_DIR", "the crew's memory volume")
        ),
    )
