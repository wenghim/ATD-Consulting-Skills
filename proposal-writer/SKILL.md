---
name: proposal-writer
description: Use when creating traceable technical proposals from customer requirements and an ATD service catalog, including draft and approval workflows, requirement mapping, and DOCX formatting with reusable proposal profiles.
---

# Proposal Writer

## Core rule

Treat every reference DOCX as read-only. Learn formatting and variable locations, never source requirements or prose. Save transformed documents to a distinct output path.

## Output Location

1. If the user specifies an output folder, use that folder.
2. Otherwise, use `<active-project>/outputs/proposal-writer/`.
3. Resolve and verify the destination before creating any file.

The active project is the user's current working project or workspace, not this skill's source or installation directory. Store proposal drafts, flagged DOCX copies, transformed DOCX files, rendered previews, temporary deliverables, and final documents in the resolved external output folder. Never write them to this skill's root or any descendant.

If the current working directory is this skill's root or lies within it and the user has not supplied an external output folder, stop before writing and ask the user to choose a destination outside the skill folder. Do not create an `outputs` folder inside this skill.

During ordinary use, treat skill scripts, references, templates, profiles, manifests, tests, and assets as read-only. Write inside the skill only when the user explicitly asks to create, update, or maintain the skill itself. An explicit profile-maintenance request may update sanitized reusable resources under `references/document-profiles`; this exception never applies to proposal deliverables.

**REQUIRED SUB-SKILL:** Use `documents:documents` whenever creating or editing a DOCX, including its bundled runtime and render-inspect-iterate workflow.

## Default proposal system

Read `references/default-profile.json` whenever the user does not name another variant. It points to the ATD Technical Proposal Red profile and variable manifest. Load the linked Markdown report when typography, components, or variable decisions are needed.

Use the default automatically for new or restyled Word documents unless the user explicitly selects another catalog variant.

## Analyze a reference

1. Confirm the `.docx` exists and record its checksum.
2. Render every page at full resolution and audit OOXML structure, styles, themes, tables, images, fields, headers, and footers.
3. For an explicit skill-maintenance request, run `scripts/analyze_docx_format.py` into `references/document-profiles`.
4. Sanitize the stored profile: retain only formatting, component rules, counts, and source identity. Remove paragraph previews, requirements, scope, commercial values, company-description prose, names, screenshots, and diagrams.
5. Define reusable variables in `references/variable-manifests`. Use `{{UPPER_SNAKE_CASE}}` markers highlighted yellow (`#FFFF00`).
6. Register the profile with `scripts/update_style_catalog.py`.

For an existing document, flag variables in a separate copy:

```bash
python scripts/flag_docx_variables.py input.docx \
  references/variable-manifests/atd-technical-proposal-red.json \
  --output /path/to/active-project/outputs/proposal-writer/input-variables-flagged.docx
```

Do not replace existing values with markers unless the user requests a template. Treat client names/aliases, logos, document metadata, contacts, project identifiers, dates, durations, quantities, team details, images, and commercial values as candidates. Keep Word fields such as PAGE, TOC, SEQ, REF, and PAGEREF as fields.

## Apply a profile

1. Resolve the requested variant; otherwise use `references/default-profile.json`.
2. Run `scripts/apply_docx_profile.py` to a distinct output path.
3. Preserve target text and structure. Do not copy source text, private metadata, or source media.
4. Check that every unresolved `{{VARIABLE_NAME}}` remains yellow and report version/header/filename inconsistencies.
5. Render and inspect every page after the latest change. Fix clipping, overlap, table breakage, missing glyphs, spacing drift, and header/footer placement before delivery.

## Common mistakes

| Mistake | Correction |
|---|---|
| Copy source prose into a template | Store semantic slots and formatting only. |
| Apply in place | Always create a separate output. |
| Guess a conflicting version | Keep `{{DOCUMENT_VERSION}}` flagged until confirmed. |
| Deliver after XML checks | Render and visually inspect every page. |

Read `references/profile-schema.md` when extending profile fields and `references/master-style-catalog.json` when selecting non-default variants.
