#!/usr/bin/env python3
"""Extract a deterministic, read-only DOCX format profile."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SCHEMA_VERSION = "1.0"
ANALYZER_VERSION = "1.0.0"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


def qn(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unnamed-profile"


def _xml(package: zipfile.ZipFile, part: str) -> ET.Element | None:
    try:
        return ET.fromstring(package.read(part))
    except KeyError:
        return None


def _value(element: ET.Element | None, prefix: str = "w", name: str = "val") -> str | None:
    if element is None:
        return None
    return element.get(qn(prefix, name))


def _bool_prop(parent: ET.Element | None, tag: str) -> bool | None:
    if parent is None:
        return None
    element = parent.find(f"w:{tag}", NS)
    if element is None:
        return None
    value = _value(element)
    return value not in {"0", "false", "off", "none"}


def _float(value: str | None, divisor: float = 1.0) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) / divisor, 4)
    except ValueError:
        return None


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        elif value is not None:
            result[key] = deepcopy(value)
    return result


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None and item != {}}


def _theme(package: zipfile.ZipFile) -> dict[str, Any]:
    root = _xml(package, "word/theme/theme1.xml")
    result: dict[str, Any] = {"fonts": {"major": {}, "minor": {}}, "colors": {}}
    if root is None:
        return result

    font_scheme = root.find(".//a:fontScheme", NS)
    if font_scheme is not None:
        for group_name, tag in (("major", "majorFont"), ("minor", "minorFont")):
            group = font_scheme.find(f"a:{tag}", NS)
            if group is None:
                continue
            latin = group.find("a:latin", NS)
            east_asia = group.find("a:ea", NS)
            complex_script = group.find("a:cs", NS)
            result["fonts"][group_name] = {
                "latin": latin.get("typeface") if latin is not None else None,
                "east_asia": east_asia.get("typeface") if east_asia is not None else None,
                "complex_script": complex_script.get("typeface") if complex_script is not None else None,
            }

    color_scheme = root.find(".//a:clrScheme", NS)
    if color_scheme is not None:
        for slot in list(color_scheme):
            name = slot.tag.rsplit("}", 1)[-1]
            color = next(iter(slot), None)
            if color is None:
                continue
            result["colors"][name] = color.get("val") or color.get("lastClr")
    return result


def _resolve_theme_font(theme_key: str | None, theme: dict[str, Any]) -> str | None:
    if not theme_key:
        return None
    group = "major" if theme_key.lower().startswith("major") else "minor"
    script = "east_asia" if theme_key.lower().endswith("eastasia") else "complex_script" if theme_key.lower().endswith("bidi") else "latin"
    return theme.get("fonts", {}).get(group, {}).get(script)


def _font(rpr: ET.Element | None, theme: dict[str, Any]) -> dict[str, Any]:
    if rpr is None:
        return {}
    rfonts = rpr.find("w:rFonts", NS)
    explicit_name = None
    theme_font = None
    if rfonts is not None:
        explicit_name = rfonts.get(qn("w", "ascii")) or rfonts.get(qn("w", "hAnsi"))
        theme_font = rfonts.get(qn("w", "asciiTheme")) or rfonts.get(qn("w", "hAnsiTheme"))
    size = _float(_value(rpr.find("w:sz", NS)), 2)
    color_el = rpr.find("w:color", NS)
    underline_el = rpr.find("w:u", NS)
    lang = rpr.find("w:lang", NS)
    return _compact(
        {
            "name": explicit_name or _resolve_theme_font(theme_font, theme),
            "size_pt": size,
            "bold": _bool_prop(rpr, "b"),
            "italic": _bool_prop(rpr, "i"),
            "underline": (
                _value(underline_el) not in {None, "none", "0", "false"}
                if underline_el is not None
                else None
            ),
            "caps": _bool_prop(rpr, "caps"),
            "small_caps": _bool_prop(rpr, "smallCaps"),
            "color": _value(color_el),
            "theme_font": theme_font,
            "theme_color": color_el.get(qn("w", "themeColor")) if color_el is not None else None,
            "language": _value(lang),
        }
    )


def _paragraph_format(ppr: ET.Element | None) -> dict[str, Any]:
    if ppr is None:
        return {}
    spacing = ppr.find("w:spacing", NS)
    ind = ppr.find("w:ind", NS)
    shading = ppr.find("w:shd", NS)
    borders = ppr.find("w:pBdr", NS)
    outline = ppr.find("w:outlineLvl", NS)
    return _compact(
        {
            "alignment": _value(ppr.find("w:jc", NS)),
            "space_before_pt": _float(spacing.get(qn("w", "before")) if spacing is not None else None, 20),
            "space_after_pt": _float(spacing.get(qn("w", "after")) if spacing is not None else None, 20),
            "line_raw": spacing.get(qn("w", "line")) if spacing is not None else None,
            "line_rule": spacing.get(qn("w", "lineRule")) if spacing is not None else None,
            "left_indent_pt": _float(ind.get(qn("w", "left")) if ind is not None else None, 20),
            "right_indent_pt": _float(ind.get(qn("w", "right")) if ind is not None else None, 20),
            "first_line_indent_pt": _float(ind.get(qn("w", "firstLine")) if ind is not None else None, 20),
            "hanging_indent_pt": _float(ind.get(qn("w", "hanging")) if ind is not None else None, 20),
            "keep_next": _bool_prop(ppr, "keepNext"),
            "keep_lines": _bool_prop(ppr, "keepLines"),
            "page_break_before": _bool_prop(ppr, "pageBreakBefore"),
            "outline_level": int(_value(outline)) if _value(outline) is not None else None,
            "shading_fill": shading.get(qn("w", "fill")) if shading is not None else None,
            "borders": _element_attributes(borders),
        }
    )


def _element_attributes(element: ET.Element | None) -> dict[str, Any]:
    if element is None:
        return {}
    result: dict[str, Any] = {}
    for child in list(element):
        name = child.tag.rsplit("}", 1)[-1]
        result[name] = {key.rsplit("}", 1)[-1]: value for key, value in child.attrib.items()}
    return result


def _styles(package: zipfile.ZipFile, theme: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    root = _xml(package, "word/styles.xml")
    declared: dict[str, Any] = {}
    if root is None:
        return declared, declared
    for style in root.findall("w:style", NS):
        style_id = style.get(qn("w", "styleId"))
        if not style_id:
            continue
        declared[style_id] = {
            "style_id": style_id,
            "type": style.get(qn("w", "type")),
            "name": _value(style.find("w:name", NS)) or style_id,
            "based_on": _value(style.find("w:basedOn", NS)),
            "next_style": _value(style.find("w:next", NS)),
            "font": _font(style.find("w:rPr", NS), theme),
            "paragraph": _paragraph_format(style.find("w:pPr", NS)),
        }

    resolved: dict[str, Any] = {}

    def resolve(style_id: str, active: set[str] | None = None) -> dict[str, Any]:
        if style_id in resolved:
            return resolved[style_id]
        active = set() if active is None else active
        if style_id in active or style_id not in declared:
            return {}
        active.add(style_id)
        item = declared[style_id]
        base = resolve(item.get("based_on"), active) if item.get("based_on") else {}
        result = _merge(base, item)
        result["declared_font"] = item.get("font", {})
        result["declared_paragraph"] = item.get("paragraph", {})
        active.remove(style_id)
        resolved[style_id] = result
        return result

    for style_id in declared:
        resolve(style_id)
    return declared, resolved


ROLE_STYLES = {
    "normal": {"normal", "body text", "bodytext"},
    "title": {"title"},
    "subtitle": {"subtitle"},
    "heading_1": {"heading 1", "heading1"},
    "heading_2": {"heading 2", "heading2"},
    "heading_3": {"heading 3", "heading3"},
    "quote": {"quote", "intense quote"},
    "caption": {"caption"},
    "list_bullet": {"list bullet", "listbullet"},
    "list_number": {"list number", "listnumber"},
    "header": {"header"},
    "footer": {"footer"},
}


def _role_for(style_id: str | None, style: dict[str, Any], text: str, index: int) -> dict[str, Any]:
    candidates = {str(style_id or "").lower(), str(style.get("name", "")).lower()}
    for role, names in ROLE_STYLES.items():
        if candidates & names:
            return {"role": role, "confidence": 1.0, "evidence": "explicit Word style"}
    outline = style.get("paragraph", {}).get("outline_level")
    if isinstance(outline, int) and 0 <= outline <= 2:
        return {"role": f"heading_{outline + 1}", "confidence": 0.9, "evidence": "outline level"}
    font = style.get("font", {})
    if index == 0 and text and font.get("size_pt", 0) >= 20:
        return {"role": "title", "confidence": 0.65, "evidence": "first paragraph and large type"}
    return {"role": "normal", "confidence": 0.55, "evidence": "fallback body-text heuristic"}


def _relationships(package: zipfile.ZipFile, part: str) -> dict[str, dict[str, str]]:
    if "/" in part:
        directory, filename = part.rsplit("/", 1)
        rel_part = f"{directory}/_rels/{filename}.rels"
    else:
        rel_part = f"_rels/{part}.rels"
    root = _xml(package, rel_part)
    result: dict[str, dict[str, str]] = {}
    if root is None:
        return result
    for rel in root.findall("rel:Relationship", NS):
        result[rel.get("Id", "")] = {
            "target": rel.get("Target", ""),
            "type": rel.get("Type", ""),
            "target_mode": rel.get("TargetMode", "Internal"),
        }
    return result


def _part_target(base_part: str, target: str) -> str:
    base = Path(base_part).parent
    parts: list[str] = []
    for item in (base / target).as_posix().split("/"):
        if item == "..":
            if parts:
                parts.pop()
        elif item not in {"", "."}:
            parts.append(item)
    return "/".join(parts)


def _paragraph_text(paragraph: ET.Element) -> str:
    values: list[str] = []
    for element in paragraph.iter():
        if element.tag == qn("w", "t"):
            values.append(element.text or "")
        elif element.tag == qn("w", "tab"):
            values.append("\t")
        elif element.tag in {qn("w", "br"), qn("w", "cr")}:
            values.append("\n")
    return "".join(values)


def _sections(document_root: ET.Element) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for index, sect in enumerate(document_root.findall(".//w:sectPr", NS)):
        size = sect.find("w:pgSz", NS)
        margins = sect.find("w:pgMar", NS)
        columns = sect.find("w:cols", NS)
        width = _float(size.get(qn("w", "w")) if size is not None else None, 1440)
        height = _float(size.get(qn("w", "h")) if size is not None else None, 1440)
        orient = size.get(qn("w", "orient")) if size is not None else None
        if not orient:
            orient = "landscape" if width and height and width > height else "portrait"
        sections.append(
            {
                "index": index,
                "orientation": orient,
                "page_width_in": width,
                "page_height_in": height,
                "margins_in": {
                    key: _float(margins.get(qn("w", key)) if margins is not None else None, 1440)
                    for key in ("top", "right", "bottom", "left", "header", "footer", "gutter")
                },
                "columns": int(columns.get(qn("w", "num"), "1")) if columns is not None else 1,
                "break_type": _value(sect.find("w:type", NS)) or "nextPage",
            }
        )
    return sections


def _content_types(package: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, str]]:
    root = _xml(package, "[Content_Types].xml")
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    if root is None:
        return defaults, overrides
    for item in root.findall("ct:Default", NS):
        defaults[item.get("Extension", "").lower()] = item.get("ContentType", "")
    for item in root.findall("ct:Override", NS):
        overrides[item.get("PartName", "").lstrip("/")] = item.get("ContentType", "")
    return defaults, overrides


def _images(package: zipfile.ZipFile, document_root: ET.Element, rels: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    defaults, overrides = _content_types(package)
    images: list[dict[str, Any]] = []
    for paragraph_index, paragraph in enumerate(document_root.findall(".//w:body/w:p", NS)):
        for blip in paragraph.findall(".//a:blip", NS):
            rel_id = blip.get(qn("r", "embed")) or blip.get(qn("r", "link"))
            rel = rels.get(rel_id or "", {})
            target = rel.get("target", "")
            part = _part_target("word/document.xml", target) if target else None
            extension = Path(part or target).suffix.lower().lstrip(".")
            doc_pr = next(iter(paragraph.findall(".//wp:docPr", NS)), None)
            extent = next(iter(paragraph.findall(".//wp:extent", NS)), None)
            placement = "anchored" if paragraph.find(".//wp:anchor", NS) is not None else "inline"
            media_type = overrides.get(part or "") or defaults.get(extension) or mimetypes.guess_type(target)[0]
            images.append(
                {
                    "relationship_id": rel_id,
                    "package_part": part,
                    "media_type": media_type,
                    "byte_size": len(package.read(part)) if part in package.namelist() else None,
                    "placement": placement,
                    "paragraph_index": paragraph_index,
                    "width_in": _float(extent.get("cx") if extent is not None else None, 914400),
                    "height_in": _float(extent.get("cy") if extent is not None else None, 914400),
                    "name": doc_pr.get("name") if doc_pr is not None else None,
                    "title": doc_pr.get("title") if doc_pr is not None else None,
                    "alt_text": doc_pr.get("descr") if doc_pr is not None else None,
                }
            )
    return images


def _headers_footers(package: zipfile.ZipFile, document_root: ET.Element, rels: dict[str, dict[str, str]]) -> dict[str, Any]:
    result: dict[str, list[dict[str, Any]]] = {"headers": [], "footers": []}
    seen: set[str] = set()
    for section_index, sect in enumerate(document_root.findall(".//w:sectPr", NS)):
        for kind in ("header", "footer"):
            for reference in sect.findall(f"w:{kind}Reference", NS):
                rel_id = reference.get(qn("r", "id"))
                rel = rels.get(rel_id or "", {})
                part = _part_target("word/document.xml", rel.get("target", ""))
                key = f"{kind}:{part}"
                if key in seen:
                    continue
                seen.add(key)
                root = _xml(package, part)
                paragraphs = [] if root is None else [
                    {
                        "text": _paragraph_text(p),
                        "style_id": _value(p.find("w:pPr/w:pStyle", NS)),
                    }
                    for p in root.findall(".//w:p", NS)
                ]
                result[f"{kind}s"].append(
                    {
                        "section_index": section_index,
                        "reference_type": reference.get(qn("w", "type")) or "default",
                        "package_part": part,
                        "paragraphs": paragraphs,
                        "contains_drawing": root is not None and root.find(".//w:drawing", NS) is not None,
                        "contains_vml": root is not None and root.find(".//w:pict", NS) is not None,
                    }
                )
    return result


def _tables(document_root: ET.Element) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, table in enumerate(document_root.findall(".//w:body/w:tbl", NS)):
        properties = table.find("w:tblPr", NS)
        grid = table.find("w:tblGrid", NS)
        rows = table.findall("w:tr", NS)
        max_cols = max((len(row.findall("w:tc", NS)) for row in rows), default=0)
        result.append(
            {
                "index": index,
                "style_id": _value(properties.find("w:tblStyle", NS)) if properties is not None else None,
                "rows": len(rows),
                "columns": max_cols,
                "grid_widths_dxa": [
                    int(column.get(qn("w", "w"), "0")) for column in grid.findall("w:gridCol", NS)
                ] if grid is not None else [],
                "width": _element_attributes(properties.find("w:tblW", NS)) if properties is not None else {},
                "indent": _element_attributes(properties.find("w:tblInd", NS)) if properties is not None else {},
                "borders": _element_attributes(properties.find("w:tblBorders", NS)) if properties is not None else {},
                "shading_fill": _value(properties.find("w:shd", NS), name="fill") if properties is not None else None,
            }
        )
    return result


def _numbering(package: zipfile.ZipFile) -> dict[str, Any]:
    root = _xml(package, "word/numbering.xml")
    if root is None:
        return {"abstract_definitions": [], "instances": []}
    abstracts = []
    for abstract in root.findall("w:abstractNum", NS):
        levels = []
        for level in abstract.findall("w:lvl", NS):
            levels.append(
                {
                    "level": int(level.get(qn("w", "ilvl"), "0")),
                    "format": _value(level.find("w:numFmt", NS)),
                    "text": _value(level.find("w:lvlText", NS)),
                }
            )
        abstracts.append({"abstract_id": abstract.get(qn("w", "abstractNumId")), "levels": levels})
    instances = [
        {
            "num_id": item.get(qn("w", "numId")),
            "abstract_id": _value(item.find("w:abstractNumId", NS)),
        }
        for item in root.findall("w:num", NS)
    ]
    return {"abstract_definitions": abstracts, "instances": instances}


def analyze_docx(source: Path | str, variant_name: str | None = None) -> dict[str, Any]:
    source = Path(source)
    if source.suffix.lower() != ".docx" or not source.is_file() or not zipfile.is_zipfile(source):
        raise ValueError(f"Input is not a valid DOCX package: {source}")

    source_bytes = source.read_bytes()
    chosen_name = variant_name or source.stem
    with zipfile.ZipFile(source) as package:
        if "word/document.xml" not in package.namelist():
            raise ValueError(f"Input is not a valid DOCX package: {source}")
        document_root = _xml(package, "word/document.xml")
        if document_root is None:
            raise ValueError(f"Input is not a valid DOCX package: {source}")

        theme = _theme(package)
        declared_styles, styles = _styles(package, theme)
        rels = _relationships(package, "word/document.xml")
        paragraphs: list[dict[str, Any]] = []
        exceptions: list[dict[str, Any]] = []
        semantic_roles: dict[str, Any] = {}

        for index, paragraph in enumerate(document_root.findall(".//w:body/w:p", NS)):
            ppr = paragraph.find("w:pPr", NS)
            style_id = _value(ppr.find("w:pStyle", NS)) if ppr is not None else None
            style_id = style_id or "Normal"
            style = styles.get(style_id, {})
            text = _paragraph_text(paragraph)
            role_info = _role_for(style_id, style, text, index)
            paragraph_item = {
                "index": index,
                "text_preview": text[:160],
                "style_id": style_id,
                "role": role_info,
                "direct_paragraph": _paragraph_format(ppr),
            }
            paragraphs.append(paragraph_item)

            role = role_info["role"]
            candidate = {
                "source_style_id": style_id,
                "confidence": role_info["confidence"],
                "evidence": role_info["evidence"],
                "font": style.get("font", {}),
                "paragraph": style.get("paragraph", {}),
            }
            if role not in semantic_roles or candidate["confidence"] > semantic_roles[role]["confidence"]:
                semantic_roles[role] = candidate

            base_font = style.get("font", {})
            for run_index, run in enumerate(paragraph.findall("w:r", NS)):
                direct_font = _font(run.find("w:rPr", NS), theme)
                changed = {
                    key: value
                    for key, value in direct_font.items()
                    if value is not None and value != base_font.get(key)
                }
                if changed:
                    exceptions.append(
                        {
                            "paragraph_index": index,
                            "run_index": run_index,
                            "text_preview": _paragraph_text(run)[:80],
                            "base_style_id": style_id,
                            "direct_font": changed,
                        }
                    )

        for style_id, style in styles.items():
            role_info = _role_for(style_id, style, "", 999)
            role = role_info["role"]
            if role == "normal" and str(style.get("name", "")).lower() not in ROLE_STYLES["normal"]:
                continue
            candidate = {
                "source_style_id": style_id,
                "confidence": role_info["confidence"],
                "evidence": role_info["evidence"],
                "font": style.get("font", {}),
                "paragraph": style.get("paragraph", {}),
            }
            if role not in semantic_roles or candidate["confidence"] > semantic_roles[role]["confidence"]:
                semantic_roles[role] = candidate

        limitations: list[str] = []
        names = set(package.namelist())
        if any(name.endswith(".bin") for name in names):
            limitations.append("Embedded binary or OLE objects are inventoried only by package presence.")
        if document_root.find(".//w:altChunk", NS) is not None:
            limitations.append("altChunk content is not expanded.")
        if document_root.find(".//w:object", NS) is not None:
            limitations.append("Embedded Word objects are not semantically analyzed.")

        return {
            "schema_version": SCHEMA_VERSION,
            "analyzer_version": ANALYZER_VERSION,
            "identity": {
                "variant_id": slugify(chosen_name),
                "variant_name": chosen_name,
                "source_filename": source.name,
                "source_sha256": sha256(source_bytes).hexdigest(),
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            "sections": _sections(document_root),
            "theme": theme,
            "styles": styles,
            "declared_styles": declared_styles,
            "semantic_roles": semantic_roles,
            "paragraphs": paragraphs,
            "direct_formatting_exceptions": exceptions,
            "numbering": _numbering(package),
            "tables": _tables(document_root),
            "images": _images(package, document_root, rels),
            "headers_footers": _headers_footers(package, document_root, rels),
            "limitations": limitations,
        }


def _markdown(profile: dict[str, Any]) -> str:
    identity = profile["identity"]
    lines = [
        f"# DOCX Format Profile: {identity['variant_name']}",
        "",
        f"- Source: `{identity['source_filename']}`",
        f"- SHA-256: `{identity['source_sha256']}`",
        f"- Analyzed: {identity['analyzed_at']}",
        "",
        "## Page layout",
        "",
    ]
    for section in profile["sections"]:
        margins = section.get("margins_in", {})
        lines.append(
            f"- Section {section['index'] + 1}: {section['orientation']}, "
            f"{section.get('page_width_in')} x {section.get('page_height_in')} in; "
            f"margins T/R/B/L {margins.get('top')}/{margins.get('right')}/"
            f"{margins.get('bottom')}/{margins.get('left')} in"
        )

    lines.extend(["", "## Typography and semantic roles", "", "| Role | Style | Font | Size | Color | Confidence |", "|---|---|---|---:|---|---:|"])
    for role, item in sorted(profile["semantic_roles"].items()):
        font = item.get("font", {})
        lines.append(
            f"| {role} | {item.get('source_style_id', '')} | {font.get('name', '')} | "
            f"{font.get('size_pt', '')} | {font.get('color') or font.get('theme_color', '')} | "
            f"{item.get('confidence', '')} |"
        )

    colors = profile.get("theme", {}).get("colors", {})
    lines.extend(["", "## Theme and color palette", ""])
    lines.extend(f"- `{name}`: `{value}`" for name, value in colors.items())
    lines.extend(["", "## Tables", ""])
    if profile["tables"]:
        lines.extend(
            f"- Table {item['index'] + 1}: {item['rows']} rows x {item['columns']} columns; style `{item.get('style_id')}`"
            for item in profile["tables"]
        )
    else:
        lines.append("No tables detected.")

    lines.extend(["", "## Images", ""])
    if profile["images"]:
        lines.extend(
            f"- `{item.get('package_part')}` ({item.get('media_type')}), {item.get('placement')}, "
            f"alt text: {item.get('alt_text') or 'none'}"
            for item in profile["images"]
        )
    else:
        lines.append("No images detected.")

    header_count = len(profile["headers_footers"].get("headers", []))
    footer_count = len(profile["headers_footers"].get("footers", []))
    lines.extend(["", "## Headers and footers", "", f"- Headers: {header_count}", f"- Footers: {footer_count}"])
    lines.extend(["", "## Direct-formatting exceptions", "", f"Detected: {len(profile['direct_formatting_exceptions'])}"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in profile["limitations"] or ["No known limitations for detected content."])
    return "\n".join(lines) + "\n"


def write_profile(profile: dict[str, Any], output_dir: Path | str) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = profile["identity"]["variant_id"]
    json_path = output_dir / f"{slug}.json"
    markdown_path = output_dir / f"{slug}.md"
    json_path.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(profile), encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--variant-name")
    parser.add_argument("--output-dir", type=Path, default=Path("references/document-profiles"))
    args = parser.parse_args()
    json_path, markdown_path = write_profile(
        analyze_docx(args.source, args.variant_name), args.output_dir
    )
    print(json_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
