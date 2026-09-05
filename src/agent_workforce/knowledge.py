"""The laws are the crew's knowledge base, not a pasted prompt.

The files are checked out from the estate's own repositories into AGENT_WORKFORCE_LAWS_DIR by the
workload (an init step that clones the crew repository's docs and the founder's law files), and
embedded once through the router's embedding lane. Every task retrieves from them at need, so a
context reset can never lose a ruling.
"""

from __future__ import annotations

from pathlib import Path

from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

from agent_workforce.estate import Dark, Estate

# The names are fixed; the directory is not (LAW 46). Any of them missing is a refusal: a crew
# that cannot read the laws does not get to act.
LAW_FILES = (
    "AGENTS.md",  # the laws, in priority order
    "AGENTS-FULL.md",  # law prose and history
    "STANDARDS.md",  # one row per platform layer
    "definition-of-done.md",  # what DONE means to the founder
)


def law_paths(laws_dir: Path) -> list[Path]:
    missing = [name for name in LAW_FILES if not (laws_dir / name).is_file()]
    if missing:
        raise Dark(
            f"law files missing from {laws_dir}: {', '.join(missing)}. The crew will not act without the laws."
        )
    return [laws_dir / name for name in LAW_FILES]


def sources(estate: Estate) -> list[TextFileKnowledgeSource]:
    # Path objects, not strings: crewAI prefixes a string with its own `knowledge/` directory,
    # which would turn an absolute directory from the environment into a path that does not exist.
    return [TextFileKnowledgeSource(file_paths=law_paths(estate.laws_dir))]


def embedder(estate: Estate) -> dict:
    """Embeddings go through the router too — no vendor key anywhere in this crew."""
    return {
        "provider": "openai",
        "config": {
            "model_name": estate.embed_model,  # crewAI's OpenAI embedder key; "model" is ignored and ada-002 is tried
            "api_key": estate.router_key,
            "api_base": estate.router_base_url,
        },
    }
