#!/usr/bin/env python3
"""Highlight unresolved DOCX variable markers and manifest terms in a copy."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

try:
    from .output_path_guard import ensure_external_output
except ImportError:
    from output_path_guard import ensure_external_output


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
VARIABLE_PART = re.compile(
    r"^word/(?:document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml$"
)


def _term_pattern(term: str) -> str:
    escaped = re.escape(term)
    if term and term[0].isalnum():
        escaped = rf"(?<!\w){escaped}"
    if term and term[-1].isalnum():
        escaped = rf"{escaped}(?!\w)"
    if term.upper() == "PUB":
        escaped = rf"{escaped}(?:['’]s)?"
    return escaped


def _matcher(manifest: dict) -> re.Pattern[str]:
    patterns = [manifest.get("marker_regex", r"\{\{[A-Z][A-Z0-9_]*\}\}")]
    patterns.extend(
        str(value) for value in manifest.get("candidate_regexes", []) if str(value)
    )
    terms = sorted(
        {str(value) for value in manifest.get("observed_terms", []) if str(value)},
        key=len,
        reverse=True,
    )
    patterns.extend(_term_pattern(term) for term in terms)
    return re.compile("|".join(f"(?:{pattern})" for pattern in patterns), re.IGNORECASE)


def _highlight_run(run: etree._Element, highlight_name: str) -> None:
    properties = run.find(f"{W}rPr")
    if properties is None:
        properties = etree.Element(f"{W}rPr")
        run.insert(0, properties)
    highlight = properties.find(f"{W}highlight")
    if highlight is None:
        highlight = etree.SubElement(properties, f"{W}highlight")
    highlight.set(f"{W}val", highlight_name)


def _split_and_highlight_run(
    run: etree._Element,
    run_text: str,
    intervals: list[tuple[int, int]],
    highlight_name: str,
) -> None:
    boundaries = {0, len(run_text)}
    for start, end in intervals:
        boundaries.update((start, end))
    points = sorted(boundaries)
    segments = []
    for start, end in zip(points, points[1:]):
        if start == end:
            continue
        highlighted = any(start < match_end and end > match_start for match_start, match_end in intervals)
        segments.append((run_text[start:end], highlighted))

    allowed = {f"{W}rPr", f"{W}t"}
    if any(child.tag not in allowed for child in run):
        _highlight_run(run, highlight_name)
        return
    if len(segments) == 1:
        _highlight_run(run, highlight_name)
        return

    parent = run.getparent()
    index = parent.index(run)
    for text, highlighted in segments:
        clone = copy.deepcopy(run)
        for child in list(clone):
            if child.tag != f"{W}rPr":
                clone.remove(child)
        text_node = etree.SubElement(clone, f"{W}t")
        text_node.text = text
        if text[:1].isspace() or text[-1:].isspace():
            text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        if highlighted:
            _highlight_run(clone, highlight_name)
        parent.insert(index, clone)
        index += 1
    parent.remove(run)


def _flag_xml(data: bytes, matcher: re.Pattern[str], highlight_name: str) -> tuple[bytes, int]:
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(data, parser)
    flagged = 0
    for paragraph in root.iter(f"{W}p"):
        runs = []
        offset = 0
        for run in paragraph.iter(f"{W}r"):
            value = "".join(text_node.text or "" for text_node in run.iter(f"{W}t"))
            if not value:
                continue
            start = offset
            offset += len(value)
            runs.append((start, offset, run, value))
        if not runs:
            continue
        paragraph_text = "".join(value for _, _, _, value in runs)
        matches = list(matcher.finditer(paragraph_text))
        flagged += len(matches)
        for start, end, run, value in runs:
            intervals = [
                (max(match.start(), start) - start, min(match.end(), end) - start)
                for match in matches
                if start < match.end() and end > match.start()
            ]
            if intervals:
                _split_and_highlight_run(run, value, intervals, highlight_name)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), flagged


def flag_docx_variables(
    source: Path | str,
    manifest_path: Path | str,
    output: Path | str,
) -> Path:
    source = Path(source)
    manifest_path = Path(manifest_path)
    output = ensure_external_output(output)
    if source.resolve() == output.resolve():
        raise ValueError("Variable highlighting requires a distinct output path; in-place edits are forbidden")
    if source.suffix.lower() != ".docx" or not source.is_file():
        raise ValueError(f"Source is not a readable DOCX: {source}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matcher = _matcher(manifest)
    highlight_name = str(manifest.get("highlight_name", "yellow"))

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(source) as source_package, zipfile.ZipFile(
            temporary, "w"
        ) as output_package:
            for info in source_package.infolist():
                data = source_package.read(info.filename)
                if VARIABLE_PART.match(info.filename):
                    data, _ = _flag_xml(data, matcher, highlight_name)
                output_package.writestr(info, data)
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(flag_docx_variables(args.source, args.manifest, args.output))


if __name__ == "__main__":
    main()
