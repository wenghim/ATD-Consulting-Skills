# ATD Technical Proposal Variables

Use `{{UPPER_SNAKE_CASE}}` markers and apply yellow `#FFFF00` highlighting to every unresolved marker. Remove highlighting only after the value is supplied and the document-wide consistency check passes.

## Variable groups

- Client: logo, legal name, short name, client-specific possessive forms.
- Document: proposal type, document type, year, version, confidentiality label, prepared date.
- Project and procurement: project title, duration, AOR number, procurement reference, quantities.
- Contact: contact person and provider contact details.
- Solution and media: solution name/logo, team names/roles/photos, figures, and captions.
- Commercial and timeline: currency, fees, tax treatment, payment milestones/percentages, dates, durations, and milestones.

The source contains 147 short-client-name occurrences, six legal-name occurrences, and nine unresolved placeholders. The filename/header version mismatch must remain flagged until the user confirms the authoritative version.

## Safety rules

- Flag existing values in a separate output copy; never edit the source in place.
- Do not replace existing content with markers unless explicitly requested.
- Do not copy requirements, scope, company-description prose, proposal narrative, screenshots, or commercial source values into a template.
- Treat page numbers, TOC references, caption sequence numbers, and cross-references as Word fields rather than manual variables.
