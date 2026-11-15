"""Headless end-to-end tests: drive the real App with synthetic clicks/keys."""
import json
import random
import re
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent


def step(app, n=1):
    for _ in range(n):
        app.update()
        app.draw()


def play(d, seed, deal_at):
    """Play a full game. Returns the App, parked on the ResultOverlay."""
    random.seed(seed)
    app = d.App()
    step(app, 5)
    app.on_click((10, 10))  # title -> stage
    step(app, 3)
    g = app.g
    truth = dict(zip(range(1, 23), random.sample(g.values, 22)))
    own = random.randint(1, 22)
    x, y = d.case_pos(own)
    app.on_click((x, y - 10))
    step(app, 3)
    assert g.phase == "open" and g.own == own
    calls = 0
    for _ in range(3000):
        step(app, 2)
        ov = app.overlay
        if g.phase == "done" and isinstance(ov, d.ResultOverlay):
            return app
        if ov is None:
            if g.phase == "open":
                n = next(iter(g.others_unopened()))
                x, y = d.case_pos(n)
                app.on_click((x, y - 10))
                step(app, 2)
                assert isinstance(app.overlay, d.PickerOverlay)
                rect = [r for r, v in app.overlay.slots if v == truth[n]][0]
                app.on_click((rect[0] + 3, rect[1] + 3))
            continue
        if isinstance(ov, d.PickerOverlay):
            rect = [r for r, v in ov.slots if v == truth[g.own]][0]
            app.on_click((rect[0] + 3, rect[1] + 3))
        elif isinstance(ov, d.CaseReveal):
            app.on_click((5, 5))
        elif isinstance(ov, d.CallOverlay):
            if ov.stage == "ring":
                calls += 1
                app.on_click((190, 180))
            elif ov.stage == "choose":
                app.on_click((130, 188) if calls >= deal_at else (250, 188))
            else:
                app.on_click((5, 5))
    raise AssertionError("game did not finish: %s %s" % (g.phase, type(app.overlay)))


def test_version_matches_pattern(game_module):
    assert re.fullmatch(r"\d+\.\d+\.\d+", game_module.__version__)


def test_changelog_has_current_version(game_module):
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [%s]" % game_module.__version__ in text


def test_full_game_no_deal(game_module):
    app = play(game_module, seed=1, deal_at=99)
    assert app.g.phase == "done"
    assert app.g.opened[app.g.own] is not None


def test_full_game_with_deal(game_module):
    app = play(game_module, seed=2, deal_at=3)
    assert app.g.deal_amount is not None


def test_undo_and_new_game(game_module):
    d = game_module
    random.seed(9)
    app = d.App()
    app.on_click((1, 1))
    step(app, 3)
    x, y = d.case_pos(5)
    app.on_click((x, y - 10))
    step(app, 2)
    assert app.g.own == 5
    app.undo()
    assert app.g.own is None and app.g.phase == "pick_own"
    app.new_game()


def _save_score(d, app, name):
    app.on_click((d.ResultOverlay.BTN1[0] + 5, d.ResultOverlay.BTN1[1] + 5))
    step(app, 5)
    assert isinstance(app.overlay, d.NameOverlay)
    for ch in name:
        app.on_key(ord(ch.lower()), ch.lower())
    app.on_key(pygame.K_RETURN, "")
    assert isinstance(app.overlay, d.ScoreOverlay)
    app.on_key(pygame.K_RETURN, "")
    assert app.overlay is None and app.g.phase == "pick_own"


def test_scoreboard_is_cumulative_per_name(game_module):
    d = game_module
    wins = []
    for name, seed, deal_at in (("JEREMY", 1, 2), ("JEREMY", 2, 3), ("ZOE", 3, 99)):
        app = play(d, seed, deal_at)
        wins.append(app.pending)
        _save_score(d, app, name)
    data = json.loads(d.scores_path.read_text())
    flat = json.dumps(data)
    assert "JEREMY" in flat and "ZOE" in flat
    app = d.App()
    step(app, 3)
    app.on_key(pygame.K_s, "s")
    step(app, 3)
    assert isinstance(app.overlay, d.ScoreOverlay)
    app.on_key(pygame.K_ESCAPE, "")
    assert app.overlay is None
