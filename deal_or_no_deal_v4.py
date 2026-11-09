#!/usr/bin/env python3
"""
DEAL OR NO DEAL - Banker Companion  (v3, 16-bit game-show edition)
==================================================================
Play the board game in real life with physical cards / briefcases.
This game is the stage, the board and the Banker.

  1. Click a case to claim YOUR case.
  2. Open real cases in rounds. Click the case you opened, then pick the
     value you found inside - the board strikes it off.
  3. After each round the Banker phones with an offer. DEAL or NO DEAL?
  4. At two cases it's a final offer. No deal = open your own case.

Needs pygame:   pip install pygame      (or: sudo apt install python3-pygame)
Run:            python3 deal_or_no_deal_v3.py

Keys: U = undo, N = new game, M = mute, F11 = fullscreen, Esc = quit.
Edit BOARD / ROUNDS / CURRENCY below to change the game.
"""

import array
import copy
import json
import math
import os
import random
import sys

try:
    import pygame
except ImportError:
    sys.exit("This game needs pygame.  Install it with:  pip install pygame\n"
             "(on Ubuntu you can also use:  sudo apt install python3-pygame)")

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
CURRENCY = "$"
BOARD = [
    (0.5, "blue"), (1, "blue"), (5, "blue"), (10, "blue"), (25, "blue"),
    (50, "blue"), (75, "blue"), (100, "blue"), (250, "blue"), (500, "blue"),
    (750, "blue"),
    (1000, "red"), (2500, "red"), (5000, "red"), (7500, "red"),
    (10000, "red"), (20000, "red"),
    (30000, "green"), (40000, "green"), (50000, "green"), (75000, "green"),
    (100000, "green"),
]
VALUES = [v for v, _ in BOARD]
COLOUR = dict(BOARD)
ROUNDS = [5, 4, 3, 3, 2, 1, 1, 1]     # should add up to len(BOARD) - 2


def fmt(v):
    if v < 1:
        return f"{int(round(v * 100))}c"
    if v != int(v):
        return f"{CURRENCY}{v:,.2f}"
    return f"{CURRENCY}{int(v):,}"


def nice_round(x):
    if x < 10:
        return round(x, 2)
    for limit, step in ((100, 1), (1000, 5), (10000, 50),
                        (100000, 500), (float("inf"), 1000)):
        if x < limit:
            return float(round(x / step) * step)


# --------------------------------------------------------------------------
# Game logic
# --------------------------------------------------------------------------
class Game:
    def __init__(self, values=None, rounds=None):
        self.values = list(values or VALUES)
        self.rounds = list(rounds or ROUNDS)
        self.n = len(self.values)
        self.reset()

    def reset(self):
        self.own = None
        self.opened = {}
        self.round_idx = 0
        self.picks_left = 0
        self.phase = "pick_own"   # pick_own, open, offer, reveal, done
        self.offers = []
        self.final_offer = False
        self.deal_amount = None
        self._history = []

    def remaining_values(self):
        rem = list(self.values)
        for v in self.opened.values():
            rem.remove(v)
        return sorted(rem)

    def unopened_cases(self):
        return [c for c in range(1, self.n + 1) if c not in self.opened]

    def others_unopened(self):
        return [c for c in self.unopened_cases() if c != self.own]

    def _snap(self):
        self._history.append({k: copy.deepcopy(v) for k, v in self.__dict__.items()
                              if k != "_history"})

    def undo(self):
        if self._history:
            state = self._history.pop()
            hist = self._history
            self.__dict__.update(state)
            self._history = hist
            return True
        return False

    def pick_own(self, case):
        self._snap()
        self.own = case
        self._start_round()

    def _start_round(self):
        others = len(self.others_unopened())
        wanted = self.rounds[self.round_idx] if self.round_idx < len(self.rounds) else 1
        self.picks_left = max(1, min(wanted, others - 1))
        self.phase = "open"

    def open_case(self, case, value):
        self._snap()
        self.opened[case] = value
        self.picks_left -= 1
        if self.picks_left == 0:
            self.final_offer = len(self.others_unopened()) == 1
            self.phase = "offer"

    def banker_offer(self):
        rem = self.remaining_values()
        ev = sum(rem) / len(rem)
        progress = len(self.opened) / max(1, self.n - 2)
        factor = 0.12 + 0.80 * progress ** 1.3
        top_heavy = max(rem) / sum(rem)
        factor *= 1 - 0.08 * (top_heavy - 0.5)
        offer = nice_round(ev * factor * random.uniform(0.93, 1.07))
        self._snap()
        self.offers.append(offer)
        return offer

    def deal(self):
        self._snap()
        self.deal_amount = self.offers[-1]
        self.phase = "reveal"

    def no_deal(self):
        self._snap()
        if self.final_offer:
            self.phase = "reveal"
        else:
            self.round_idx += 1
            self._start_round()

    def finish(self, value):
        self._snap()
        self.opened[self.own] = value
        self.phase = "done"


# --------------------------------------------------------------------------
# Pixel font (5x7) and drawing helpers
# --------------------------------------------------------------------------
VW, VH, FPS = 384, 216, 60

WHITE = (250, 250, 255)
BLACK = (6, 4, 10)
GOLD = (255, 214, 64)
AMBER = (255, 168, 20)
GREEN = (60, 230, 90)
REDC = (255, 70, 60)
GREY = (120, 120, 150)

_G = {
    "A": ".###./#...#/#...#/#####/#...#/#...#/#...#",
    "B": "####./#...#/#...#/####./#...#/#...#/####.",
    "C": ".###./#...#/#..../#..../#..../#...#/.###.",
    "D": "####./#...#/#...#/#...#/#...#/#...#/####.",
    "E": "#####/#..../#..../####./#..../#..../#####",
    "F": "#####/#..../#..../####./#..../#..../#....",
    "G": ".###./#...#/#..../#.###/#...#/#...#/.###.",
    "H": "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    "I": ".###./..#../..#../..#../..#../..#../.###.",
    "J": "..###/...#./...#./...#./...#./#..#./.##..",
    "K": "#...#/#..#./#.#../##.../#.#../#..#./#...#",
    "L": "#..../#..../#..../#..../#..../#..../#####",
    "M": "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#",
    "N": "#...#/##..#/#.#.#/#..##/#...#/#...#/#...#",
    "O": ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    "P": "####./#...#/#...#/####./#..../#..../#....",
    "Q": ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    "R": "####./#...#/#...#/####./#.#../#..#./#...#",
    "S": ".####/#..../#..../.###./....#/....#/####.",
    "T": "#####/..#../..#../..#../..#../..#../..#..",
    "U": "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    "V": "#...#/#...#/#...#/#...#/#...#/.#.#./..#..",
    "W": "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#",
    "X": "#...#/#...#/.#.#./..#../.#.#./#...#/#...#",
    "Y": "#...#/#...#/.#.#./..#../..#../..#../..#..",
    "Z": "#####/....#/...#./..#../.#.../#..../#####",
    "0": ".###./#...#/#..##/#.#.#/##..#/#...#/.###.",
    "1": "..#../.##../..#../..#../..#../..#../.###.",
    "2": ".###./#...#/....#/...#./..#../.#.../#####",
    "3": ".###./#...#/....#/..##./....#/#...#/.###.",
    "4": "...#./..##./.#.#./#..#./#####/...#./...#.",
    "5": "#####/#..../####./....#/....#/#...#/.###.",
    "6": "..##./.#.../#..../####./#...#/#...#/.###.",
    "7": "#####/....#/...#./..#../.#.../.#.../.#...",
    "8": ".###./#...#/#...#/.###./#...#/#...#/.###.",
    "9": ".###./#...#/#...#/.####/....#/...#./.##..",
    "$": "..#../.####/#.#../.###./..#.#/####./..#..",
    ",": "...../...../...../...../..##./...#./..#..",
    ".": "...../...../...../...../...../.##../.##..",
    "!": "..#../..#../..#../..#../..#../...../..#..",
    "?": ".###./#...#/....#/...#./..#../...../..#..",
    "'": "..#../..#../...../...../...../...../.....",
    "-": "...../...../...../#####/...../...../.....",
    ":": "...../.##../.##../...../.##../.##../.....",
    "#": ".#.#./.#.#./#####/.#.#./#####/.#.#./.#.#.",
    "/": "....#/....#/...#./..#../.#.../#..../#....",
    "*": "...../#.#.#/.###./#####/.###./#.#.#/.....",
    " ": "...../...../...../...../...../...../.....",
}
GLYPHS = {k: v.split("/") for k, v in _G.items()}
_TC = {}


