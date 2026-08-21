#!/usr/bin/env python3
"""Generate an importable BPMN 2.0 file from a compact JSON process model."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

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

SUPPORTED_TYPES = {
    "startEvent",
    "endEvent",
    "task",
    "userTask",
    "serviceTask",
    "manualTask",
    "businessRuleTask",
    "sendTask",
    "receiveTask",
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
}

EVENT_SIZE = (36, 36)
GATEWAY_SIZE = (50, 50)
TASK_MIN_WIDTH = 170
TASK_MAX_WIDTH = 270
TASK_MIN_HEIGHT = 90
COLUMN_SPACING = 145
MIN_LANE_HEIGHT = 170
LANE_TOP_PADDING = 35
LANE_BOTTOM_PADDING = 75
STACK_Y_SPACING = 35
TOP_MARGIN = 80
LEFT_MARGIN = 180
EDGE_CLEARANCE = 24
EDGE_TRACK_SPACING = 26


def qname(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def clean_id(value: str, prefix: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value).strip())
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = prefix
    if not re.match(r"^[A-Za-z_]", value):
        value = f"{prefix}_{value}"
    return value


def bpmn_id(kind: str, value: str) -> str:
    return f"{kind}_{clean_id(value, kind)}"


def require_list(model: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = model.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"`{key}` must be a list")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"`{key}` must contain objects")
    return value


def normalize_model(model: dict[str, Any]) -> dict[str, Any]:
    nodes = require_list(model, "nodes")
    flows = require_list(model, "flows")
    lanes = require_list(model, "lanes")
    if not nodes:
        raise ValueError("model must contain at least one node")

    lane_by_id: dict[str, dict[str, str]] = {}
    for i, lane in enumerate(lanes, start=1):
        lane_id = clean_id(str(lane.get("id") or f"lane_{i}"), "lane")
        lane_by_id[lane_id] = {
            "id": lane_id,
            "bpmn_id": bpmn_id("Lane", lane_id),
            "name": str(lane.get("name") or lane_id.replace("_", " ").title()),
        }

    normalized_nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for i, node in enumerate(nodes, start=1):
        node_type = str(node.get("type") or "task")
        if node_type not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported node type `{node_type}`")
        raw_id = clean_id(str(node.get("id") or f"node_{i}"), "node")
        if raw_id in node_ids:
            raise ValueError(f"duplicate node id `{raw_id}`")
        node_ids.add(raw_id)
        lane_id = clean_id(str(node.get("lane") or "main"), "lane")
        if lane_id not in lane_by_id:
            lane_by_id[lane_id] = {
                "id": lane_id,
                "bpmn_id": bpmn_id("Lane", lane_id),
                "name": lane_id.replace("_", " ").title(),
            }
        normalized_nodes.append(
            {
                **node,
                "id": raw_id,
                "bpmn_id": bpmn_id(node_type[0].upper() + node_type[1:], raw_id),
                "type": node_type,
                "name": str(node.get("name") or raw_id.replace("_", " ").title()),
                "lane": lane_id,
            }
        )

    normalized_flows: list[dict[str, Any]] = []
    flow_ids: set[str] = set()
    for i, flow in enumerate(flows, start=1):
        source = clean_id(str(flow.get("source") or ""), "node")
        target = clean_id(str(flow.get("target") or ""), "node")
        if source not in node_ids:
            raise ValueError(f"flow `{flow.get('id') or i}` has unknown source `{source}`")
        if target not in node_ids:
            raise ValueError(f"flow `{flow.get('id') or i}` has unknown target `{target}`")
        raw_id = clean_id(str(flow.get("id") or f"flow_{i}"), "flow")
        if raw_id in flow_ids:
            raise ValueError(f"duplicate flow id `{raw_id}`")
        flow_ids.add(raw_id)
        normalized_flows.append(
            {
                **flow,
                "id": raw_id,
                "bpmn_id": bpmn_id("Flow", raw_id),
                "source": source,
                "target": target,
                "name": str(flow.get("name") or ""),
                "condition": str(flow.get("condition") or ""),
            }
        )

    model["process_id"] = clean_id(str(model.get("process_id") or "process"), "process")
    model["process_name"] = str(model.get("process_name") or model["process_id"].replace("_", " ").title())
    model["lanes"] = list(lane_by_id.values())
    model["nodes"] = normalized_nodes
    model["flows"] = normalized_flows

    external_participants: list[dict[str, str]] = []
    external_ids: set[str] = set()
    for i, participant in enumerate(model.get("external_participants", []) or [], start=1):
        if not isinstance(participant, dict):
            raise ValueError("`external_participants` must contain objects")
        raw_id = clean_id(str(participant.get("id") or f"external_{i}"), "participant")
        if raw_id in external_ids:
            raise ValueError(f"duplicate external participant id `{raw_id}`")
        external_ids.add(raw_id)
        external_participants.append(
            {
                "id": raw_id,
                "bpmn_id": bpmn_id("Participant", raw_id),
                "name": str(participant.get("name") or raw_id.replace("_", " ").title()),
            }
        )
    model["external_participants"] = external_participants

    message_flows: list[dict[str, str]] = []
    message_flow_ids: set[str] = set()
    reference_ids = node_ids | external_ids
    for i, flow in enumerate(model.get("message_flows", []) or [], start=1):
        if not isinstance(flow, dict):
            raise ValueError("`message_flows` must contain objects")
        source = clean_id(str(flow.get("source") or ""), "node")
        target = clean_id(str(flow.get("target") or ""), "node")
        if source not in reference_ids:
            raise ValueError(f"message flow `{flow.get('id') or i}` has unknown source `{source}`")
        if target not in reference_ids:
            raise ValueError(f"message flow `{flow.get('id') or i}` has unknown target `{target}`")
        raw_id = clean_id(str(flow.get("id") or f"message_flow_{i}"), "message_flow")
        if raw_id in message_flow_ids:
            raise ValueError(f"duplicate message flow id `{raw_id}`")
        message_flow_ids.add(raw_id)
        message_flows.append(
            {
                "id": raw_id,
                "bpmn_id": bpmn_id("MessageFlow", raw_id),
                "source": source,
                "target": target,
                "name": str(flow.get("name") or ""),
            }
        )
    model["message_flows"] = message_flows
    return model


def graph_depths(nodes: list[dict[str, Any]], flows: list[dict[str, Any]]) -> dict[str, int]:
    incoming_count = {node["id"]: 0 for node in nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for flow in flows:
        outgoing[flow["source"]].append(flow["target"])
        incoming_count[flow["target"]] += 1

    queue = deque([node_id for node_id, count in incoming_count.items() if count == 0])
    depths = {node_id: 0 for node_id in incoming_count}
    seen = set(queue)
    while queue:
        node_id = queue.popleft()
        for target in outgoing[node_id]:
            depths[target] = max(depths[target], depths[node_id] + 1)
            incoming_count[target] -= 1
            if incoming_count[target] == 0:
                queue.append(target)
                seen.add(target)

    # Cycles keep remaining nodes from reaching zero. Place them after their known predecessors.
    for node in nodes:
        if node["id"] not in seen:
            preds = [flow["source"] for flow in flows if flow["target"] == node["id"]]
            depths[node["id"]] = max([depths.get(pred, 0) + 1 for pred in preds] or [0])
    return depths


def layout(model: dict[str, Any]) -> dict[str, dict[str, int]]:
    depths = graph_depths(model["nodes"], model["flows"])
    lanes = lane_layout(model, depths)
    columns = column_layout(model["nodes"], depths)
    occupied_height: dict[tuple[str, int], int] = defaultdict(int)
    positions: dict[str, dict[str, int]] = {}

    for node in model["nodes"]:
        depth = depths[node["id"]]
        lane = lanes[node["lane"]]
        width, height = size_for(node)
        stack_key = (node["lane"], depth)
        y_offset = occupied_height[stack_key]
        occupied_height[stack_key] += height + STACK_Y_SPACING
        positions[node["id"]] = {
            "x": columns[depth],
            "y": lane["y"] + LANE_TOP_PADDING + y_offset,
            "width": width,
            "height": height,
            "lane": node["lane"],
        }
    return positions


def lane_layout(model: dict[str, Any], depths: dict[str, int] | None = None) -> dict[str, dict[str, int]]:
    depths = depths or graph_depths(model["nodes"], model["flows"])
    lane_depth_heights = {lane["id"]: defaultdict(int) for lane in model["lanes"]}

    for node in model["nodes"]:
        lane_id = node["lane"]
        depth = depths[node["id"]]
        lane_depth_heights[lane_id][depth] += size_for(node)[1] + STACK_Y_SPACING

    lanes: dict[str, dict[str, int]] = {}
    y = TOP_MARGIN
    for lane in model["lanes"]:
        lane_id = lane["id"]
        content_height = max(lane_depth_heights[lane_id].values(), default=0)
        if content_height:
            content_height -= STACK_Y_SPACING
        height = max(
            MIN_LANE_HEIGHT,
            LANE_TOP_PADDING + content_height + LANE_BOTTOM_PADDING,
        )
        lanes[lane_id] = {"y": y, "height": height}
        y += height
    return lanes


def column_layout(nodes: list[dict[str, Any]], depths: dict[str, int]) -> dict[int, int]:
    widths_by_depth: dict[int, int] = defaultdict(lambda: TASK_MIN_WIDTH)
    for node in nodes:
        depth = depths[node["id"]]
        widths_by_depth[depth] = max(widths_by_depth[depth], size_for(node)[0])

    columns: dict[int, int] = {}
    x = LEFT_MARGIN
    for depth in range(max(widths_by_depth.keys(), default=0) + 1):
        columns[depth] = x
        x += widths_by_depth[depth] + COLUMN_SPACING
    return columns


def size_for(node: dict[str, Any] | str) -> tuple[int, int]:
    node_type = node if isinstance(node, str) else str(node["type"])
    if node_type.endswith("Event"):
        return EVENT_SIZE
    if node_type.endswith("Gateway"):
        return GATEWAY_SIZE
    name = "" if isinstance(node, str) else str(node.get("name") or "")
    width = min(TASK_MAX_WIDTH, max(TASK_MIN_WIDTH, 150 + len(name) * 2))
    chars_per_line = max(18, width // 8)
    line_count = max(1, math.ceil(len(name) / chars_per_line))
    height = max(TASK_MIN_HEIGHT, 46 + line_count * 22)
    return width, height


def point_for(bounds: dict[str, int], side: str) -> tuple[int, int]:
    if side == "left":
        return bounds["x"], bounds["y"] + bounds["height"] // 2
    if side == "right":
        return bounds["x"] + bounds["width"], bounds["y"] + bounds["height"] // 2
    if side == "top":
        return bounds["x"] + bounds["width"] // 2, bounds["y"]
    if side == "bottom":
        return bounds["x"] + bounds["width"] // 2, bounds["y"] + bounds["height"]
    raise ValueError(f"unknown side {side}")


def segment_hits_rect(a: tuple[int, int], b: tuple[int, int], rect: dict[str, int], clearance: int = 8) -> bool:
    x1, y1 = a
    x2, y2 = b
    left = rect["x"] - clearance
    right = rect["x"] + rect["width"] + clearance
    top = rect["y"] - clearance
    bottom = rect["y"] + rect["height"] + clearance

    if x1 == x2:
        x = x1
        if not left <= x <= right:
            return False
        return max(min(y1, y2), top) <= min(max(y1, y2), bottom)
    if y1 == y2:
        y = y1
        if not top <= y <= bottom:
            return False
        return max(min(x1, x2), left) <= min(max(x1, x2), right)
    return False


def path_collision_score(path: list[tuple[int, int]], rects: dict[str, dict[str, int]], excluded: set[str]) -> int:
    score = 0
    for a, b in zip(path, path[1:]):
        if a == b:
            continue
        for node_id, rect in rects.items():
            if node_id in excluded:
                continue
            if segment_hits_rect(a, b, rect):
                score += 1
    return score


def path_length(path: list[tuple[int, int]]) -> int:
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(path, path[1:]))


def route_edge(
    flow: dict[str, Any],
    positions: dict[str, dict[str, int]],
    lanes: dict[str, dict[str, int]],
    node_rects: dict[str, dict[str, int]],
    index: int,
) -> list[tuple[int, int]]:
    source = positions[flow["source"]]
    target = positions[flow["target"]]
    forward = target["x"] >= source["x"]
    source_side = "right" if forward else "left"
    target_side = "left" if forward else "right"
    start = point_for(source, source_side)
    end = point_for(target, target_side)
    max_right = max(rect["x"] + rect["width"] for rect in node_rects.values())
    min_left = min(rect["x"] for rect in node_rects.values())

    candidates: list[list[tuple[int, int]]] = []
    if forward:
        left = start[0] + EDGE_CLEARANCE
        right = end[0] - EDGE_CLEARANCE
        if right > left:
            mid = (left + right) // 2
            for offset in (0, EDGE_TRACK_SPACING, -EDGE_TRACK_SPACING, EDGE_TRACK_SPACING * 2, -EDGE_TRACK_SPACING * 2):
                x = min(right, max(left, mid + offset + (index % 3 - 1) * 8))
                candidates.append([start, (x, start[1]), (x, end[1]), end])
    else:
        outside_right = max_right + 90 + (index % 4) * EDGE_TRACK_SPACING
        outside_left = max(80, min_left - 90 - (index % 4) * EDGE_TRACK_SPACING)
        candidates.append([start, (outside_right, start[1]), (outside_right, end[1]), end])
        candidates.append([start, (outside_left, start[1]), (outside_left, end[1]), end])

    source_lane = lanes[source["lane"]]
    target_lane = lanes[target["lane"]]
    track_ys = [
        source_lane["y"] + source_lane["height"] - EDGE_CLEARANCE - (index % 3) * EDGE_TRACK_SPACING,
        source_lane["y"] + EDGE_CLEARANCE + (index % 3) * EDGE_TRACK_SPACING,
        target_lane["y"] + target_lane["height"] - EDGE_CLEARANCE - (index % 3) * EDGE_TRACK_SPACING,
        target_lane["y"] + EDGE_CLEARANCE + (index % 3) * EDGE_TRACK_SPACING,
    ]
    if source["lane"] != target["lane"]:
        top = min(source_lane["y"], target_lane["y"])
        bottom = max(source_lane["y"] + source_lane["height"], target_lane["y"] + target_lane["height"])
        track_ys.append((top + bottom) // 2)

    for y in track_ys:
        x1 = start[0] + EDGE_CLEARANCE if forward else start[0] - EDGE_CLEARANCE
        x2 = end[0] - EDGE_CLEARANCE if forward else end[0] + EDGE_CLEARANCE
        candidates.append([start, (x1, start[1]), (x1, y), (x2, y), (x2, end[1]), end])

    if not candidates:
        mid_x = start[0] + max(35, (end[0] - start[0]) // 2)
        candidates.append([start, (mid_x, start[1]), (mid_x, end[1]), end])

    excluded = {flow["source"], flow["target"]}
    return min(candidates, key=lambda path: (path_collision_score(path, node_rects, excluded), path_length(path)))


def add_text(parent: ET.Element, tag: str, text: str, **attrs: str) -> ET.Element:
    child = ET.SubElement(parent, tag, attrs)
    child.text = text
    return child


def build_bpmn(model: dict[str, Any]) -> ET.Element:
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)

    model = normalize_model(model)
    positions = layout(model)
    process_bpmn_id = bpmn_id("Process", model["process_id"])
    collaboration_id = bpmn_id("Collaboration", model["process_id"])
    participant_id = bpmn_id("Participant", model["process_id"])

    definitions = ET.Element(
        qname("bpmn", "definitions"),
        {
            "id": bpmn_id("Definitions", model["process_id"]),
            "targetNamespace": "https://codex.local/bpmn-modeller",
        },
    )

    collaboration = ET.SubElement(definitions, qname("bpmn", "collaboration"), {"id": collaboration_id})
    ET.SubElement(
        collaboration,
        qname("bpmn", "participant"),
        {
            "id": participant_id,
            "name": model["process_name"],
            "processRef": process_bpmn_id,
        },
    )
    external_participant_by_id = {participant["id"]: participant for participant in model.get("external_participants", [])}
    for participant in model.get("external_participants", []):
        ET.SubElement(
            collaboration,
            qname("bpmn", "participant"),
            {
                "id": participant["bpmn_id"],
                "name": participant["name"],
            },
        )

    process = ET.SubElement(
        definitions,
        qname("bpmn", "process"),
        {"id": process_bpmn_id, "name": model["process_name"], "isExecutable": "false"},
    )

    lane_set = ET.SubElement(process, qname("bpmn", "laneSet"), {"id": bpmn_id("LaneSet", model["process_id"])})
    nodes_by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in model["nodes"]:
        nodes_by_lane[node["lane"]].append(node)
    for lane in model["lanes"]:
        lane_el = ET.SubElement(lane_set, qname("bpmn", "lane"), {"id": lane["bpmn_id"], "name": lane["name"]})
        for node in nodes_by_lane.get(lane["id"], []):
            add_text(lane_el, qname("bpmn", "flowNodeRef"), node["bpmn_id"])

    incoming: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for flow in model["flows"]:
        incoming[flow["target"]].append(flow["bpmn_id"])
        outgoing[flow["source"]].append(flow["bpmn_id"])

    node_by_id = {node["id"]: node for node in model["nodes"]}
    for node in model["nodes"]:
        attrs = {"id": node["bpmn_id"], "name": node["name"]}
        if node["type"].endswith("Gateway") and node.get("gatewayDirection"):
            attrs["gatewayDirection"] = str(node["gatewayDirection"])
        node_el = ET.SubElement(process, qname("bpmn", node["type"]), attrs)
        for flow_id in incoming[node["id"]]:
            add_text(node_el, qname("bpmn", "incoming"), flow_id)
        for flow_id in outgoing[node["id"]]:
            add_text(node_el, qname("bpmn", "outgoing"), flow_id)

    for flow in model["flows"]:
        attrs = {
            "id": flow["bpmn_id"],
            "sourceRef": node_by_id[flow["source"]]["bpmn_id"],
            "targetRef": node_by_id[flow["target"]]["bpmn_id"],
        }
        if flow["name"]:
            attrs["name"] = flow["name"]
        flow_el = ET.SubElement(process, qname("bpmn", "sequenceFlow"), attrs)
        if flow["condition"]:
            cond = ET.SubElement(
                flow_el,
                qname("bpmn", "conditionExpression"),
                {qname("xsi", "type"): "bpmn:tFormalExpression"},
            )
            cond.text = flow["condition"]

    def interaction_ref(raw_id: str) -> str:
        if raw_id in node_by_id:
            return node_by_id[raw_id]["bpmn_id"]
        if raw_id in external_participant_by_id:
            return external_participant_by_id[raw_id]["bpmn_id"]
        raise ValueError(f"unknown interaction reference `{raw_id}`")

    for flow in model.get("message_flows", []):
        attrs = {
            "id": flow["bpmn_id"],
            "sourceRef": interaction_ref(flow["source"]),
            "targetRef": interaction_ref(flow["target"]),
        }
        if flow["name"]:
            attrs["name"] = flow["name"]
        ET.SubElement(collaboration, qname("bpmn", "messageFlow"), attrs)

    diagram = ET.SubElement(definitions, qname("bpmndi", "BPMNDiagram"), {"id": bpmn_id("BPMNDiagram", model["process_id"])})
    plane = ET.SubElement(
        diagram,
        qname("bpmndi", "BPMNPlane"),
        {"id": bpmn_id("BPMNPlane", model["process_id"]), "bpmnElement": collaboration_id},
    )

    depths = graph_depths(model["nodes"], model["flows"])
    lanes = lane_layout(model, depths)
    max_right = max((pos["x"] + pos["width"] for pos in positions.values()), default=LEFT_MARGIN)
    pool_width = max_right + 220
    pool_height = TOP_MARGIN + sum(lane["height"] for lane in lanes.values()) + 40
    participant_shape = ET.SubElement(
        plane,
        qname("bpmndi", "BPMNShape"),
        {"id": f"{participant_id}_di", "bpmnElement": participant_id, "isHorizontal": "true"},
    )
    ET.SubElement(participant_shape, qname("dc", "Bounds"), {"x": "60", "y": "50", "width": str(pool_width), "height": str(pool_height)})

    external_bounds: dict[str, dict[str, int]] = {}
    external_y = 50 + pool_height + 45
    for index, participant in enumerate(model.get("external_participants", [])):
        bounds = {"x": 60, "y": external_y + index * 150, "width": pool_width, "height": 120}
        external_bounds[participant["id"]] = bounds
        participant_shape = ET.SubElement(
            plane,
            qname("bpmndi", "BPMNShape"),
            {"id": f"{participant['bpmn_id']}_di", "bpmnElement": participant["bpmn_id"], "isHorizontal": "true"},
        )
        ET.SubElement(participant_shape, qname("dc", "Bounds"), {key: str(value) for key, value in bounds.items()})

    for lane in model["lanes"]:
        lane_bounds = lanes[lane["id"]]
        lane_shape = ET.SubElement(
            plane,
            qname("bpmndi", "BPMNShape"),
            {"id": f"{lane['bpmn_id']}_di", "bpmnElement": lane["bpmn_id"], "isHorizontal": "true"},
        )
        ET.SubElement(
            lane_shape,
            qname("dc", "Bounds"),
            {"x": "90", "y": str(lane_bounds["y"]), "width": str(pool_width - 30), "height": str(lane_bounds["height"])},
        )

    for node in model["nodes"]:
        pos = positions[node["id"]]
        shape = ET.SubElement(plane, qname("bpmndi", "BPMNShape"), {"id": f"{node['bpmn_id']}_di", "bpmnElement": node["bpmn_id"]})
        ET.SubElement(
            shape,
            qname("dc", "Bounds"),
            {key: str(pos[key]) for key in ("x", "y", "width", "height")},
        )

    node_rects = {node["id"]: positions[node["id"]] for node in model["nodes"]}
    for index, flow in enumerate(model["flows"]):
        edge = ET.SubElement(plane, qname("bpmndi", "BPMNEdge"), {"id": f"{flow['bpmn_id']}_di", "bpmnElement": flow["bpmn_id"]})
        waypoints = route_edge(flow, positions, lanes, node_rects, index)
        for x, y in waypoints:
            ET.SubElement(edge, qname("di", "waypoint"), {"x": str(x), "y": str(y)})

    def message_point(raw_id: str, role: str) -> tuple[int, int]:
        if raw_id in positions:
            side = "bottom" if role == "source" else "top"
            return point_for(positions[raw_id], side)
        bounds = external_bounds[raw_id]
        y = bounds["y"] if role == "target" else bounds["y"] + bounds["height"]
        return bounds["x"] + bounds["width"] // 2, y

    for flow in model.get("message_flows", []):
        edge = ET.SubElement(plane, qname("bpmndi", "BPMNEdge"), {"id": f"{flow['bpmn_id']}_di", "bpmnElement": flow["bpmn_id"]})
        start = message_point(flow["source"], "source")
        end = message_point(flow["target"], "target")
        mid_y = (start[1] + end[1]) // 2
        for x, y in [start, (start[0], mid_y), (end[0], mid_y), end]:
            ET.SubElement(edge, qname("di", "waypoint"), {"x": str(x), "y": str(y)})

    return definitions


def validate_model(model: dict[str, Any]) -> list[str]:
    model = normalize_model(model)
    node_ids = {node["id"] for node in model["nodes"]}
    incoming = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: 0 for node_id in node_ids}
    warnings: list[str] = []
    for flow in model["flows"]:
        incoming[flow["target"]] += 1
        outgoing[flow["source"]] += 1
    for node in model["nodes"]:
        if node["type"] != "startEvent" and incoming[node["id"]] == 0:
            warnings.append(f"{node['id']} has no incoming sequence flow")
        if node["type"] != "endEvent" and outgoing[node["id"]] == 0:
            warnings.append(f"{node['id']} has no outgoing sequence flow")
    return warnings


def write_pretty_xml(root: ET.Element, output_path: Path) -> None:
    rough = ET.tostring(root, encoding="utf-8")
    pretty = xml.dom.minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    output_path.write_bytes(pretty)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_json", type=Path, help="Path to compact BPMN JSON model")
    parser.add_argument("output_bpmn", type=Path, help="Path to write .bpmn XML")
    parser.add_argument("--strict", action="store_true", help="Treat connectivity warnings as errors")
    args = parser.parse_args()

    try:
        output_bpmn = ensure_external_output(args.output_bpmn)
        model = json.loads(args.model_json.read_text(encoding="utf-8"))
        if not isinstance(model, dict):
            raise ValueError("top-level JSON must be an object")
        warnings = validate_model(model)
        if args.strict and warnings:
            raise ValueError("; ".join(warnings))
        root = build_bpmn(model)
        output_bpmn.parent.mkdir(parents=True, exist_ok=True)
        write_pretty_xml(root, output_bpmn)
        ET.parse(output_bpmn)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(output_bpmn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
