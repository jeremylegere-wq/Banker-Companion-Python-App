import importlib
import os
import sys

# Headless pygame: must be set before pygame is imported.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture
def game_module(tmp_path, monkeypatch):
    """The game module with its score file redirected to a temp file."""
    scores = tmp_path / "scores.json"
    monkeypatch.setenv("DND_SCORES", str(scores))
    mod = importlib.import_module("deal_or_no_deal_v4")
    mod = importlib.reload(mod)  # SCORE_FILE / ScoreBoard default are bound at import time
    mod.scores_path = scores
    return mod
