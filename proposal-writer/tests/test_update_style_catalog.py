import json
import tempfile
import unittest
from pathlib import Path


def write_profile(path: Path, variant_id: str, variant_name: str, checksum: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "identity": {
                    "variant_id": variant_id,
                    "variant_name": variant_name,
                    "source_filename": f"{variant_id}.docx",
                    "source_sha256": checksum,
                    "analyzed_at": "2026-07-10T00:00:00+00:00",
                },
                "semantic_roles": {
                    "normal": {"font": {"name": "Aptos", "size_pt": 10.5}},
                    "title": {"font": {"name": "Aptos Display", "size_pt": 24.0}},
                },
            }
        ),
        encoding="utf-8",
    )
    return path


class UpdateStyleCatalogTests(unittest.TestCase):
    def test_preserves_named_variants_and_refreshes_same_checksum(self):
        from scripts.update_style_catalog import register_profile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog = root / "catalog.json"
            catalog_md = root / "catalog.md"
            profile_a = write_profile(root / "blue.json", "brand-blue", "Brand Blue", "aaa")
            profile_b = write_profile(root / "green.json", "brand-green", "Brand Green", "bbb")

            register_profile(profile_a, catalog, catalog_md)
            register_profile(profile_b, catalog, catalog_md)
            register_profile(profile_a, catalog, catalog_md)

            data = json.loads(catalog.read_text(encoding="utf-8"))
            report = catalog_md.read_text(encoding="utf-8")

        self.assertEqual(
            [item["variant_id"] for item in data["variants"]],
            ["brand-blue", "brand-green"],
        )
        self.assertEqual(len(data["variants"]), 2)
        self.assertIn("Brand Blue", report)
        self.assertIn("Brand Green", report)

    def test_rejects_same_variant_id_with_different_checksum(self):
        from scripts.update_style_catalog import register_profile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog = root / "catalog.json"
            catalog_md = root / "catalog.md"
            first = write_profile(root / "first.json", "brand-blue", "Brand Blue", "aaa")
            conflict = write_profile(root / "conflict.json", "brand-blue", "Brand Blue", "changed")
            register_profile(first, catalog, catalog_md)

            with self.assertRaisesRegex(ValueError, "different checksum"):
                register_profile(conflict, catalog, catalog_md)

    def test_rejects_unsupported_profile_schema(self):
        from scripts.update_style_catalog import register_profile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "profile.json"
            profile.write_text('{"schema_version":"9.9","identity":{}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema"):
                register_profile(profile, root / "catalog.json", root / "catalog.md")


if __name__ == "__main__":
    unittest.main()
