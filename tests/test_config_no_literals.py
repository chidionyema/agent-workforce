"""No file names where the estate lives: no host, zone, home directory, machine or key (LAW 46)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED = [
    *ROOT.joinpath("src").rglob("*"),
    *ROOT.glob("*.toml"),
    *ROOT.glob("Dockerfile"),
    *ROOT.joinpath(".github").rglob("*.yml"),
]

LITERALS = re.compile(
    r"(/Users/|/home/\w|~/|C:\\\\|"
    r"\b\d{1,3}(\.\d{1,3}){3}\b|"  # an IP address
    r"\b(mumchimp\.com|bytesync|\w+\.tail[0-9a-f]+\.ts\.net)\b|"  # estate names
    r"\b(ghp_|github_pat_|sk-|pk-lf-|sk-lf-)[A-Za-z0-9_-]{6,}|"  # token shapes
    r"\blocalhost:\d+|127\.0\.0\.1)"
)


def test_no_estate_literal_in_any_shipped_file():
    hits = []
    for path in SCANNED:
        if not path.is_file() or path.suffix == ".pyc":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if LITERALS.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not hits, "\n".join(hits)
