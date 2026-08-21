import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from tests.docx_fixtures import build_format_fixture


class AnalyzeDocxFormatTests(unittest.TestCase):
    def test_analyzes_structure_without_modifying_source(self):
        from scripts.analyze_docx_format import analyze_docx

        with tempfile.TemporaryDirectory() as temp_dir:
            source = build_format_fixture(Path(temp_dir) / "fixture.docx")
            before = sha256(source.read_bytes()).hexdigest()
            profile = analyze_docx(source, "Fixture Blue")
            after = sha256(source.read_bytes()).hexdigest()

        self.assertEqual(before, after)
        self.assertEqual(profile["identity"]["variant_name"], "Fixture Blue")
        self.assertEqual(profile["identity"]["variant_id"], "fixture-blue")
        self.assertEqual(profile["sections"][0]["orientation"], "portrait")
        self.assertEqual(
            profile["semantic_roles"]["title"]["font"]["size_pt"], 24.0
        )
        self.assertEqual(
            profile["semantic_roles"]["heading_1"]["font"]["size_pt"], 16.0
        )
        self.assertTrue(profile["direct_formatting_exceptions"])
        self.assertEqual(profile["tables"][0]["rows"], 2)
        self.assertEqual(profile["images"][0]["media_type"], "image/png")
        self.assertEqual(
            profile["images"][0]["alt_text"], "Blue rectangular brand sample"
        )
        self.assertTrue(profile["headers_footers"]["headers"])
        self.assertIn("accent1", profile["theme"]["colors"])

    def test_writes_json_and_markdown_profiles(self):
        from scripts.analyze_docx_format import analyze_docx, write_profile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = build_format_fixture(root / "fixture.docx")
            profile = analyze_docx(source, "Fixture Blue")
            json_path, markdown_path = write_profile(profile, root / "profiles")

            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            report = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(loaded["schema_version"], "1.0")
        self.assertIn("# DOCX Format Profile: Fixture Blue", report)
        self.assertIn("## Typography and semantic roles", report)
        self.assertIn("## Images", report)

    def test_rejects_non_docx_input(self):
        from scripts.analyze_docx_format import analyze_docx

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "invalid.docx"
            invalid.write_text("not a zip", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "valid DOCX"):
                analyze_docx(invalid, "Invalid")


if __name__ == "__main__":
    unittest.main()
