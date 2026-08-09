from __future__ import annotations

import contextlib
import io
import unittest

import agent_tools.tools.diff_report as diff_report
from agent_tools.tools.diff_report.cli import main as cli_main
from agent_tools.tools.diff_report.core import generate_report
from agent_tools.tools.diff_report.models import DiffReportError


class PublicApiTests(unittest.TestCase):
    def test_package_exports_stable_entrypoints(self) -> None:
        self.assertIs(diff_report.generate_report, generate_report)
        self.assertIs(diff_report.DiffReportError, DiffReportError)
        self.assertIn("generate_report", diff_report.__all__)
        self.assertIn("DiffReportError", diff_report.__all__)
        self.assertIn("main", diff_report.__all__)

    def test_package_main_delegates_to_cli_main(self) -> None:
        cli_stdout = io.StringIO()
        package_stdout = io.StringIO()

        with contextlib.redirect_stdout(cli_stdout):
            cli_status = cli_main(["--help-compact"])
        with contextlib.redirect_stdout(package_stdout):
            package_status = diff_report.main(["--help-compact"])

        self.assertEqual(cli_status, package_status)
        self.assertEqual(cli_stdout.getvalue(), package_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