def tsurf(s, col, sc):
    key = (s, col, sc)
    surf = _TC.get(key)
    if surf is None:
        if len(_TC) > 1500:
            _TC.clear()
        w = max(1, len(s) * 6 - 1)
        surf = pygame.Surface((w * sc, 7 * sc), pygame.SRCALPHA)
        for i, ch in enumerate(s):
            g = GLYPHS.get(ch)
            if not g:
                continue
            for y, row in enumerate(g):
                for x, c in enumerate(row):
                    if c == "#":
                        surf.fill(col, ((i * 6 + x) * sc, y * sc, sc, sc))
        _TC[key] = surf
    return surf


def tw(s, sc=1):
    return max(1, len(s) * 6 - 1) * sc


def text(surf, s, x, y, col=WHITE, sc=1, a="l", sh=None, outline=None):
    s = s.upper()
    w = tw(s, sc)
    if a == "c":
        x -= w // 2
    elif a == "r":
        x -= w
    if outline:
        o = tsurf(s, outline, sc)
        k = max(1, sc // 3)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1),
                       (-1, 1), (1, -1)):
            surf.blit(o, (x + dx * k, y + dy * k))
    if sh:
        surf.blit(tsurf(s, sh, sc), (x + max(1, sc // 2), y + max(1, sc // 2)))
    surf.blit(tsurf(s, col, sc), (x, y))


PLATE = {
    "blue": ((36, 92, 220), (140, 178, 255), (10, 34, 130)),
    "red": ((222, 38, 38), (255, 156, 146), (112, 10, 16)),
    "green": ((30, 172, 62), (150, 255, 160), (8, 92, 32)),
    "gold": ((232, 176, 0), (255, 240, 140), (122, 86, 0)),
    "grey": ((90, 90, 120), (170, 170, 200), (40, 40, 64)),
}


def bevel(s, rect, pal, outline=BLACK):
    x, y, w, h = rect
    base, hi, lo = PLATE[pal] if isinstance(pal, str) else pal
    s.fill(outline, (x - 1, y - 1, w + 2, h + 2))
    s.fill(base, rect)
    s.fill(hi, (x, y, w, 1))
    s.fill(hi, (x, y, 1, h))
    s.fill(lo, (x, y + h - 1, w, 1))
    s.fill(lo, (x + w - 1, y, 1, h))


_SH = {}


def shade(s, rect, col=(0, 0, 0), alpha=128):
    key = (rect[2], rect[3], col, alpha)
    surf = _SH.get(key)
    if surf is None:
        surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        surf.fill((*col, alpha))
        _SH[key] = surf
    s.blit(surf, (rect[0], rect[1]))


def panel(s, rect, border=GOLD, fill=(10, 8, 30)):
    x, y, w, h = rect
    s.fill(BLACK, (x - 1, y - 1, w + 2, h + 2))
    s.fill(border, (x, y, w, h))
    s.fill(fill, (x + 2, y + 2, w - 4, h - 4))
    s.fill((255, 255, 255), (x + 2, y + 2, w - 4, 1))
    s.fill(fill, (x + 2, y + 2, w - 4, 1))


# --------------------------------------------------------------------------
# Procedural sprites and backdrop
# --------------------------------------------------------------------------
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
RAMP = [(10, 4, 2), (46, 20, 4), (92, 42, 6), (146, 74, 8), (204, 116, 12),
        (255, 172, 30)]


def build_backdrop():
    s = pygame.Surface((VW, VH))
    for y in range(VH):
        for x in range(VW):
            if y >= 150:
                lvl = max(0.0, 0.18 - (y - 150) * 0.0025)
            else:
                glow = math.exp(-(((y - 62) / 60.0) ** 2))
                lvl = 0.22 + 0.62 * glow
                lvl *= 0.55 + 0.45 * math.sin(math.pi * x / VW)
                if y % 8 == 7:
                    lvl *= 0.25
                elif x % 4 == 2 and y % 4 == 1:
                    lvl = min(1.0, lvl + 0.30)
                if x % 64 < 3:
                    lvl *= 0.18
            v = lvl * 5
            b = int(v)
            if BAYER[y & 3][x & 3] / 16.0 < v - b:
                b += 1
            s.set_at((x, y), RAMP[min(5, b)])
    return s


FEET = [78, 114, 150, 186]            # feet y of the four rows (back .. front)
ROW_CASES = [[19, 20, 21, 22], [13, 14, 15, 16, 17, 18],
             [7, 8, 9, 10, 11, 12], [1, 2, 3, 4, 5, 6]]
SPACING = 40


def case_pos(n):
    for r, row in enumerate(ROW_CASES):
        if n in row:
            i = row.index(n)
            cx = 192 + (i - (len(row) - 1) / 2.0) * SPACING
            return int(cx), FEET[r]
    raise ValueError(n)


def build_stage(backdrop):
    s = backdrop.copy()
    for f in FEET:
        x0, x1 = 64, 320
        s.fill((255, 226, 90), (x0, f - 1, x1 - x0, 2))
        s.fill((240, 128, 32), (x0, f + 1, x1 - x0, 2))
        s.fill((196, 40, 24), (x0, f + 3, x1 - x0, 4))
        s.fill((84, 14, 14), (x0, f + 7, x1 - x0, 30))
        for yy in range(f + 11, f + 36, 5):
            s.fill((132, 22, 22), (x0, yy, x1 - x0, 1))
        s.fill(BLACK, (x0 - 2, f - 1, 2, 38))
        s.fill(BLACK, (x1, f - 1, 2, 38))
    shade(s, (3, 19, 60, 172), (0, 0, 0), 150)
    shade(s, (321, 19, 60, 172), (0, 0, 0), 150)
    for x in (3, 321):
        pygame.draw.rect(s, (200, 205, 230), (x, 19, 60, 172), 1)
    return s


SKINS = [(250, 206, 170), (232, 170, 120), (186, 120, 70), (120, 74, 42)]
HAIRS = [(40, 26, 18), (110, 62, 28), (236, 200, 96), (168, 60, 28), (16, 14, 18)]
Y1, Y2, Y3 = (250, 214, 28), (200, 158, 12), (255, 244, 130)


def make_model(n):
    rng = random.Random(n * 131 + 7)
    skin = rng.choice(SKINS)
    hair = rng.choice(HAIRS)
    long_hair = rng.random() < 0.75
    hs = tuple(max(0, c - 40) for c in hair)
    sk2 = tuple(max(0, c - 34) for c in skin)
    s = pygame.Surface((18, 34), pygame.SRCALPHA)

    def r(x, y, w, h, c):
        s.fill(c, (x, y, w, h))

    if long_hair:
        r(4, 3, 10, 15, hair)
        r(4, 16, 10, 2, hs)
    else:
        r(5, 3, 8, 7, hair)
    r(6, 4, 6, 7, skin)
    r(5, 5, 8, 5, skin)
    r(5, 3, 8, 2, hair)
    r(5, 4, 1, 3, hair)
    r(12, 4, 1, 3, hair)
    r(7, 7, 1, 1, BLACK)
    r(10, 7, 1, 1, BLACK)
    r(8, 9, 2, 1, (200, 60, 80))
    r(8, 11, 2, 1, sk2)
    r(5, 12, 8, 6, Y1)
    r(5, 12, 1, 6, Y3)
    r(12, 12, 1, 6, Y2)
    r(3, 13, 2, 6, skin)
    r(13, 13, 2, 6, skin)
    r(4, 18, 10, 3, Y1)
    r(3, 21, 12, 2, Y1)
    r(3, 22, 12, 1, Y2)
    r(6, 23, 2, 8, skin)
    r(10, 23, 2, 8, skin)
    r(7, 23, 1, 8, sk2)
    r(11, 23, 1, 8, sk2)
    r(5, 31, 3, 2, (30, 20, 30))
    r(10, 31, 3, 2, (30, 20, 30))
    r(5, 33, 1, 1, (30, 20, 30))
    r(12, 33, 1, 1, (30, 20, 30))
    return s


def draw_phone(s, cx, cy, t, ringing, handset=True):
    pygame.draw.polygon(s, BLACK, [(cx - 24, cy + 11), (cx - 16, cy - 5),
                                   (cx + 16, cy - 5), (cx + 24, cy + 11)])
    pygame.draw.polygon(s, (196, 26, 30), [(cx - 22, cy + 10), (cx - 14, cy - 4),
                                           (cx + 14, cy - 4), (cx + 22, cy + 10)])
    s.fill(BLACK, (cx - 26, cy + 10, 52, 8))
    s.fill((120, 12, 16), (cx - 25, cy + 11, 50, 6))
    pygame.draw.circle(s, BLACK, (cx, cy + 3), 8)
    pygame.draw.circle(s, (236, 226, 200), (cx, cy + 3), 7)
    pygame.draw.circle(s, BLACK, (cx, cy + 3), 3)
    for i in range(8):
        a = i * math.pi / 4
        s.set_at((int(cx + 5 * math.cos(a)), int(cy + 3 + 5 * math.sin(a))), BLACK)
    if handset:
        hop = -1 if (ringing and (t // 3) % 2) else 0
        s.fill(BLACK, (cx - 27, cy - 12 + hop, 54, 9))
        s.fill((214, 30, 34), (cx - 26, cy - 11 + hop, 52, 7))
        s.fill((255, 120, 110), (cx - 24, cy - 11 + hop, 48, 1))
        s.fill((120, 12, 16), (cx - 26, cy - 6 + hop, 52, 2))
        s.fill(BLACK, (cx - 18, cy - 10 + hop, 36, 1))


def draw_banker(s, rect, bg, t, arm_up):
    x, y, w, h = rect
    s.blit(bg, (x, y), (x, y, w, h))
    # make the booth brighter than the stage backdrop
    shade(s, (x, y, w, h), (255, 150, 20), 40)
    clip = s.get_clip()
    s.set_clip(rect)
    cx, by = x + w // 2, y + h
    dark, chair = (4, 2, 3), (36, 14, 6)
    pygame.draw.rect(s, chair, (cx - 27, by - 74, 54, 74), border_radius=10)
    pygame.draw.rect(s, (70, 30, 10), (cx - 27, by - 74, 54, 74), 1, border_radius=10)
    pygame.draw.polygon(s, dark, [(cx - 40, by), (cx - 34, by - 32), (cx - 16, by - 44),
                                  (cx + 16, by - 44), (cx + 34, by - 32), (cx + 40, by)])
    pygame.draw.circle(s, dark, (cx, by - 58), 13)
    s.fill(dark, (cx - 4, by - 48, 8, 6))
    pygame.draw.line(s, dark, (cx - 13, by - 60), (cx - 20, by - 52), 2)
    pygame.draw.line(s, dark, (cx - 20, by - 52), (cx - 12, by - 48), 2)
    if arm_up:
        pygame.draw.line(s, dark, (cx + 34, by - 34), (cx + 22, by - 54), 7)
        pygame.draw.line(s, dark, (cx + 22, by - 54), (cx + 13, by - 60), 6)
        s.fill(dark, (cx + 10, by - 72, 5, 18))
    else:
        pygame.draw.line(s, dark, (cx + 34, by - 34), (cx + 38, by - 16), 7)
        pygame.draw.line(s, dark, (cx + 38, by - 16), (cx + 18, by - 12), 6)
    if (t // 50) % 4 == 0:
        s.set_at((cx - 5, by - 60), (255, 214, 120))
        s.set_at((cx + 4, by - 60), (255, 214, 120))
    s.set_clip(clip)
    pygame.draw.rect(s, BLACK, (x - 3, y - 3, w + 6, h + 6), 1)
    pygame.draw.rect(s, (200, 205, 230), (x - 2, y - 2, w + 4, h + 4), 2)
    pygame.draw.rect(s, (90, 96, 130), (x, y, w, h), 1)


def draw_case_sprite(s, cx, cy, n, openness):
    """Red briefcase. openness 0 closed .. 1 fully open."""
    x, y = cx - 32, cy - 18
    if openness >= 0.25:
        full = openness >= 0.6
        top = y - 24 if full else y - 6
        k = 0 if full else 7
        lid = [(x + 4 - k, y + 9), (x + 60 + k, y + 9), (x + 60, top), (x + 4, top)]
        pygame.draw.polygon(s, (190, 26, 32), lid)
        pygame.draw.polygon(s, BLACK, lid, 1)
        if full:
            s.fill((136, 14, 20), (x + 9, top + 4, 46, 18))
    s.fill(BLACK, (x - 1, y + 7, 66, 32))
    s.fill((150, 16, 22), (x, y + 8, 64, 30))
    s.fill((96, 8, 14), (x, y + 33, 64, 5))
    if openness < 0.25:
        s.fill(BLACK, (x - 1, y - 1, 66, 28))
        s.fill((206, 30, 34), (x, y, 64, 26))
        s.fill((255, 130, 120), (x, y, 64, 2))
        s.fill((130, 12, 18), (x, y + 24, 64, 2))
        s.fill(BLACK, (cx - 8, y - 4, 16, 4))
        s.fill((150, 150, 170), (cx - 7, y - 3, 14, 2))
        s.fill(BLACK, (cx - 17, y + 5, 34, 18))
        s.fill(WHITE, (cx - 16, y + 6, 32, 16))
        text(s, str(n), cx, y + 11, (20, 20, 60), 1, "c")
        s.fill(GOLD, (x + 4, y + 22, 6, 4))
        s.fill(GOLD, (x + 54, y + 22, 6, 4))
    else:
        s.fill((24, 6, 6), (x + 3, y + 10, 58, 14))
        g = int(70 + 170 * openness)
        s.fill((g, g * 2 // 3, 0), (x + 5, y + 11, 54, 12))
        s.fill((255, 240, 170), (x + 12, y + 13, 40, 2))


# --------------------------------------------------------------------------
# Chiptune sound effects (generated at start-up)
# --------------------------------------------------------------------------
def synth(notes, vol=0.28):
    rate = 22050
    buf = array.array("h")
    for note in notes:
        freq, ms = note[0], note[1]
        wave = note[2] if len(note) > 2 else "sq"
        gain = note[3] if len(note) > 3 else 1.0
        n = int(rate * ms / 1000)
        for i in range(n):
            if freq == 0:
                v = 0.0
            elif wave == "noise":
                v = random.uniform(-1, 1)
            else:
                ph = (i * freq / rate) % 1.0
                v = (1.0 if ph < 0.5 else -1.0) if wave == "sq" else 4 * abs(ph - 0.5) - 1
            env = min(1.0, (n - i) / (n * 0.5 + 1))
            buf.append(int(v * env * vol * gain * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def build_sounds():
    s = {}
    s["click"] = synth([(880, 35)])
    s["pick"] = synth([(523, 60), (784, 100)])
    s["open"] = synth([(180, 60, "tri"), (240, 60, "tri"), (320, 70, "tri")])
    s["good"] = synth([(523, 70), (659, 70), (784, 70), (1047, 180)])
    s["bad"] = synth([(392, 100), (330, 100), (262, 120), (196, 340, "tri")])
    s["ring"] = synth([(1300, 30), (950, 30)] * 7 + [(0, 120)], 0.2)
    s["pickup"] = synth([(300, 35), (620, 45)])
    s["drum"] = synth([(0, 1, "noise", 0)] + [(0, 28, "noise", 0.12 + i * 0.026)
                                              for i in range(36)] + [(0, 1)])
    s["lock"] = synth([(988, 50), (1319, 110)])
    s["deal"] = synth([(523, 90), (659, 90), (784, 90), (1047, 90), (784, 70),
                       (1047, 360)])
    s["nodeal"] = synth([(110, 140), (82, 160, "sq", 1.0), (60, 320, "noise", 0.6)])
    s["win"] = synth([(523, 100), (523, 100), (523, 100), (698, 300), (587, 100),
                      (659, 100), (784, 100), (1047, 500)])
    s["sad"] = synth([(392, 220, "tri"), (370, 220, "tri"), (349, 220, "tri"),
                      (330, 600, "tri")])
    return s


# --------------------------------------------------------------------------
# Overlays (each is a little time-based state machine)
# --------------------------------------------------------------------------
class Overlay:
    t = 0

    def update(self, app):
        self.t += 1

    def draw(self, app, s):
        pass

    def click(self, app, pos):
        pass


def button(s, rect, label, pal, sc=1, hover=False, pulse=0):
    x, y, w, h = rect
    if pulse:
        grow = int(1 + math.sin(pulse * 0.2) * 1.2)
        rect = (x - grow, y - grow, w + grow * 2, h + grow * 2)
    bevel(s, rect, pal)
    if hover:
        shade(s, rect, (255, 255, 255), 50)
    x, y, w, h = rect
    text(s, label, x + w // 2, y + (h - 7 * sc) // 2, WHITE, sc, "c", (0, 0, 0))


def hit(rect, pos):
    return pygame.Rect(rect).collidepoint(pos)


class PickerOverlay(Overlay):
    PANEL = (20, 34, 344, 150)

    def __init__(self, app, prompt, values, on_pick, cancellable=True):
        self.prompt, self.on_pick, self.cancellable = prompt, on_pick, cancellable
        self.slots = []
        vals = sorted(values)
        for i, v in enumerate(vals):
            r, c = divmod(i, 6)
            self.slots.append(((26 + c * 56, 76 + r * 17, 52, 13), v))
        rows = (len(vals) + 5) // 6
        cy = 76 + rows * 17 + 6
        self.cancel = (132, cy, 120, 18)
        self.PANEL = (20, 34, 344, cy + (24 if cancellable else 4) - 34)

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (0, 0, 20), 150)
        panel(s, self.PANEL)
        text(s, self.prompt, 192, 44, GOLD, 2, "c", (0, 0, 0))
        text(s, "TAP THE VALUE YOU FOUND INSIDE", 192, 64, GREY, 1, "c")
        for rect, v in self.slots:
            hov = hit(rect, app.mouse)
            x, y, w, h = rect
            bevel(s, rect, PLATE[COLOUR[v]])
            text(s, fmt(v), x + w // 2, y + 3, WHITE, 1, "c", PLATE[COLOUR[v]][2])
            if hov:
                pygame.draw.rect(s, WHITE, (x - 2, y - 2, w + 4, h + 4), 1)
        if self.cancellable:
            button(s, self.cancel, "CANCEL", "grey", 1, hit(self.cancel, app.mouse))

    def click(self, app, pos):
        for rect, v in self.slots:
            if hit(rect, pos):
                app.sfx("pick")
                app.overlay = None
                self.on_pick(v)
                return
        if self.cancellable and hit(self.cancel, pos):
            app.overlay = None


class CaseReveal(Overlay):
    T_IN, T_OPEN, T_FLASH, T_SHOW, T_FLY, END = 24, 44, 46, 128, 128, 160

    def __init__(self, app, n, value, on_done):
        self.n, self.v, self.on_done = n, value, on_done
        self.band = COLOUR[value]
        self.slot = app.slot_rect(value)
        self.big = None

    def update(self, app):
        self.t += 1
        if self.t == self.T_IN:
            app.sfx("open")
        if self.t == self.T_FLASH:
            app.flash = 8
            app.burst(192, 100, 36, [(255, 255, 255), GOLD, AMBER])
            if self.band == "blue":
                app.sfx("good")
            else:
                app.sfx("bad")
                app.shake = 12 if self.band == "green" else 6
        if self.t >= self.END:
            app.overlay = None
            self.on_done()

    def click(self, app, pos):
        if self.t < self.T_FLY:
            self.t = max(self.t, self.T_FLY - 1)

    def plate(self):
        if self.big is None:
            label = fmt(self.v)
            w, h = tw(label, 3) + 16, 31
            surf = pygame.Surface((w, h))
            bevel(surf, (1, 1, w - 2, h - 2), self.band, BLACK)
            text(surf, label, w // 2, 5, WHITE, 3, "c", PLATE[self.band][2])
            self.big = surf
        return self.big

    def draw(self, app, s):
        t = self.t
        shade(s, (0, 0, VW, VH), (0, 0, 20), 170)
        if t < self.T_IN:
            e = t / self.T_IN
            cy = int(260 - (260 - 128) * (1 - (1 - e) ** 2))
            draw_case_sprite(s, 192, cy, self.n, 0)
        elif t < self.T_FLY:
            op = 0 if t < self.T_IN + 4 else min(1.0, (t - self.T_IN) / 20.0)
            draw_case_sprite(s, 192, 128, self.n, op)
        if t >= self.T_FLASH:
            plate = self.plate()
            pw, ph = plate.get_size()
            if t < self.T_FLY:
                e = min(1.0, (t - self.T_FLASH) / 14.0)
                py = int(112 - 46 * e + math.sin(t * 0.15) * 1.5)
                sc = 0.3 + 0.7 * e
                surf = pygame.transform.scale(plate, (max(1, int(pw * sc)), max(1, int(ph * sc))))
                s.blit(surf, (192 - surf.get_width() // 2, py - surf.get_height() // 2))
                if t > self.T_FLASH + 10:
                    word, col = {"blue": ("PHEW!", GREEN), "red": ("OUCH!", AMBER),
                                 "green": ("NOOO!", REDC)}[self.band]
                    text(s, word, 192, 158, col, 3, "c", (0, 0, 0), BLACK)
            else:
                e = (t - self.T_FLY) / float(self.END - self.T_FLY)
                sx, sy, sw, sh = self.slot
                px = 192 + (sx + sw / 2 - 192) * e
                py = 66 + (sy + sh / 2 - 66) * e
                w = max(1, int(pw + (sw - pw) * e))
                h = max(1, int(ph + (sh - ph) * e))
                surf = pygame.transform.scale(plate, (w, h))
                s.blit(surf, (int(px - w / 2), int(py - h / 2)))


class CallOverlay(Overlay):
    WIN = (92, 24, 200, 92)
    PLATE = (62, 120, 260, 46)
    ANSWER = (134, 170, 116, 26)
    DEAL = (74, 174, 108, 28)
    NODEAL = (202, 174, 108, 28)

    def __init__(self, app, offer, final):
        self.offer, self.final = offer, final
        self.stage, self.st = "ring", 0
        self.label = fmt(offer)
        self.digits = [i for i, c in enumerate(self.label) if c.isdigit()]
        self.locked = 0
        app.dim_stage = True
        app.sfx("ring")

    def goto(self, st):
        self.stage, self.st = st, 0

    def update(self, app):
        self.t += 1
        self.st += 1
        if self.stage == "ring":
            if self.st % 80 == 0:
                app.sfx("ring")
        elif self.stage == "answer":
            if self.st == 1:
                app.sfx("pickup")
            if self.st >= 50:
                self.goto("roll")
        elif self.stage == "roll":
            if self.st == 1:
                app.sfx("drum")
            if self.st >= 100 and (self.st - 100) % 16 == 0:
                self.locked += 1
                app.sfx("lock")
                if self.locked >= len(self.digits):
                    self.goto("hold")
        elif self.stage == "hold":
            if self.st == 1:
                app.flash = 6
            if self.st >= 30:
                self.goto("choose")

    def shown(self):
        out = []
        for i, c in enumerate(self.label):
            if c.isdigit() and self.digits.index(i) >= self.locked:
                out.append(str(random.randint(0, 9)))
            else:
                out.append(c)
        return "".join(out)

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (0, 0, 8), 238)
        # spotlight cone
        cone = pygame.Surface((VW, VH), pygame.SRCALPHA)
        pygame.draw.polygon(cone, (255, 190, 80, 26),
                            [(192, 0), (60, VH), (324, VH)])
        s.blit(cone, (0, 0))
        ring = self.stage == "ring"
        if ring:
            if (self.t // 12) % 2 == 0:
                text(s, "THE BANKER IS CALLING", 192, 6, GOLD, 2, "c", BLACK)
            draw_banker(s, self.WIN, app.backdrop, self.t, False)
            s.fill((70, 36, 14), (60, 150, 264, 8))
            s.fill((140, 80, 30), (60, 150, 264, 2))
            draw_phone(s, 192, 142, self.t, True)
            if (self.t // 4) % 2 == 0:
                for sx in (-1, 1):
                    for k, (ox, oy) in enumerate(((36, -6), (42, -12), (48, -18))):
                        pygame.draw.line(s, GOLD, (192 + sx * ox, 142 + oy + 14),
                                         (192 + sx * (ox + 4), 142 + oy + 8), 2)
            button(s, self.ANSWER, "ANSWER", "green", 2, hit(self.ANSWER, app.mouse),
                   self.t)
            return
        text(s, "FINAL OFFER" if self.final else "THE BANKER", 192, 6, GOLD, 2, "c", BLACK)
        draw_banker(s, self.WIN, app.backdrop, self.t, True)
        panel(s, self.PLATE)
        text(s, "THE BANKER OFFERS", 192, 126, GREY, 1, "c")
        label = self.shown() if self.stage in ("roll",) else self.label
        flash_col = WHITE if (self.stage == "hold" and (self.st // 3) % 2 == 0) else GOLD
        text(s, label, 192, 134, flash_col, 3 if tw(label, 4) > 240 else 4, "c", (120, 60, 0))
        if self.stage == "choose":
            button(s, self.DEAL, "DEAL", "green", 2, hit(self.DEAL, app.mouse), self.t)
            button(s, self.NODEAL, "NO DEAL", "red", 2, hit(self.NODEAL, app.mouse),
                   self.t + 15)
        elif self.stage in ("roll", "hold"):
            text(s, "..." if (self.t // 15) % 2 else "", 192, 184, GREY, 2, "c")

    def click(self, app, pos):
        if self.stage == "ring":
            if hit(self.ANSWER, pos) or hit((160, 120, 64, 40), pos):
                app.sfx("click")
                self.goto("answer")
        elif self.stage in ("roll", "hold", "answer"):
            self.locked = len(self.digits)
            self.goto("choose")
        elif self.stage == "choose":
            if hit(self.DEAL, pos):
                app.overlay = DealFx(app, self.offer)
            elif hit(self.NODEAL, pos):
                app.overlay = NoDealFx(app)


class DealFx(Overlay):
    END = 130

    def __init__(self, app, offer):
        self.offer = offer
        app.sfx("deal")

    def update(self, app):
        self.t += 1
        if self.t in (2, 30, 60):
            app.cannons(40)
        if self.t >= self.END:
            app.dim_stage = False
            app.overlay = None
            app.apply_deal()

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (0, 20, 0), 150)
        bounce = int(2 * math.sin(self.t * 0.3))
        sc = min(7, 2 + self.t)
        text(s, "DEAL!", 192, 74 - bounce, GREEN, sc, "c", (0, 70, 20), BLACK)
        if self.t > 25:
            text(s, f"YOU TAKE {fmt(self.offer)}", 192, 150, GOLD, 2, "c", BLACK)


class NoDealFx(Overlay):
    END = 80

    def __init__(self, app):
        app.sfx("nodeal")

    def update(self, app):
        self.t += 1
        if self.t == 8:
            app.shake = 16
            app.flash = 5
        if self.t >= self.END:
            app.dim_stage = False
            app.overlay = None
            app.apply_nodeal()

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (30, 0, 0), 150)
        sc = max(6, 12 - self.t)
        text(s, "NO DEAL!", 192, 108 - 3 * sc, REDC, sc, "c", (90, 0, 0), BLACK)


class ResultOverlay(Overlay):
    BTN1 = (70, 150, 118, 22)
    BTN2 = (196, 150, 118, 22)

    def __init__(self, app, lines, big, good):
        self.lines, self.big, self.good = lines, big, good
        if good:
            app.sfx("win")
            app.cannons(60)
        else:
            app.sfx("sad")

    def update(self, app):
        self.t += 1
        if self.good and self.t % 70 == 0:
            app.cannons(30)

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (0, 0, 20), 150)
        panel(s, (50, 30, 284, 148))
        y = 42
        for ln, col in self.lines:
            text(s, ln, 192, y, col, 1, "c", BLACK)
            y += 12
        text(s, self.big[0], 192, 92, self.big[1], 5 if tw(self.big[0], 5) < 270 else 4,
             "c", (80, 40, 0))
        button(s, self.BTN1, "SAVE SCORE", "green", 1, hit(self.BTN1, app.mouse),
               pulse=self.t if (self.t // 40) % 2 == 0 else 0)
        button(s, self.BTN2, "VIEW BOARD", "blue", 1, hit(self.BTN2, app.mouse))

    def click(self, app, pos):
        if hit(self.BTN1, pos):
            app.overlay = NameOverlay(app)
        elif hit(self.BTN2, pos):
            app.overlay = None


# --------------------------------------------------------------------------
# Scoreboard (cumulative winnings per player name, saved to a JSON file)
# --------------------------------------------------------------------------
SCORE_FILE = os.environ.get("DND_SCORES") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "deal_or_no_deal_scores.json")
NAME_MAX = 10
NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -.'")


def clean_name(n):
    n = " ".join(str(n).upper().split())
    return "".join(c for c in n if c in NAME_CHARS)[:NAME_MAX] or "PLAYER"


class ScoreBoard:
    def __init__(self, path=SCORE_FILE):
        self.path = path
        self.last = "PLAYER"
        self.players = {}
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.last = clean_name(d.get("last", "PLAYER"))
            for k, v in d.get("players", {}).items():
                self.players[clean_name(k)] = {
                    "total": float(v.get("total", 0)),
                    "games": int(v.get("games", 0)),
                    "best": float(v.get("best", 0))}
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"last": self.last, "players": self.players}, f, indent=2)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    def add(self, name, amount):
        name = clean_name(name)
        p = self.players.setdefault(name, {"total": 0.0, "games": 0, "best": 0.0})
        p["total"] += amount
        p["games"] += 1
        p["best"] = max(p["best"], amount)
        self.last = name
        return self.save()

    def ranking(self):
        return sorted(self.players.items(),
                      key=lambda kv: (-kv[1]["total"], -kv[1]["games"], kv[0]))


class NameOverlay(Overlay):
    """Type a name on the keyboard, Enter to save."""
    BTN1 = (96, 138, 90, 20)
    BTN2 = (198, 138, 90, 20)
    keys = True

    def __init__(self, app):
        self.name = app.scores.last
        self.fresh = True

    def key(self, app, key, uni):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.save(app)
        elif key == pygame.K_ESCAPE:
            app.overlay = None
        elif key == pygame.K_BACKSPACE:
            self.name = "" if self.fresh else self.name[:-1]
            self.fresh = False
        elif uni:
            c = uni.upper()
            if c in NAME_CHARS and c != "":
                if self.fresh:
                    self.name = ""
                    self.fresh = False
                if len(self.name) < NAME_MAX:
                    self.name += c
                app.sfx("click")

    def save(self, app):
        name = clean_name(self.name)
        win = app.pending or 0
        app.scores.add(name, win)
        app.pending = None
        app.sfx("pick")
        app.overlay = ScoreOverlay(app, highlight=name, again=True)

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (0, 0, 20), 170)
        panel(s, (64, 40, 256, 128))
        text(s, "ENTER YOUR NAME", 192, 52, GOLD, 2, "c", BLACK)
        text(s, f"WINNINGS: {fmt(app.pending or 0)}", 192, 72, WHITE, 1, "c", BLACK)
        s.fill(BLACK, (84, 88, 216, 30))
        pygame.draw.rect(s, AMBER, (84, 88, 216, 30), 1)
        shown = self.name + ("_" if (self.t // 25) % 2 == 0 and len(self.name) < NAME_MAX else "")
        text(s, shown, 192, 96, GOLD if self.fresh else WHITE, 2, "c", (80, 40, 0))
        text(s, "TYPE A NAME - SCORES ADD UP PER NAME", 192, 124, (170, 170, 200), 1, "c")
        button(s, self.BTN1, "SAVE - ENTER", "green", 1, hit(self.BTN1, app.mouse))
        button(s, self.BTN2, "SKIP - ESC", "blue", 1, hit(self.BTN2, app.mouse))

    def click(self, app, pos):
        if hit(self.BTN1, pos):
            self.save(app)
        elif hit(self.BTN2, pos):
            app.overlay = None


class ScoreOverlay(Overlay):
    BTN1 = (96, 188, 90, 18)
    BTN2 = (198, 188, 90, 18)
    keys = True

    def __init__(self, app, highlight=None, again=False):
        self.highlight, self.again = highlight, again

    def key(self, app, key, uni):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_s):
            self.leave(app)

    def leave(self, app):
        if self.again:
            app.new_game()
        else:
            app.overlay = None

    def draw(self, app, s):
        shade(s, (0, 0, VW, VH), (0, 0, 20), 190)
        panel(s, (40, 8, 304, 206))
        text(s, "HALL OF FAME", 192, 16, GOLD, 2, "c", BLACK)
        text(s, "#", 52, 36, AMBER, 1, "l")
        text(s, "NAME", 70, 36, AMBER, 1, "l")
        text(s, "TOTAL WON", 270, 36, AMBER, 1, "r")
        text(s, "GAMES", 330, 36, AMBER, 1, "r")
        s.fill(AMBER, (50, 45, 284, 1))
        rank = app.scores.ranking()[:8]
        if not rank:
            text(s, "NO SCORES YET - PLAY A GAME!", 192, 100, WHITE, 1, "c")
        for i, (name, p) in enumerate(rank):
            y = 52 + i * 16
            col = GOLD if name == self.highlight else WHITE
            if name == self.highlight:
                shade(s, (48, y - 3, 288, 14), (255, 214, 64), 40)
            text(s, str(i + 1), 52, y, col, 1, "l", BLACK)
            text(s, name, 70, y, col, 1, "l", BLACK)
            text(s, fmt(p["total"]), 270, y, col, 1, "r", BLACK)
            text(s, str(p["games"]), 330, y, col, 1, "r", BLACK)
        if self.again:
            button(s, self.BTN1, "PLAY AGAIN", "green", 1, hit(self.BTN1, app.mouse))
            button(s, self.BTN2, "VIEW BOARD", "blue", 1, hit(self.BTN2, app.mouse))
        else:
            btn = (146, 188, 92, 18)
            button(s, btn, "CLOSE", "blue", 1, hit(btn, app.mouse))

    def click(self, app, pos):
        if self.again:
            if hit(self.BTN1, pos):
                app.new_game()
            elif hit(self.BTN2, pos):
                app.overlay = None
        elif hit((146, 188, 92, 18), pos):
            app.overlay = None


# --------------------------------------------------------------------------
# The app
# --------------------------------------------------------------------------
class App:
    UNDO = (324, 191, 54, 11)
    NEWG = (324, 204, 54, 11)

    def __init__(self, headless=False):
        pygame.init()
        self.sounds = {}
        self.muted = False
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            self.sounds = build_sounds()
        except Exception:
            self.sounds = {}
        pygame.display.set_caption("Deal or No Deal - Banker Companion")
        info = pygame.display.Info()
        scale = 3
        if info.current_w > 0 and info.current_h > 0:
            scale = max(2, int(min(info.current_w * 0.92 // VW, (info.current_h - 90) // VH)))
        self.win = pygame.display.set_mode((VW * scale, VH * scale), pygame.RESIZABLE)
        self.v = pygame.Surface((VW, VH))
        self.g = Game()
        self.scores = ScoreBoard()
        self.pending = None
        self.backdrop = build_backdrop()
        self.stage_bg = build_stage(self.backdrop)
        self.models = {n: make_model(n) for n in range(1, self.g.n + 1)}
        self.slots = {}
        for i, v in enumerate(sorted(self.g.values)):
            col, row = divmod(i, 11)
            self.slots[v] = (6 if col == 0 else 324, 22 + row * 15, 54, 13)
        self.t = 0
        self.mode = "title"
        self.overlay = None
        self.dim_stage = False
        self.sparkles, self.confetti, self.poofs = [], [], []
        self.board_flash = {}
        self.banner = None
        self.shake = 0
        self.flash = 0
        self.delay = None
        self.mouse = (0, 0)
        self.sc, self.off = scale, (0, 0)

    # -- helpers ---------------------------------------------------------
    def sfx(self, name):
        snd = self.sounds.get(name)
        if snd and not self.muted:
            snd.play()

    def slot_rect(self, v):
        return self.slots[v]

    def burst(self, x, y, n, cols):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(0.6, 3.2)
            self.confetti.append([x, y, math.cos(a) * sp, math.sin(a) * sp - 1,
                                  random.choice(cols), 2, 2, random.randint(25, 50), 0.05])

    def cannons(self, n):
        cols = [(255, 60, 60), (60, 200, 255), (255, 230, 60), (90, 255, 120),
                (255, 120, 220), (255, 255, 255)]
        for i in range(n):
            side = i % 2
            x = 0 if side == 0 else VW
            vx = random.uniform(1.5, 4.5) * (1 if side == 0 else -1)
            self.confetti.append([x, VH - 8, vx, random.uniform(-7.5, -3.5),
                                  random.choice(cols), random.choice((2, 3)), 2,
                                  random.randint(90, 150), 0.12])

    def show_banner(self, txt):
        self.banner = [txt, 0]

    def to_v(self, pos):
        return ((pos[0] - self.off[0]) / self.sc, (pos[1] - self.off[1]) / self.sc)

    # -- game flow ----------------------------------------------------------
    def start_game(self):
        self.mode = "stage"
        self.sfx("pick")
        self.show_banner("PICK YOUR CASE!")

    def on_case(self, n):
        g = self.g
        if n in g.opened:
            return
        if g.phase == "pick_own":
            g.pick_own(n)
            x, y = case_pos(n)
            self.burst(x, y - 20, 24, [GOLD, WHITE, AMBER])
            self.sfx("pick")
            self.show_banner(f"ROUND 1: OPEN {g.picks_left}")
        elif g.phase == "open" and n != g.own:
            self.sfx("click")
            self.overlay = PickerOverlay(self, f"CASE {n} CONTAINED...",
                                         g.remaining_values(),
                                         lambda v, n=n: self.begin_reveal(n, v))

    def begin_reveal(self, n, v):
        self.overlay = CaseReveal(self, n, v, lambda: self.after_open(n, v))

    def after_open(self, n, v):
        g = self.g
        g.open_case(n, v)
        x, y = case_pos(n)
        self.poofs.append([x, y - 20, 0])
        self.board_flash[v] = 40
        if g.phase == "offer":
            self.delay = (50, self.banker_call)

    def banker_call(self):
        offer = self.g.banker_offer()
        self.overlay = CallOverlay(self, offer, self.g.final_offer)

    def apply_deal(self):
        self.g.deal()
        self.start_reveal()

    def apply_nodeal(self):
        self.g.no_deal()
        if self.g.phase == "reveal":
            self.start_reveal()
        else:
            n = self.g.picks_left
            self.show_banner(f"ROUND {self.g.round_idx + 1}: OPEN {n}")

    def start_reveal(self):
        g = self.g
        self.overlay = PickerOverlay(
            self, f"OPEN CASE #{g.own}", g.remaining_values(),
            lambda v: self.reveal_own(v), cancellable=False)

    def reveal_own(self, v):
        self.overlay = CaseReveal(self, self.g.own, v, lambda: self.finish(v))

    def finish(self, v):
        g = self.g
        g.finish(v)
        self.board_flash[v] = 40
        self.pending = g.deal_amount if g.deal_amount is not None else v
        if g.deal_amount is not None:
            diff = v - g.deal_amount
            lines = [(f"YOU TOOK {fmt(g.deal_amount)}", GOLD),
                     (f"YOUR CASE HELD {fmt(v)}", WHITE)]
            if diff > 0:
                big, good = ("BAD DEAL!", REDC), False
                lines.append((f"YOU MISSED OUT ON {fmt(diff)}", AMBER))
            elif diff < 0:
                big, good = ("GREAT DEAL!", GREEN), True
                lines.append((f"YOU BEAT THE CASE BY {fmt(-diff)}", GREEN))
            else:
                big, good = ("DEAD EVEN!", GOLD), True
        else:
            lines = [("NO DEAL ALL THE WAY!", GOLD), ("YOU WALK AWAY WITH", WHITE)]
            big, good = (fmt(v), GOLD), v >= 1000
        self.overlay = ResultOverlay(self, lines, big, good)

    def undo(self):
        if self.overlay or self.mode != "stage":
            return
        g = self.g
        if not g.undo():
            return
        while g.phase == "offer" and g.undo():
            pass
        self.sfx("click")
        if g.phase == "reveal":
            self.start_reveal()

    def new_game(self):
        self.g.reset()
        self.pending = None
        self.overlay = None
        self.dim_stage = False
        self.poofs, self.board_flash = [], {}
        self.delay = None
        self.mode = "stage"
        self.show_banner("PICK YOUR CASE!")

    # -- input -----------------------------------------------------------
    def on_click(self, pos):
        if self.overlay:
            self.overlay.click(self, pos)
            return
        if self.mode == "title":
            self.start_game()
            return
        if self.overlay:
            self.overlay.click(self, pos)
            return
        if hit(self.UNDO, pos):
            self.undo()
            return
        if hit(self.NEWG, pos):
            self.new_game()
            return
        if self.g.phase in ("pick_own", "open"):
            for n in range(self.g.n, 0, -1):
                x, y = case_pos(n)
                if hit((x - 9, y - 34, 18, 34), pos):
                    self.on_case(n)
                    return

    def on_key(self, key, uni=""):
        if self.overlay is not None and getattr(self.overlay, "keys", False):
            self.overlay.key(self, key, uni)
            return
        if key == pygame.K_s and (self.mode == "title" or not self.overlay):
            if self.pending is not None and self.mode == "stage":
                self.overlay = NameOverlay(self)
            else:
                self.overlay = ScoreOverlay(self)
            return
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        elif key == pygame.K_m:
            self.muted = not self.muted
        elif key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif key == pygame.K_u:
            self.undo()
        elif key == pygame.K_n and self.mode == "stage" and not self.overlay:
            self.new_game()

    # -- update ----------------------------------------------------------
    def update(self):
        self.t += 1
        self.mouse = self.to_v(pygame.mouse.get_pos())
        if random.random() < 0.35:
            self.sparkles.append([random.randint(4, VW - 4), random.randint(4, 150),
                                  0, random.randint(20, 45)])
        for sp in self.sparkles:
            sp[2] += 1
        self.sparkles = [sp for sp in self.sparkles if sp[2] < sp[3]]
        for c in self.confetti:
            c[0] += c[2]
            c[1] += c[3]
            c[3] += c[8]
            c[7] -= 1
        self.confetti = [c for c in self.confetti if c[7] > 0 and c[1] < VH + 6]
        for p in self.poofs:
            p[2] += 1
        self.poofs = [p for p in self.poofs if p[2] < 24]
        for k in list(self.board_flash):
            self.board_flash[k] -= 1
            if self.board_flash[k] <= 0:
                del self.board_flash[k]
        if self.banner:
            self.banner[1] += 1
            if self.banner[1] > 110:
                self.banner = None
        if self.shake:
            self.shake -= 1
        if self.flash:
            self.flash -= 1
        if self.delay:
            self.delay = (self.delay[0] - 1, self.delay[1])
            if self.delay[0] <= 0:
                fn = self.delay[1]
                self.delay = None
                fn()
        if self.overlay:
            self.overlay.update(self)

    # -- drawing ---------------------------------------------------------
    def draw(self):
        s = self.v
        if self.mode == "title":
            self.draw_title(s)
            if self.overlay:
                self.overlay.draw(self, s)
        else:
            self.draw_stage(s)
            if self.dim_stage:
                pass
            self.draw_banner(s)
            if self.overlay:
                self.overlay.draw(self, s)
        for c in self.confetti:
            s.fill(c[4], (int(c[0]), int(c[1]), c[5], c[6]))
        if self.flash:
            shade(s, (0, 0, VW, VH), (255, 255, 255), min(255, self.flash * 30))

    def present(self):
        ww, wh = self.win.get_size()
        sc = min(ww / VW, wh / VH)
        sc = int(sc) if sc >= 1 else sc
        self.sc = sc
        sw, sh = max(1, int(VW * sc)), max(1, int(VH * sc))
        ox, oy = (ww - sw) // 2, (wh - sh) // 2
        if self.shake:
            ox += random.randint(-2, 2) * max(1, int(sc))
            oy += random.randint(-2, 2) * max(1, int(sc))
        self.off = ((ww - sw) // 2, (wh - sh) // 2)
        self.win.fill((0, 0, 0))
        self.win.blit(pygame.transform.scale(self.v, (sw, sh)), (ox, oy))
        pygame.display.flip()

    def draw_sparkles(self, s):
        for x, y, a, life in self.sparkles:
            col = WHITE if a < life * 0.6 else GOLD
            if a < life * 0.3 or a > life * 0.7:
                s.set_at((x, y), col)
            else:
                s.fill(col, (x - 1, y, 3, 1))
                s.fill(col, (x, y - 1, 1, 3))

    def draw_title(self, s):
        s.blit(self.backdrop, (0, 0))
        self.draw_sparkles(s)
        # parade of numbered models along the bottom
        for n in range(1, 23):
            x = 8 + (n - 1) * 17
            y = 214 - int(abs(math.sin(self.t * 0.07 + n * 0.5)) * 5)
            s.blit(self.models[n], (x, y - 34))
        s.fill((255, 226, 90), (0, 212, VW, 2))
        s.fill((84, 14, 14), (0, 214, VW, 2))
        # logo
        for top in (22, 84):
            pygame.draw.rect(s, GOLD, (58, top, 268, 56))
            s.fill(BLACK, (62, top + 4, 260, 48))
        text(s, "DEAL", 192, 33, WHITE, 5, "c")
        text(s, "NO DEAL", 192, 95, WHITE, 5, "c")
        s.fill(BLACK, (164, 72, 56, 18))
        pygame.draw.rect(s, GOLD, (164, 72, 56, 18), 2)
        text(s, "OR", 192, 77, GOLD, 1, "c")
        text(s, "AUSTRALIAN EDITION", 192, 146, GOLD, 1, "c", BLACK)
        text(s, "BANKER COMPANION", 192, 156, WHITE, 1, "c", BLACK)
        if (self.t // 30) % 2 == 0:
            text(s, "CLICK TO START", 192, 168, AMBER, 2, "c", BLACK)
        text(s, "S = HALL OF FAME", 192, 188, (170, 170, 200), 1, "c", BLACK)

    def draw_stage(self, s):
        g = self.g
        s.blit(self.stage_bg, (0, 0))
        self.draw_sparkles(s)
        # title plate and status LCD
        s.fill(BLACK, (96, 1, 192, 20))
        pygame.draw.rect(s, GOLD, (97, 2, 190, 18), 1)
        text(s, "DEAL OR NO DEAL", 192, 6, WHITE, 2, "c")
        n = g.picks_left
        msgs = {
            "pick_own": "PICK YOUR CASE",
            "open": f"OPEN {n} MORE CASE{'S' if n != 1 else ''}",
            "offer": "THE BANKER IS CALLING...",
            "reveal": "OPEN YOUR CASE!",
            "done": "GAME OVER - PLAY AGAIN?",
        }
        s.fill(BLACK, (100, 23, 184, 12))
        pygame.draw.rect(s, (90, 90, 130), (100, 23, 184, 12), 1)
        flash = g.phase == "pick_own" and (self.t // 25) % 2
        text(s, msgs[g.phase], 192, 26, WHITE if flash else AMBER, 1, "c")
        # boards
        gone = list(g.opened.values())
        for v in sorted(g.values):
            dead = v in gone
            if dead:
                gone.remove(v)
            x, y, w, h = self.slots[v]
            if dead:
                s.fill(BLACK, (x - 1, y - 1, w + 2, h + 2))
                s.fill((14, 12, 26), (x, y, w, h))
                text(s, fmt(v), x + w // 2, y + 3, (52, 50, 84), 1, "c")
                s.fill((52, 50, 84), (x + 4, y + h // 2, w - 8, 1))
            else:
                pal = PLATE[COLOUR[v]]
                bevel(s, (x, y, w, h), pal)
                text(s, fmt(v), x + w // 2, y + 3, WHITE, 1, "c", pal[2])
            if v in self.board_flash:
                shade(s, (x, y, w, h), (255, 255, 255), min(220, self.board_flash[v] * 8))
        # models, back row to front row
        hover = None
        if not self.overlay and g.phase in ("pick_own", "open"):
            for n in range(1, g.n + 1):
                x, y = case_pos(n)
                if n not in g.opened and hit((x - 9, y - 34, 18, 34), self.mouse):
                    hover = n
        for row in ROW_CASES:
            for n in row:
                x, y = case_pos(n)
                if n in g.opened:
                    s.fill(BLACK, (x - 7, y - 7, 14, 8))
                    s.fill((40, 34, 60), (x - 6, y - 6, 12, 6))
                    text(s, str(n), x, y - 5, (110, 100, 140), 1, "c")
                    continue
                bob = 0
                if n == g.own:
                    bob = -1 if (self.t // 10) % 2 else 0
                elif n == hover:
                    bob = -1 if (self.t // 5) % 2 else 0
                elif (self.t // 40 + n * 3) % 17 == 0:
                    bob = -1
                if n == g.own:
                    pulse = 120 + int(80 * math.sin(self.t * 0.15))
                    shade(s, (x - 12, y - 38 + bob, 24, 40), GOLD, pulse // 4)
                s.blit(self.models[n], (x - 9, y - 34 + bob))
                card = (x - 8, y - 16 + bob, 16, 9)
                s.fill(BLACK, (card[0] - 1, card[1] - 1, 18, 11))
                col = (255, 226, 70) if n == g.own else ((255, 250, 170) if n == hover else (246, 246, 255))
                s.fill(col, card)
                text(s, str(n), x, card[1] + 1, (20, 20, 70), 1, "c")
                if n == g.own:
                    text(s, "YOURS", x, y - 46 + bob, GOLD, 1, "c", BLACK)
        for p in self.poofs:
            e = p[2]
            r = 3 + e // 2
            col = WHITE if e < 10 else GOLD
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r), (r - 1, r - 1), (-r + 1, r - 1),
                           (r - 1, -r + 1), (-r + 1, -r + 1)):
                s.fill(col, (p[0] + dx, p[1] + dy, 2, 2))
        # bottom panels
        for rect in ((6, 191, 146, 24), (156, 191, 80, 24), (240, 191, 80, 24)):
            s.fill(BLACK, rect)
            pygame.draw.rect(s, (90, 90, 130), rect, 1)
        text(s, "BANKER OFFERS", 10, 194, GOLD, 1)
        last = g.offers[-2:]
        text(s, "  ".join(fmt(o) for o in last) if last else "NONE YET", 10, 204,
             AMBER if last else GREY, 1)
        text(s, "YOUR CASE", 196, 194, GOLD, 1, "c")
        text(s, f"#{g.own}" if g.own else "?", 196, 204, WHITE, 1, "c")
        rem = g.remaining_values()
        text(s, "AVG LEFT", 280, 194, GOLD, 1, "c")
        text(s, fmt(sum(rem) / len(rem)) if (g.phase != "pick_own" and rem) else "-", 280,
             204, GREEN, 1, "c")
        button(s, self.UNDO, "UNDO", "blue", 1, hit(self.UNDO, self.mouse) and not self.overlay)
        button(s, self.NEWG, "NEW GAME", "red", 1, hit(self.NEWG, self.mouse) and not self.overlay)

    def draw_banner(self, s):
        if not self.banner:
            return
        txt, t = self.banner
        if t < 14:
            x = int(VW + (192 - VW) * (t / 14.0))
        elif t > 96:
            x = int(192 - (t - 96) * 30)
        else:
            x = 192
        w = tw(txt, 2) + 30
        s.fill(BLACK, (x - w // 2 - 2, 96, w + 4, 28))
        s.fill(GOLD, (x - w // 2, 98, w, 24))
        s.fill((20, 14, 50), (x - w // 2 + 2, 100, w - 4, 20))
        text(s, txt, x, 103, WHITE, 2, "c", (0, 0, 0))

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    return
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.on_click(self.to_v(e.pos))
                elif e.type == pygame.KEYDOWN:
                    self.on_key(e.key, e.unicode)
            self.update()
            self.draw()
            self.present()
            clock.tick(FPS)


def main():
    App().run()


if __name__ == "__main__":
    main()
