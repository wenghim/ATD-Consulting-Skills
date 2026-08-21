from __future__ import annotations

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def ensure_external_output(
    path: Path | str,
    skill_root: Path | str | None = None,
) -> Path:
    resolved = Path(path).expanduser().resolve()
    root = (
        Path(skill_root).expanduser().resolve()
        if skill_root is not None
        else SKILL_ROOT
    )
    if resolved == root or root in resolved.parents:
        raise ValueError(
            "Generated deliverables must be written outside the skill folder"
        )
    return resolved
