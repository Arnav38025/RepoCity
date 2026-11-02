"""Tests for repocity's command line interface."""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repocity import __version__  # noqa: E402
from repocity.cli import main  # noqa: E402


class TestCli(unittest.TestCase):
    def test_version_flag_prints_version_and_exits_zero(self):
        out = io.StringIO()
        with redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), f"repocity {__version__}")


if __name__ == "__main__":
    unittest.main()
