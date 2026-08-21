# BPMN Modelling Guide

## Element Choices

Use start events for triggers, end events for outcomes, tasks for work, gateways for control flow, and intermediate events for waits, timers, messages, or externally triggered pauses.

Prefer these task types:

- `userTask`: A person uses a system or form to complete work.
- `manualTask`: A person performs work outside a system.
- `serviceTask`: A system performs automated work.
- `businessRuleTask`: A decision table, policy rule, or rules engine determines an outcome.
- `sendTask` / `receiveTask`: The process explicitly sends or receives information.
- `task`: Use when the source does not justify a more specific type.

Use gateway types carefully:

- `exclusiveGateway`: Exactly one path is taken.
- `parallelGateway`: Multiple branches all happen, or multiple branches must all complete.
- `inclusiveGateway`: One or more paths may happen based on conditions.

## Actor And Lane Heuristics

Create lanes for stable responsibility boundaries: role, team, department, external partner, or system. Do not create a lane for every named person unless the process is person-specific.

Use separate pools only when the model needs message-flow semantics between independent participants. The bundled generator creates one executable-style process pool with lanes; if separate pools are required, create the BPMN XML manually and validate it carefully.

## Extraction Checklist

When reading source content, capture:

- Process trigger.
- Primary happy path.
- Roles or systems responsible for each activity.
- Decisions and branch conditions.
- Parallel work and joins.
- Exception, rejection, rework, escalation, and cancellation paths.
- Business outputs and end states.
- Inputs, records, approvals, controls, or evidence created by tasks.

## Labeling

Use short, action-oriented labels:

- Good: `Validate invoice`, `Approve exception`, `Notify requester`.
- Avoid: `The finance team needs to validate whether the invoice is correct`.

Name gateways as questions only when it improves readability, for example `Complete?`, `Approved?`, or `Data valid?`.

## Common Patterns

Approval:

1. Submit request.
2. Review request.
3. Exclusive gateway `Approved?`.
4. Approved branch continues.
5. Rejected branch notifies requester or ends as rejected.

Rework:

1. Review output.
2. Exclusive gateway `Changes needed?`.
3. Yes branch goes to `Revise output`.
4. Revision loops back to review.
5. No branch continues.

Parallel work:

1. Parallel gateway splits work.
2. Each branch performs independent activity.
3. Parallel gateway joins before dependent activity.

Exception:

1. Keep exception paths explicit when source content mentions escalation, rejection, cancellation, missing information, failed validation, or timeout.
2. Use concise branch labels such as `Invalid`, `Missing information`, or `Timed out`.
