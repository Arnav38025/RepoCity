"""Tests for repocity rendering: height scales, skyline drama, superlatives."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repocity.analyze import FileStat
from repocity.render import HEIGHT_MAX, HEIGHT_MIN, build_city


def _stats():
    return [
        FileStat(path="src/tiny.py", lines=10, last_commit="2026-10-20"),
        FileStat(path="src/mid.py", lines=1000, last_commit="2026-10-25"),
        FileStat(path="lib/huge.py", lines=100000, last_commit="2026-10-10"),
    ]


def _heights(mode):
    city = build_city(_stats(), height_scale=mode)
    by_path = {b["path"]: b["h"] for b in city["buildings"]}
    return by_path


def test_height_scales_increase_with_lines():
    for mode in ("log", "sqrt", "linear"):
        h = _heights(mode)
        assert h["src/tiny.py"] < h["src/mid.py"] < h["lib/huge.py"], mode


def test_sqrt_tallest_hits_max_height():
    h = _heights("sqrt")
    assert h["lib/huge.py"] == HEIGHT_MAX
    assert h["src/tiny.py"] >= HEIGHT_MIN
    # The skyline is actually dramatic now: the smallest tower is less
    # than a fifth of the tallest, not clustered near it.
    assert h["src/tiny.py"] < HEIGHT_MAX / 5


def test_repo_superlatives():
    city = build_city(_stats())
    assert city["repo"]["tallest"] == {"path": "lib/huge.py", "lines": 100000}
    assert city["repo"]["most_recent"]["path"] == "src/mid.py"
    assert city["repo"]["avg_lines"] == round(101010 / 3, 1)


def test_empty_city():
    city = build_city([])
    assert city["buildings"] == [] and city["districts"] == []
