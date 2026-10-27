"""Command line interface: repocity <path> [-o output] [--json]."""

from __future__ import annotations

import argparse
import sys

from .analyze import analyze
from .render import build_city, render_html, render_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repocity",
        description="Turn a codebase into an explorable 3D city. "
                    "No API keys, no accounts -- reads a local checkout.",
    )
    parser.add_argument("path", help="Path to a local repository checkout")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file (default: city.html, or city.json with --json)")
    parser.add_argument("--json", action="store_true",
                        help="Emit raw city data as JSON instead of the HTML viewer")
    parser.add_argument("--max-files", type=int, default=2000,
                        help="Only include the N largest files (default: 2000)")
    parser.add_argument("--height-scale", choices=["log", "sqrt", "linear"],
                        default="sqrt",
                        help="How building height maps to lines of code "
                             "(default: sqrt -- a dramatic skyline)")
    parser.add_argument("--include-hidden", action="store_true",
                        help="Include dotfiles and dot-directories")
    parser.add_argument("--no-git", action="store_true",
                        help="Ignore git history; use file modification times")
    parser.add_argument("--exclude", action="append", default=[],
                        help="Skip paths matching GLOB (repeatable)")
    args = parser.parse_args(argv)

    import os
    if not os.path.isdir(args.path):
        print(f"repocity: not a directory: {args.path}", file=sys.stderr)
        return 2

    stats = analyze(args.path, max_files=args.max_files,
                    include_hidden=args.include_hidden,
                    extra_excludes=tuple(args.exclude))
    if args.no_git:
        for stat in stats:
            stat.commits, stat.last_commit = 0, None
    city = build_city(stats, height_scale=args.height_scale)
    output = args.output or ("city.json" if args.json else "city.html")
    text = render_json(city) if args.json else render_html(city)
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"repocity: {city['repo']['files']} files, "
          f"{city['repo']['lines']} lines, "
          f"{city['repo']['districts']} districts -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
