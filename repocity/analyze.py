"""Analyze a local checkout into per-file stats.

Everything here runs locally. The only external program used is ``git`` itself
(``git log`` on the repo you point at) -- no network, no tokens, no API keys.
If the directory is not a git repo, or git is missing, recency falls back to
file modification times and commit counts are reported as 0.
"""

from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Directories never walked, even with --include-hidden.
ALWAYS_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
                    ".tox", "dist", "build", ".next", ".cache"}

# File patterns treated as generated/binary even when they look like text.
SKIP_GLOBS = (
    "*.min.js", "*.min.css", "*.map", "*.pyc", "*.pyo",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "*.lock", "*.svg",
)

# Extensions that are almost always binary, even if they decode as text.
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".wav", ".mov", ".avi", ".mkv",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".pdf",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
}


@dataclass
class FileStat:
    """Stats for one file, relative to the repo root."""

    path: str                    # posix-style path, e.g. "src/server.py"
    lines: int                   # non-blank lines of text
    commits: int = 0             # commits touching the file (0 without git)
    last_commit: str | None = None  # ISO date of most recent commit, if known
    mtime: float = 0.0           # fallback recency when git is unavailable

    @property
    def district(self) -> str:
        """Top-level folder; files at the root belong to the '.' district."""
        parts = self.path.split("/")
        return parts[0] if len(parts) > 1 else "."


def _is_binary(path: str) -> bool:
    if os.path.splitext(path)[1].lower() in BINARY_EXTS:
        return True
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(4096)
    except OSError:
        return True


def _count_lines(path: str) -> int | None:
    """Non-blank line count, or None if the file is not readable text."""
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as fh:
            return sum(1 for line in fh if line.strip())
    except (OSError, UnicodeDecodeError):
        return None


def _git_history(root: str) -> dict[str, tuple[int, str]]:
    """Map path -> (commit count, last-commit ISO date) via one git log run.

    Returns {} when git is unavailable or the directory is not a repo.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", root, "log", "--format=COMMIT:%aI", "--name-only",
             "--no-renames"],
            capture_output=True, text=True, timeout=120, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if proc.returncode != 0:
        return {}
    history: dict[str, list[str]] = {}
    current_date: str | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("COMMIT:"):
            current_date = line[len("COMMIT:"):][:10]  # YYYY-MM-DD
        elif line.strip() and current_date:
            history.setdefault(line.strip(), []).append(current_date)
    return {p: (len(dates), max(dates)) for p, dates in history.items()}


def analyze(root: str, max_files: int = 2000, include_hidden: bool = False,
            extra_excludes: tuple[str, ...] = ()) -> list[FileStat]:
    """Walk ``root`` and return stats for its text files, largest first."""
    root = os.path.abspath(root)
    history = _git_history(root)
    stats: list[FileStat] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories in place so os.walk never descends.
        dirnames[:] = [
            d for d in dirnames
            if d not in ALWAYS_SKIP_DIRS
            and (include_hidden or not d.startswith("."))
            and not any(fnmatch.fnmatch(d, pat) for pat in extra_excludes)
        ]
        for name in filenames:
            if not include_hidden and name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, pat) for pat in SKIP_GLOBS + extra_excludes):
                continue
            if _is_binary(full):
                continue
            lines = _count_lines(full)
            if lines is None:
                continue
            commits, last = history.get(rel, (0, None))
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                mtime = 0.0
            stats.append(FileStat(path=rel, lines=lines, commits=commits,
                                  last_commit=last, mtime=mtime))
    stats.sort(key=lambda s: (-s.lines, s.path))
    return stats[:max_files]


def recency_days(stat: FileStat, now: datetime | None = None) -> int | None:
    """Days since the file last changed, from git or (fallback) mtime."""
    now = now or datetime.now(timezone.utc)
    if stat.last_commit:
        try:
            day = datetime.strptime(stat.last_commit, "%Y-%m-%d")
            day = day.replace(tzinfo=timezone.utc)
            return max(0, (now - day).days)
        except ValueError:
            pass
    if stat.mtime:
        return max(0, int((now.timestamp() - stat.mtime) // 86400))
    return None
