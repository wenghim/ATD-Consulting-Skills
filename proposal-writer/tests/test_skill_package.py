import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_skill_frontmatter_and_identity(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: proposal-writer\n"))
        self.assertIn("description: Use when", text)

    def test_catalog_registers_the_default_proposal_variant(self):
        catalog = json.loads(
            (ROOT / "references" / "master-style-catalog.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(catalog["schema_version"], "1.0")
        self.assertEqual(len(catalog["variants"]), 1)
        self.assertEqual(
            catalog["variants"][0]["variant_id"], "atd-technical-proposal-red"
        )

    def test_openai_yaml_mentions_skill(self):
        text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Proposal Writer"', text)
        self.assertIn("$proposal-writer", text)


if __name__ == "__main__":
    unittest.main()
