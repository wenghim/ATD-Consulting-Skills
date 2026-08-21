# ATD Services Catalog Output Template

Generate or update `ATD_Services_Catalog.md` with the following structure. Keep the two required business sections in this order. Add the quality-review section after them.

```markdown
# ATD Services Catalog

| Catalog Field | Value |
|---|---|
| Last Updated | YYYY-MM-DD |
| New or Revised Sources in This Run | Number |
| Total Analyzed Sources | Number |
| Catalog Quality Status | Pass / Needs Review |

## 1. Project Summary

| Project ID | Project Name | Client Company | Region | Project Period | Evidence Type | Source Document | Reference | QC Status |
|---|---|---|---|---|---|---|---|---|
| PRJ-001 | Evidence-based project name | Full client company name | MY / SG / HK / other ISO alpha-2 code / Unknown | Dates or Unknown | Proposed / Conditional / Committed / Reported Delivered / Delivered / Unverified | Full original filename | Page and section, clause, table, slide, heading, or cell range | Verified / Needs Review |

## 2. Consolidated Available Services / Scope of Work

| No. | Standard Service Name | Scope / Service Description | Key Deliverables | Service Domain | BDAT Domain | Client / Project | Source and Reference | QC Status |
|---:|---|---|---|---|---|---|---|---|
| 1 | Canonical name from taxonomy | Concise evidence-faithful scope and boundaries | Evidence-based deliverables or Not stated | Controlled service domain | Controlled BDAT value | Full client name / project | Full original filename — precise page, section, clause, table, slide, heading, or cell reference; use `<br>` for multiple source-reference pairs | Verified / Needs Review |

## 3. Quality Review

| Check | Result | Notes |
|---|---|---|
| Source traceability | Pass / Needs Review | Missing or weak references |
| Scope accuracy | Pass / Needs Review | Conflicts, exclusions, or unsupported wording |
| Consolidation and naming | Pass / Needs Review | Duplicate or uncertain mappings |
| Domain classification | Pass / Needs Review | Uncertain service-domain or BDAT decisions |
| Incremental processing | Pass / Needs Review | Register reconciliation result |

### Items Requiring Review

| Review ID | Item | Issue | Sources | Required Resolution |
|---|---|---|---|---|
| REV-001 | Service, project, or document | Concise ambiguity or conflict | Full filenames and references | Decision or evidence needed |
```

## Consolidation Rules

- Keep one project-summary row per project and evidence state when source documents describe materially different proposed, committed, or delivered positions.
- Keep one service row per materially distinct canonical service. Combine multiple clients, projects, and references in the same row only when the service purpose, activities, boundaries, and deliverables remain equivalent.
- Assign stable sequential `PRJ-###` identifiers to project-summary records. Number consolidated services with a normal sequential index such as `1`, `2`, `3`, `4`, `5` in the current display order; do not use service IDs.
- Combine every full source filename with its precise reference in one `Source and Reference` cell. Use `<br>` between multiple source-reference pairs.
- Preserve proposed, conditional, committed, and delivered distinctions in the Project Summary and evidence-faithful scope wording when material. Do not add a lifecycle column to the consolidated-services table.
- Keep unexercised optional scope `Conditional` even when it appears in an approved proposal. Use `Reported Delivered` when a final report lacks acceptance or sign-off evidence.
- Record `Not stated` or `Unknown` instead of filling evidence gaps.
- Include `Items Requiring Review` even when empty; write `None` when the quality gate passes without exceptions.
