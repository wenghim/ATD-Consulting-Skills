#!/usr/bin/env python3
"""Register a DOCX format profile as a preserved named catalog variant."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "variants": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("variants"), list):
        raise ValueError(f"Unsupported or invalid catalog schema in {path}")
    return data


def _summary(profile: dict[str, Any]) -> str:
    roles = profile.get("semantic_roles", {})
    normal = roles.get("normal", {}).get("font", {})
    title = roles.get("title", {}).get("font", {})
    parts = []
    if normal.get("name") or normal.get("size_pt"):
        parts.append(f"Body: {normal.get('name', 'unknown')} {normal.get('size_pt', '?')} pt")
    if title.get("name") or title.get("size_pt"):
        parts.append(f"Title: {title.get('name', 'unknown')} {title.get('size_pt', '?')} pt")
    return "; ".join(parts) or "Profile available; inspect the detailed report."


def _markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Master Style Catalog",
        "",
        "This file is generated from `master-style-catalog.json` by `scripts/update_style_catalog.py`. Treat the JSON catalog as authoritative and do not edit this Markdown file independently.",
        "",
    ]
    variants = catalog.get("variants", [])
    if not variants:
        lines.append("No DOCX format profiles have been registered yet.")
        return "\n".join(lines) + "\n"
    lines.extend(["| Variant | ID | Source | Summary |", "|---|---|---|---|"])
    for item in variants:
        lines.append(
            f"| {item['variant_name']} | `{item['variant_id']}` | "
            f"`{item['source_filename']}` | {item['style_summary']} |"
        )
    return "\n".join(lines) + "\n"


def register_profile(
    profile_path: Path | str,
    catalog_path: Path | str,
    markdown_path: Path | str,
) -> dict[str, Any]:
    profile_path = Path(profile_path)
    catalog_path = Path(catalog_path)
    markdown_path = Path(markdown_path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported profile schema: {profile.get('schema_version')}")
    identity = profile.get("identity")
    required = {
        "variant_id",
        "variant_name",
        "source_filename",
        "source_sha256",
        "analyzed_at",
    }
    if not isinstance(identity, dict) or not required.issubset(identity):
        raise ValueError("Profile identity is missing required fields")

    catalog = _load_catalog(catalog_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        profile_json = str(profile_path.resolve().relative_to(catalog_path.parent.resolve()))
    except ValueError:
        profile_json = str(profile_path.resolve())
    report_candidate = profile_path.with_suffix(".md")
    try:
        profile_markdown = str(report_candidate.resolve().relative_to(catalog_path.parent.resolve()))
    except ValueError:
        profile_markdown = str(report_candidate.resolve())

    entry = {
        "variant_id": identity["variant_id"],
        "variant_name": identity["variant_name"],
        "source_filename": identity["source_filename"],
        "source_sha256": identity["source_sha256"],
        "profile_json": profile_json,
        "profile_markdown": profile_markdown,
        "style_summary": _summary(profile),
        "created_at": now,
        "updated_at": now,
    }

    existing_index = next(
        (
            index
            for index, item in enumerate(catalog["variants"])
            if item.get("variant_id") == identity["variant_id"]
        ),
        None,
    )
    if existing_index is not None:
        existing = catalog["variants"][existing_index]
        if existing.get("source_sha256") != identity["source_sha256"]:
            raise ValueError(
                f"Variant '{identity['variant_id']}' already exists with a different checksum"
            )
        entry["created_at"] = existing.get("created_at", now)
        catalog["variants"][existing_index] = entry
    else:
        catalog["variants"].append(entry)

    _atomic_text(catalog_path, json.dumps(catalog, indent=2, sort_keys=False) + "\n")
    _atomic_text(markdown_path, _markdown(catalog))
    return catalog


def main() -> None:
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=skill_root / "references" / "master-style-catalog.json",
    )
    parser.add_argument(
        "--markdown-catalog",
        type=Path,
        default=skill_root / "references" / "master-style-catalog.md",
    )
    args = parser.parse_args()
    catalog = register_profile(args.profile, args.catalog, args.markdown_catalog)
    print(f"Registered {len(catalog['variants'])} variant(s) in {args.catalog}")


if __name__ == "__main__":
    main()
