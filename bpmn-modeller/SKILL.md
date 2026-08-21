---
name: bpmn-modeller
description: Create BPMN 2.0 process models from narrative content, SOPs, requirements, policies, transcripts, or process notes. Use when Codex needs to analyze source content, identify process actors, activities, events, decisions, handoffs, exceptions, and outputs, then generate an importable .bpmn XML file for BPMN tools such as Camunda Modeler, bpmn.io, Signavio, Bizagi, or similar modelling tools.
---

# BPMN Modeller

## Overview

Create importable BPMN 2.0 `.bpmn` files from user-provided process content. Prefer a clear, valid, tool-importable model over an over-decorated diagram.

## Output Location

1. If the user specifies an output folder, use that folder.
2. Otherwise, use `<active-project>/outputs/bpmn-modeller/`.
3. Resolve and verify the destination before creating any file.

The active project is the user's current working project or workspace, not this skill's source or installation directory. Never write generated deliverables, working files, temporary deliverables, or processing state to this skill's root or any descendant.

If the current working directory is this skill's root or lies within it and the user has not supplied an external output folder, stop before writing and ask the user to choose a destination outside the skill folder. Do not create an `outputs` folder inside this skill.

During ordinary use, treat skill scripts, references, templates, profiles, manifests, tests, and assets as read-only. Write inside the skill only when the user explicitly asks to create, update, or maintain the skill itself.

## Workflow

1. Read the source content and identify the process scope, trigger, desired outcome, actors, systems, major activities, decisions, parallel work, exceptions, and end states.
2. If the process scope, actors, or level of detail is ambiguous and the ambiguity changes the model structure, ask a concise clarification. Otherwise make reasonable assumptions and list them in the handoff.
3. Draft a structured BPMN model before writing XML:
   - Use one process pool by default.
   - Use lanes for roles, teams, systems, or departments that own activities.
   - Use tasks for work, events for triggers/outcomes/waits, gateways for real branching or synchronization, and sequence flows for ordering.
   - Keep labels verb-led and concise, for example `Review request`, `Validate customer data`, `Approve exception`.
4. Create a JSON model in the resolved external output folder and run `scripts/create_bpmn.py` to generate the `.bpmn` file in the same folder.
5. Validate the generated file with XML parsing and a BPMN consistency pass. Fix validation failures before handing off.
6. In the final response, provide the `.bpmn` file path, summarize the model shape, and note any modelling assumptions.

## Generating BPMN XML

Use `scripts/create_bpmn.py` for deterministic `.bpmn` generation:

```bash
python3 path/to/bpmn-modeller/scripts/create_bpmn.py \
  /path/to/active-project/outputs/bpmn-modeller/model.json \
  /path/to/active-project/outputs/bpmn-modeller/model.bpmn
```

JSON shape:

```json
{
  "process_id": "customer_onboarding",
  "process_name": "Customer onboarding",
  "lanes": [
    {"id": "sales", "name": "Sales"},
    {"id": "operations", "name": "Operations"}
  ],
  "nodes": [
    {"id": "start", "type": "startEvent", "name": "Request received", "lane": "sales"},
    {"id": "capture", "type": "userTask", "name": "Capture customer details", "lane": "sales"},
    {"id": "end", "type": "endEvent", "name": "Customer onboarded", "lane": "operations"}
  ],
  "flows": [
    {"id": "flow_1", "source": "start", "target": "capture"},
    {"id": "flow_2", "source": "capture", "target": "end"}
  ]
}
```

Supported node types: `startEvent`, `endEvent`, `task`, `userTask`, `serviceTask`, `manualTask`, `businessRuleTask`, `sendTask`, `receiveTask`, `exclusiveGateway`, `parallelGateway`, `inclusiveGateway`, `intermediateCatchEvent`, `intermediateThrowEvent`.

Use `gatewayDirection` on gateways when helpful: `Diverging`, `Converging`, `Mixed`, or `Unspecified`.

Use `condition` on sequence flows leaving decision gateways when the branch meaning is not obvious from the target label.

## Modelling Guidance

Read `references/bpmn-modelling-guide.md` when the source content includes multiple actors, exception paths, gateways, message-style interactions, or unclear task/event boundaries.

Use these defaults unless the user asks otherwise:

- Generate BPMN 2.0 XML with BPMN DI, not only semantic BPMN.
- Model a single end-to-end process unless the source clearly describes separate processes.
- Use lanes instead of separate pools when actors belong to the same organization or when message flow semantics are not needed.
- Avoid gateway clutter. Use gateways only when there are multiple possible paths, parallel branches, or required synchronization.
- Preserve business language from the source, but tighten labels for diagram readability.
- Do not invent system integrations, approvals, exceptions, or controls unless they are stated or are necessary assumptions.

## Quality Checks

Before completion:

- Parse the generated `.bpmn` as XML.
- Confirm every sequence flow source and target exists.
- Confirm every non-start node has at least one incoming sequence flow, unless intentionally disconnected and documented.
- Confirm every non-end node has at least one outgoing sequence flow, unless intentionally disconnected and documented.
- Confirm lanes reference only nodes that exist.
- Open the file textually if import testing is unavailable and ensure it contains `bpmn:definitions`, `bpmn:process`, `bpmndi:BPMNDiagram`, and `bpmndi:BPMNShape`.
