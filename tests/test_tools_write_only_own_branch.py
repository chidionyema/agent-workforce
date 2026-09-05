"""The crew writes only on branches named agent-workforce/* and only plain English reaches the board."""

from __future__ import annotations

import pytest

from agent_workforce.tools.board import _plain
from agent_workforce.tools.repo import BRANCH_PREFIX, _own


def test_branch_prefix_is_enforced():
    assert _own(f"{BRANCH_PREFIX}123") == f"{BRANCH_PREFIX}123"
    for bad in ("main", "release", "feat/x", "agent-workforce"):
        with pytest.raises(ValueError):
            _own(bad)


@pytest.mark.parametrize("word", ["in 3 days", "next week", "TODO later", "WIP", "lgtm"])
def test_banned_words_never_reach_a_founder_surface(word: str):
    with pytest.raises(ValueError):
        _plain(f"Built: the thing, {word}.")


def test_plain_english_passes():
    assert _plain("Built: the drill row. Use: merge the pull request.").startswith("Built:")
