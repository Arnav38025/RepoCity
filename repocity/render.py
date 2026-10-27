"""Turn file stats into a city layout and a viewer page (or raw JSON).

Layout is fully deterministic: same repo, same city. Districts are the
top-level folders, sorted by total size; inside a district, buildings are
sorted by size and packed onto a grid, largest first.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict

from .analyze import FileStat, recency_days

# Recency buckets: (max days, color, label). Colors go warm -> cool.
RECENCY_BUCKETS = [
    (7, 0xFFB020, "changed in the last week"),
    (30, 0xFF7A1A, "changed in the last month"),
    (90, 0x2EC4B6, "changed in the last 3 months"),
    (365, 0x3B82F6, "changed in the last year"),
    (float("inf"), 0x64748B, "untouched for over a year"),
]

FOOTPRINT_MIN, FOOTPRINT_MAX = 1.0, 6.0
HEIGHT_MIN, HEIGHT_MAX = 1.0, 42.0  # tall enough for a real skyline
GAP = 1.2  # street width between buildings


def _scale(value: int, lo: int, hi: int, out_lo: float, out_hi: float) -> float:
    """Log scale so one giant file doesn't flatten the whole skyline."""
    if hi <= lo:
        return out_lo
    frac = math.log1p(value - lo) / math.log1p(hi - lo)
    return out_lo + frac * (out_hi - out_lo)


def _height_scale(value: int, max_value: int, mode: str) -> float:
    """Map lines of code to building height.

    sqrt (the default) spreads the skyline out: small files stay low and
    the biggest files become unmistakable towers, instead of everything
    clustering in the middle the way a log scale does. log keeps the old
    compressed look; linear makes height directly proportional to lines.
    """
    if max_value <= 1:
        return HEIGHT_MIN
    if mode == "sqrt":
        frac = math.sqrt(value) / math.sqrt(max_value)
    elif mode == "linear":
        frac = value / max_value
    else:  # "log"
        frac = math.log1p(value - 1) / math.log1p(max_value - 1)
    return HEIGHT_MIN + frac * (HEIGHT_MAX - HEIGHT_MIN)


def _color_for(days: int | None) -> int:
    if days is None:
        return RECENCY_BUCKETS[-1][1]
    for max_days, color, _ in RECENCY_BUCKETS:
        if days <= max_days:
            return color
    return RECENCY_BUCKETS[-1][1]


def _label_for(days: int | None) -> str:
    if days is None:
        return "no history"
    for max_days, _, label in RECENCY_BUCKETS:
        if days <= max_days:
            return label
    return RECENCY_BUCKETS[-1][2]


def build_city(stats: list[FileStat], height_scale: str = "sqrt") -> dict:
    """Build the city data structure from analyzed file stats."""
    if not stats:
        return {"repo": {}, "districts": [], "buildings": []}
    max_lines = max(s.lines for s in stats)
    districts: dict[str, list[FileStat]] = {}
    for stat in stats:
        districts.setdefault(stat.district, []).append(stat)
    # Districts largest-first; files inside each district largest-first.
    ordered = sorted(districts.items(),
                     key=lambda kv: -sum(s.lines for s in kv[1]))

    buildings: list[dict] = []
    district_meta: list[dict] = []
    cursor_x = 0.0
    for name, files in ordered:
        files.sort(key=lambda s: (-s.lines, s.path))
        cols = max(1, math.ceil(math.sqrt(len(files))))
        # District footprint: grid of its largest footprint + streets.
        cell = FOOTPRINT_MAX + GAP
        width = cols * cell
        depth = math.ceil(len(files) / cols) * cell
        district_meta.append({
            "name": name, "x": cursor_x, "z": 0.0,
            "width": width, "depth": depth, "files": len(files),
            "lines": sum(s.lines for s in files),
        })
        for i, stat in enumerate(files):
            col, row = i % cols, i // cols
            footprint = _scale(stat.lines, 1, max_lines,
                               FOOTPRINT_MIN, FOOTPRINT_MAX)
            height = _height_scale(stat.lines, max_lines, height_scale)
            days = recency_days(stat)
            buildings.append({
                "path": stat.path, "district": name,
                "x": cursor_x + col * cell, "z": row * cell,
                "w": round(footprint, 2), "d": round(footprint, 2),
                "h": round(height, 2),
                "lines": stat.lines, "commits": stat.commits,
                "last_commit": stat.last_commit,
                "color": "#%06x" % _color_for(days),
                "recency": _label_for(days),
            })
        cursor_x += width + 8.0  # avenue between districts
    tallest = max(stats, key=lambda s: s.lines)
    dated = [s for s in stats if recency_days(s) is not None]
    most_recent = min(dated, key=recency_days) if dated else None
    return {
        "repo": {
            "files": len(stats),
            "lines": sum(s.lines for s in stats),
            "districts": len(district_meta),
            "avg_lines": round(sum(s.lines for s in stats) / len(stats), 1),
            "tallest": {"path": tallest.path, "lines": tallest.lines},
            "most_recent": (
                {"path": most_recent.path,
                 "last_commit": most_recent.last_commit}
                if most_recent else None
            ),
        },
        "districts": district_meta,
        "buildings": buildings,
    }


def _viewer_template() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "viewer.html"), encoding="utf-8") as fh:
        return fh.read()


def render_html(city: dict, title: str = "repocity") -> str:
    """Fill the viewer template with the city data."""
    template = _viewer_template()
    payload = json.dumps(city, ensure_ascii=False)
    return template.replace("__CITY_DATA__", payload).replace("__TITLE__", title)


def render_json(city: dict) -> str:
    return json.dumps(city, indent=2, ensure_ascii=False)
