"""The crew refuses to boot when it cannot be seen or has no credential. Never a silent default."""

from __future__ import annotations

import pytest

from infra_crew import estate
from infra_crew.estate import EXIT_DARK, Dark

FULL_ENV = {
    "LITELLM_BASE_URL": "http://router.test",
    "LITELLM_API_KEY": "k",
    "INFRA_CREW_MODEL": "m",
    "INFRA_CREW_VERIFIER_MODEL": "v",
    "INFRA_CREW_EMBED_MODEL": "e",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector.test",
    "LANGFUSE_BASE_URL": "http://langfuse.test",
    "LANGFUSE_PUBLIC_KEY": "pk",
    "LANGFUSE_SECRET_KEY": "sk",
    "INFRA_CREW_GITHUB_TOKEN": "t",
    "INFRA_CREW_REPO_OWNER": "owner",
    "INFRA_CREW_LAWS_DIR": "/laws",
    "INFRA_CREW_STORAGE_DIR": "/store",
}


def _set(monkeypatch, env: dict[str, str]) -> None:
    for key in FULL_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("CREWAI_STORAGE_DIR", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_full_environment_loads(monkeypatch):
    _set(monkeypatch, FULL_ENV)
    est = estate.load()
    assert est.router_base_url == "http://router.test"
    expected = FULL_ENV["INFRA_CREW_GITHUB_TOKEN"]
    assert est.github_token == expected


@pytest.mark.parametrize("missing", sorted(FULL_ENV))
def test_each_missing_value_refuses(monkeypatch, missing: str):
    env = dict(FULL_ENV)
    del env[missing]
    _set(monkeypatch, env)
    with pytest.raises(Dark) as why:
        estate.load()
    assert missing in str(why.value)


def test_secret_may_come_from_a_mounted_file(monkeypatch, tmp_path):
    env = dict(FULL_ENV)
    del env["INFRA_CREW_GITHUB_TOKEN"]
    secret = tmp_path / "token"
    secret.write_text("from-file\n", encoding="utf-8")
    _set(monkeypatch, env)
    monkeypatch.setenv("INFRA_CREW_GITHUB_TOKEN_FILE", str(secret))
    expected = secret.read_text(encoding="utf-8").strip()
    assert estate.load().github_token == expected


def test_main_exits_dark_without_an_estate(monkeypatch, capsys):
    from infra_crew import main

    _set(monkeypatch, {})
    assert main.run(["42"]) == EXIT_DARK
    assert "REFUSED:" in capsys.readouterr().err


def test_main_refuses_without_the_laws(monkeypatch, tmp_path, capsys):
    from infra_crew import main

    # crewAI creates the storage directory the moment it is imported, so the store must be a
    # real writable path here; the laws directory is empty on purpose.
    env = dict(
        FULL_ENV,
        INFRA_CREW_LAWS_DIR=str(tmp_path / "laws"),
        INFRA_CREW_STORAGE_DIR=str(tmp_path / "store"),
    )
    (tmp_path / "laws").mkdir()
    _set(monkeypatch, env)
    assert main.run(["42"]) == EXIT_DARK
    assert "law files missing" in capsys.readouterr().err
