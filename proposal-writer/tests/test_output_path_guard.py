import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document


SKILL_ROOT = Path(__file__).resolve().parents[1]


class OutputPathGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.installed_skill = self.root / "installed" / "proposal-writer"
        self.project = self.root / "project"
        shutil.copytree(SKILL_ROOT / "scripts", self.installed_skill / "scripts")
        self.project.mkdir(parents=True)

        document = Document()
        document.add_paragraph("Prepared for {{CLIENT_NAME}}")
        self.source = self.project / "source.docx"
        document.save(self.source)

        self.profile = self.project / "profile.json"
        self.profile.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "semantic_roles": {},
                    "sections": [],
                    "tables": [],
                    "table_design": {},
                }
            ),
            encoding="utf-8",
        )
        self.manifest = self.project / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "highlight_color": "FFFF00",
                    "highlight_name": "yellow",
                    "marker_regex": r"\{\{[A-Z][A-Z0-9_]*\}\}",
                    "observed_terms": [],
                    "candidate_regexes": [],
                }
            ),
            encoding="utf-8",
        )

    def run_apply(self, output: Path | str, cwd: Path | None = None):
        return subprocess.run(
            [
                sys.executable,
                str(self.installed_skill / "scripts" / "apply_docx_profile.py"),
                str(self.source),
                str(self.profile),
                "--output",
                str(output),
            ],
            cwd=cwd or self.project,
            capture_output=True,
            text=True,
            check=False,
        )

    def run_flag(self, output: Path | str, cwd: Path | None = None):
        return subprocess.run(
            [
                sys.executable,
                str(self.installed_skill / "scripts" / "flag_docx_variables.py"),
                str(self.source),
                str(self.manifest),
                "--output",
                str(output),
            ],
            cwd=cwd or self.project,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_apply_rejects_output_inside_copied_skill(self):
        unsafe_output = self.installed_skill / "unsafe-applied.docx"

        result = self.run_apply(unsafe_output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the skill folder", result.stderr)
        self.assertFalse(unsafe_output.exists())

    def test_flag_rejects_relative_parent_path_that_resolves_inside_skill(self):
        unsafe_output = self.installed_skill / "unsafe-flagged.docx"

        result = self.run_flag(
            Path("..") / unsafe_output.name,
            cwd=self.installed_skill / "scripts",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the skill folder", result.stderr)
        self.assertFalse(unsafe_output.exists())

    def test_apply_allows_external_project_output(self):
        external_output = self.project / "safe-applied.docx"

        result = self.run_apply(external_output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(external_output.exists())

    def test_flag_allows_external_project_output(self):
        external_output = self.project / "safe-flagged.docx"

        result = self.run_flag(external_output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(external_output.exists())


if __name__ == "__main__":
    unittest.main()
