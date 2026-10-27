"""Tests for repocity's analyzer and layout. Stdlib only, no network."""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repocity.analyze import analyze, recency_days  # noqa: E402
from repocity.render import build_city  # noqa: E402


def make_repo(files: dict[str, str], commits: int = 1) -> str:
    """Create a temp dir with the given files, committed with git if present."""
    root = tempfile.mkdtemp(prefix="repocity-test-")
    for path, content in files.items():
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
    try:
        subprocess.run(["git", "-C", root, "init", "-q"], check=True)
        subprocess.run(["git", "-C", root, "-c", "user.email=t@t",
                        "-c", "user.name=t", "add", "."], check=True)
        for _ in range(commits):
            subprocess.run(["git", "-C", root, "-c", "user.email=t@t",
                            "-c", "user.name=t", "commit", "-qm", "x"],
                           check=True)
    except (OSError, subprocess.CalledProcessError):
        pass  # git missing: tests still exercise the non-git path
    return root


class TestAnalyze(unittest.TestCase):
    def test_line_counts_skip_blanks_and_binary(self):
        root = make_repo({
            "src/a.py": "x = 1\n\n\ny = 2\n",
            "src/blob.bin": "\x00\x01\x02",
            "node_modules/dep/index.js": "a\n" * 50,
        })
        stats = {s.path: s for s in analyze(root)}
        self.assertEqual(stats["src/a.py"].lines, 2)
        self.assertNotIn("src/blob.bin", stats)
        self.assertNotIn("node_modules/dep/index.js", stats)

    def test_districts_and_git_churn(self):
        root = make_repo({"src/a.py": "a\n" * 10, "docs/b.md": "b\n" * 3},
                         commits=2)
        stats = {s.path: s for s in analyze(root)}
        self.assertEqual(stats["src/a.py"].district, "src")
        self.assertEqual(stats["docs/b.md"].district, "docs")
        # If git worked, both files have 2 commits; otherwise 0 -- either is
        # fine, but the two files must agree.
        self.assertEqual(stats["src/a.py"].commits, stats["docs/b.md"].commits)
        self.assertIsNotNone(recency_days(stats["src/a.py"]))

    def test_max_files_and_order(self):
        files = {f"mod/f{i}.py": "x\n" * i for i in range(1, 8)}
        root = make_repo(files)
        stats = analyze(root, max_files=3)
        self.assertEqual(len(stats), 3)
        self.assertEqual([s.lines for s in stats], [7, 6, 5])


class TestLayout(unittest.TestCase):
    def test_deterministic_city(self):
        root = make_repo({"src/a.py": "a\n" * 40, "src/b.py": "b\n" * 10,
                          "top.py": "t\n" * 5})
        city1 = build_city(analyze(root))
        city2 = build_city(analyze(root))
        self.assertEqual(city1, city2)
        self.assertEqual(city1["repo"]["files"], 3)
        self.assertEqual(city1["repo"]["districts"], 2)
        tallest = max(city1["buildings"], key=lambda b: b["h"])
        self.assertEqual(tallest["path"], "src/a.py")

    def test_empty_repo(self):
        root = tempfile.mkdtemp(prefix="repocity-empty-")
        self.assertEqual(build_city(analyze(root))["buildings"], [])


if __name__ == "__main__":
    unittest.main()
