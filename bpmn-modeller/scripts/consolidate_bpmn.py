#!/usr/bin/env python3
"""Consolidate multiple BPMN 2.0 files into one definitions document."""

from __future__ import annotations

import argparse
import re
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

try:
    from .output_path_guard import ensure_external_output
except ImportError:
    from output_path_guard import ensure_external_output


NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

REFERENCE_ATTRS = {
    "bpmnElement",
    "processRef",
    "sourceRef",
    "targetRef",
    "messageRef",
    "errorRef",
    "escalationRef",
    "signalRef",
    "calledElement",
}

REFERENCE_TEXT_TAGS = {
    "incoming",
    "outgoing",
    "flowNodeRef",
}


def qname(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def clean_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "bpmn"
    if not re.match(r"^[A-Za-z_]", value):
        value = f"bpmn_{value}"
    return value


def collect_ids(root: ET.Element) -> dict[str, str]:
    return {
        value: value
        for element in root.iter()
        for attr, value in element.attrib.items()
        if local_name(attr) == "id"
    }


def prefix_document(root: ET.Element, prefix: str) -> ET.Element:
    root = deepcopy(root)
    id_map = {old: f"{prefix}_{old}" for old in collect_ids(root)}

    for element in root.iter():
        for attr, value in list(element.attrib.items()):
            attr_name = local_name(attr)
            if attr_name == "id" and value in id_map:
                element.attrib[attr] = id_map[value]
            elif attr_name in REFERENCE_ATTRS and value in id_map:
                element.attrib[attr] = id_map[value]

        if local_name(element.tag) in REFERENCE_TEXT_TAGS and element.text in id_map:
            element.text = id_map[element.text]

    return root


def consolidate(inputs: list[Path], output: Path, name: str) -> Path:
    output = ensure_external_output(output)
    for uri in NS.values():
        ET.register_namespace(next(prefix for prefix, value in NS.items() if value == uri), uri)

    definitions = ET.Element(
        qname("bpmn", "definitions"),
        {
            "id": clean_id(f"Definitions_{name}"),
            "name": name,
            "targetNamespace": "https://codex.local/bpmn-modeller/consolidated",
        },
    )

    for input_path in inputs:
        root = ET.parse(input_path).getroot()
        if local_name(root.tag) != "definitions":
            raise ValueError(f"{input_path} root is not bpmn:definitions")
        prefix = clean_id(input_path.stem)
        prefixed = prefix_document(root, prefix)
        for child in list(prefixed):
            definitions.append(deepcopy(child))

    output.parent.mkdir(parents=True, exist_ok=True)
    rough = ET.tostring(definitions, encoding="utf-8")
    pretty = xml.dom.minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    output.write_bytes(pretty)
    ET.parse(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path to write consolidated .bpmn")
    parser.add_argument("inputs", type=Path, nargs="+", help="BPMN files to consolidate")
    parser.add_argument("--name", default="Consolidated BPMN Model", help="Name for the consolidated definitions")
    args = parser.parse_args()

    try:
        output = consolidate(args.inputs, args.output, args.name)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
