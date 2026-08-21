---
name: atd-services-catalog
description: Use when building or updating an ATD services catalog from approved or submitted proposals, statements of work, project final reports, completion reports, or similar delivery evidence, especially when documents accumulate over time and only new or revised sources should be analyzed.
---

# ATD Services Catalog

## Overview

Build a traceable catalog of services and scope of work evidenced by past projects. Consolidate equivalent services under controlled names, verify every captured item against its source, and process source collections incrementally.

## Output Location

1. If the user specifies an output folder, use that folder.
2. Otherwise, use `<active-project>/outputs/atd-services-catalog/`.
3. Resolve and verify the destination before creating any file.

The active project is the user's current working project or workspace, not this skill's source or installation directory. Never write generated deliverables, working files, temporary deliverables, or processing state to this skill's root or any descendant.

If the current working directory is this skill's root or lies within it and the user has not supplied an external output folder, stop before writing and ask the user to choose a destination outside the skill folder. Do not create an `outputs` folder inside this skill.

During ordinary use, treat skill scripts, references, templates, profiles, manifests, tests, and assets as read-only. Write inside the skill only when the user explicitly asks to create, update, or maintain the skill itself.

## Required References

Read all three files before analyzing sources:

1. `references/service-taxonomy.md` for canonical naming and classification.
2. `references/output-template.md` for the catalog structure.
3. `references/processing-register.md` for document identity and skip logic.

## Deliverables

Maintain exactly two Markdown files together in the resolved external output folder unless the user requests different names:

- `ATD_Services_Catalog.md`: the single business deliverable.
- `ATD_Services_Catalog_Processing_Register.md`: the operational audit record.

Do not create separate extraction reports for individual documents.

Use the resolved output folder as the base for relative source paths recorded in the processing register.

## Workflow

1. **Locate inputs and existing outputs.** Recursively inventory supported proposal, SoW, change-control, completion, and final-report documents. Leave source files untouched.
2. **Load the register before reading source content.** Create it from `references/processing-register.md` only when it does not exist.
3. **Match candidates against the register.** Use the exact source filename plus relative path as the default registry key. Skip a successfully processed current entry when it is already registered. Use stored size and modified time to flag a likely changed revision. Do not calculate SHA-256 by default; use a content hash only when the user requests it or when a rename, duplicate, or revision cannot be resolved from the register and document evidence.
4. **Analyze only eligible documents.** Read each eligible document fully enough to capture project metadata, explicit services, activities, deliverables, exclusions, options, and delivery evidence. Use OCR or the appropriate document-reading capability when ordinary extraction is incomplete.
5. **Separate lifecycle evidence.** Classify source evidence without collapsing different meanings:
   - approved or signed proposal, contract, SoW, or change request: `Committed`
   - submitted but unapproved proposal: `Proposed`
   - optional or conditional scope not formally exercised: `Conditional`
   - accepted or signed final or completion report: `Delivered`
   - final or completion report without acceptance evidence: `Reported Delivered`
   - draft or unclear source: `Unverified`
   Do not classify an option as committed merely because it appears in an approved document. A final report proves delivery only to the strength of its acceptance evidence; it does not silently redefine the originally committed scope.
6. **Normalize services.** Apply `references/service-taxonomy.md`. Merge services only when their purpose, activities, and deliverables are materially equivalent. Preserve distinct variants when scope differs.
7. **Update the catalog.** Consolidate evidence into the existing service row when appropriate and append each full source filename together with its precise reference in the combined evidence cell. Add a new row only for a materially distinct service.
8. **Perform the quality gate.** Re-open every cited passage and verify that the standardized name, scope summary, lifecycle status, client, region, domain, BDAT classification, and deliverables remain faithful to the evidence. Check the source again for omitted scope and exclusions.
9. **Commit processing state last.** Update the processing register only after the catalog update and quality gate succeed. Record affected project IDs and standard service names. Record failed extraction or unresolved evidence as retryable; never mark it analyzed.

If no eligible documents remain, do not rewrite the catalog. Report that no new or revised sources were found.

## Evidence and Conflict Rules

- Cite the full original filename plus page and section, clause, table, slide, heading path, or sheet/cell range where available.
- Use `Unknown` for an unsupported client, region, date, or project fact. Use ISO 3166-1 alpha-2 region codes such as `MY`, `SG`, and `HK` only when supported by evidence.
- Resolve committed scope from approved contractual evidence and delivered scope from accepted completion evidence. Retain both when they differ.
- Prefer explicit evidence over inference. If equally authoritative sources conflict, mark `Needs Review` and describe the conflict; do not guess.
- Treat domain and BDAT values as analyst classification, not quoted source facts, and verify them against the controlled taxonomy.
- Do not catalog recommendations, examples, marketing claims, staff credentials, or generic capabilities unless the source explicitly places them in project scope or reports them as delivered.

## Quality Gate

The catalog passes only when:

- every service row has at least one locatable source reference;
- each reference points to a successfully analyzed register entry;
- every scope statement is supported and exclusions are not presented as services;
- duplicate services are consolidated by meaning, not label similarity alone;
- revised documents remain traceable and unchanged documents are not reanalyzed;
- unresolved ambiguity is visible as `Needs Review`; and
- rerunning with the same registered source inventory produces no catalog changes.
