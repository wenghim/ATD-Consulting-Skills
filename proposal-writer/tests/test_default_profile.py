import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


class DefaultProfileTests(unittest.TestCase):
    def test_default_profile_points_to_the_sanitized_variant(self):
        default = json.loads(
            (REFERENCES / "default-profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual(default["default_variant_id"], "atd-technical-proposal-red")
        self.assertEqual(
            default["profile_path"],
            "document-profiles/atd-technical-proposal-red.json",
        )
        self.assertEqual(
            default["variable_manifest_path"],
            "variable-manifests/atd-technical-proposal-red.json",
        )

    def test_profile_has_formatting_but_no_source_prose(self):
        profile = json.loads(
            (
                REFERENCES
                / "document-profiles"
                / "atd-technical-proposal-red.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(profile["identity"]["variant_id"], "atd-technical-proposal-red")
        self.assertEqual(profile["semantic_roles"]["normal"]["font"]["name"], "Calibri")
        self.assertEqual(profile["semantic_roles"]["heading_1"]["font"]["color"], "C00000")
        self.assertEqual(profile["table_design"]["header_fill"], "C00000")
        self.assertNotIn("paragraphs", profile)
        self.assertNotIn("direct_formatting_exceptions", profile)
        self.assertNotIn("headers_footers", profile)
        serialized = json.dumps(profile).lower()
        for forbidden in ("executive summary", "scope of work", "about atd"):
            self.assertNotIn(forbidden, serialized)

    def test_variable_manifest_uses_yellow_upper_snake_markers(self):
        manifest = json.loads(
            (
                REFERENCES
                / "variable-manifests"
                / "atd-technical-proposal-red.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["marker_syntax"], "{{UPPER_SNAKE_CASE}}")
        self.assertEqual(manifest["highlight_color"], "FFFF00")
        keys = {item["key"] for item in manifest["variables"]}
        self.assertTrue(
            {
                "CLIENT_SHORT_NAME",
                "CLIENT_LEGAL_NAME",
                "CLIENT_LOGO",
                "DOCUMENT_VERSION",
                "PROJECT_TITLE",
                "PROJECT_DURATION",
                "CONTACT_PERSON",
            }.issubset(keys)
        )
        client = next(
            item for item in manifest["variables"] if item["key"] == "CLIENT_SHORT_NAME"
        )
        self.assertIn("PUB", client["observed_aliases"])

    def test_skill_declares_default_and_variable_safety_workflow(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/default-profile.json", text)
        self.assertIn("{{UPPER_SNAKE_CASE}}", text)
        self.assertIn("yellow", text.lower())
        self.assertIn("requirements", text.lower())
        self.assertIn("company-description", text.lower())


if __name__ == "__main__":
    unittest.main()
