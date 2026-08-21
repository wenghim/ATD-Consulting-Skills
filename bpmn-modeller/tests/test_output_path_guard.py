import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class OutputPathGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.installed_skill = self.root / "installed" / "bpmn-modeller"
        self.project = self.root / "project"
        shutil.copytree(SKILL_ROOT / "scripts", self.installed_skill / "scripts")
        self.project.mkdir(parents=True)
        self.model_path = self.project / "model.json"
        self.model_path.write_text(
            json.dumps(
                {
                    "process_id": "purchase_approval",
                    "process_name": "Purchase approval",
                    "lanes": [
                        {"id": "requester", "name": "Requester"},
                        {"id": "manager", "name": "Manager"},
                    ],
                    "nodes": [
                        {
                            "id": "start",
                            "type": "startEvent",
                            "name": "Request started",
                            "lane": "requester",
                        },
                        {
                            "id": "submit",
                            "type": "userTask",
                            "name": "Submit request",
                            "lane": "requester",
                        },
                        {
                            "id": "approved",
                            "type": "endEvent",
                            "name": "Request approved",
                            "lane": "manager",
                        },
                    ],
                    "flows": [
                        {"id": "flow_1", "source": "start", "target": "submit"},
                        {
                            "id": "flow_2",
                            "source": "submit",
                            "target": "approved",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

    def run_create(self, output: Path | str, cwd: Path | None = None):
        return subprocess.run(
            [
                sys.executable,
                str(self.installed_skill / "scripts" / "create_bpmn.py"),
                str(self.model_path),
                str(output),
            ],
            cwd=cwd or self.project,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_create_rejects_output_inside_copied_skill(self):
        unsafe_output = self.installed_skill / "unsafe.bpmn"

        result = self.run_create(unsafe_output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the skill folder", result.stderr)
        self.assertFalse(unsafe_output.exists())

    def test_create_rejects_relative_parent_path_that_resolves_inside_skill(self):
        unsafe_output = self.installed_skill / "unsafe-relative.bpmn"

        result = self.run_create(
            Path("..") / unsafe_output.name,
            cwd=self.installed_skill / "scripts",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the skill folder", result.stderr)
        self.assertFalse(unsafe_output.exists())

    def test_create_allows_external_project_output(self):
        external_output = self.project / "safe.bpmn"

        result = self.run_create(external_output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(external_output.exists())

    def test_consolidate_rejects_output_inside_copied_skill(self):
        input_bpmn = self.project / "input.bpmn"
        create_result = self.run_create(input_bpmn)
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        unsafe_output = self.installed_skill / "unsafe-consolidated.bpmn"

        result = subprocess.run(
            [
                sys.executable,
                str(self.installed_skill / "scripts" / "consolidate_bpmn.py"),
                str(unsafe_output),
                str(input_bpmn),
                "--name",
                "Consolidated",
            ],
            cwd=self.project,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the skill folder", result.stderr)
        self.assertFalse(unsafe_output.exists())


if __name__ == "__main__":
    unittest.main()
