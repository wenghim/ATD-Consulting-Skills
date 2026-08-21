# Processing Register Contract

Maintain `ATD_Services_Catalog_Processing_Register.md` beside the catalog. This file is an operational audit record, not a second business deliverable.

## Required Structure

```markdown
# ATD Services Catalog Processing Register

| Register Field | Value |
|---|---|
| Register Version | 1.0 |
| Last Updated | YYYY-MM-DD |
| Catalog File | ATD_Services_Catalog.md |

## Documents

| Document ID | Source Filename | Relative Path | Size (Bytes) | Modified Time | Document Type | Client / Project | Analysis Status | Revision Status | Analyzed Date | Catalog Entries | Supersedes | Duplicate Of | Notes |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|
| DOC-001 | Full original filename | Path relative to the source root | Integer or Unknown | ISO timestamp or Unknown | Approved Proposal / Submitted Proposal / SoW / Change Request / Final Report / Completion Report / Other | Full client / project or Unknown | Analyzed / No Relevant Scope / Duplicate / Failed / Unsupported | Current / Superseded / Duplicate Copy / Unknown | YYYY-MM-DD or blank | PRJ-### values and standard service names, or None | Prior revision Document ID or None | Original Document ID or None | Concise outcome, verification note, or retry reason |
```

## Registry Matching and Skip Rules

1. Assign each registered document a stable sequential `DOC-###` identifier. Never renumber an existing row.
2. Use the normalized combination of `Relative Path` and `Source Filename` as the default registry key. Normalize path separators and redundant `./` segments, but preserve the actual filename in the table.
3. Skip content analysis by default when that key has either a `Current` row with status `Analyzed` or `No Relevant Scope`, or a row with status `Duplicate` and a populated `Duplicate Of` value, provided the stored size and modified time do not indicate a change.
4. When the key is absent, analyze the document as new.
5. When the key exists but stored size or modified time differs, treat the file as a likely revision and analyze it. Add a new `DOC-###` row, link it through `Supersedes`, retain the prior row's successful `Analysis Status`, and set its separate `Revision Status` to `Superseded`.
6. When size or modified time is unavailable, use the registry-key match unless the user or document inventory indicates that the file was replaced or revised.
7. Retry `Failed` entries on future runs. Revisit `Unsupported` entries when a suitable extraction capability becomes available.
8. Do not calculate SHA-256 during normal registry checks. Use a content hash only when explicitly requested or when a suspected rename, duplicate, or revision remains ambiguous after comparing the register, metadata, and extracted document evidence.

## Update Transaction

For each eligible document:

1. Extract and analyze the source.
2. Update and quality-check the catalog.
3. Record the affected stable project IDs and standard service names.
4. Only then write `Analyzed` or `No Relevant Scope` to the register.

If extraction, evidence verification, or catalog writing fails, record `Failed` with the reason and leave the document eligible for retry. This order prevents the register from suppressing an incomplete catalog update.

## Revision and Duplicate Handling

- Do not delete historical register rows.
- Do not silently replace evidence from an older revision.
- If multiple rows have the same registry key, use the single row marked `Current` for the next-run comparison.
- Treat a renamed or relocated file as new by default. Mark it `Duplicate` only when matching content is confirmed by document comparison, user confirmation, or an optional content hash. Set `Revision Status` to `Duplicate Copy`, populate `Duplicate Of` with the original `DOC-###`, and reserve `Supersedes` for revision chains.
- Use authority by evidence purpose: approved contractual sources establish `Committed`; accepted final reports establish `Delivered`.
- If a revision changes evidence, update the catalog and retain the previous source reference when needed to explain committed-versus-delivered differences.
- If the same content is confirmed in multiple files, retain one analyzed entry and link the copies as duplicates.

## Register Quality Checks

- Every catalog source appears in the register with a successful status.
- Every successful non-duplicate source has catalog entries or the result `No Relevant Scope`.
- Every non-duplicate source filename and relative-path key maps to no more than one `Current` register row.
- Every `Supersedes` value points to an existing Document ID.
- Every `Duplicate Of` value points to an existing successfully processed Document ID.
- Re-running a source collection already matched by the register produces zero eligible documents and no catalog change.
