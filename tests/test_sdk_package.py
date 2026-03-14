"""Packaging smoke tests for the Harnessiq SDK."""

from __future__ import annotations

import io
import logging
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from setuptools.build_meta import build_sdist, build_wheel


REPO_ROOT = Path(__file__).resolve().parents[1]


class HarnessiqPackageTests(unittest.TestCase):
    def test_top_level_package_exposes_sdk_modules(self) -> None:
        import harnessiq

        self.assertEqual(harnessiq.__version__, "0.1.0")
        self.assertTrue(hasattr(harnessiq, "agents"))
        self.assertTrue(hasattr(harnessiq, "tools"))
        self.assertTrue(hasattr(harnessiq, "providers"))

    def test_package_builds_wheel_and_sdist_and_imports_from_wheel(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            build_output = io.StringIO()
            previous_disable_level = logging.root.manager.disable
            logging.disable(logging.CRITICAL)
            try:
                with redirect_stdout(build_output), redirect_stderr(build_output):
                    sdist_name = build_sdist(str(temp_path))
                    wheel_name = build_wheel(str(temp_path))
            finally:
                logging.disable(previous_disable_level)
            wheel_path = temp_path / wheel_name

            self.assertTrue((temp_path / sdist_name).exists())
            self.assertTrue(wheel_path.exists())

            smoke = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        f"import sys; sys.path.insert(0, r'{wheel_path}'); "
                        "import harnessiq, harnessiq.agents, harnessiq.tools; "
                        "assert harnessiq.__version__ == '0.1.0'; "
                        "assert hasattr(harnessiq.agents, 'LinkedInJobApplierAgent'); "
                        "assert hasattr(harnessiq.tools, 'create_builtin_registry')"
                    ),
                ],
                check=True,
                cwd=temp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(smoke.returncode, 0)


if __name__ == "__main__":
    unittest.main()
