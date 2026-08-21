# ATD Technical Proposal Red

Use this as the default `proposal-writer` formatting system. It was distilled from the named source at the checksum recorded in the JSON profile. The source itself remains read-only.

## Typography and semantic roles

| Role          | Font               |  Size | Treatment         | Spacing/alignment                           |
| ------------- | ------------------ | ----: | ----------------- | ------------------------------------------- |
| Body          | Calibri            | 11 pt | Black             | Standard left-aligned body copy             |
| Title         | Source title style | 28 pt | Cover-specific    | Centered within the bordered identity panel |
| Heading 1     | Calibri            | 16 pt | Bold, `#C00000`   | 14 pt before, 6 pt after                    |
| Heading 2     | Calibri            | 13 pt | Bold, `#C00000`   | 10 pt before, 4 pt after                    |
| Heading 3     | Calibri            | 12 pt | Bold, `#C00000`   | 8 pt before, 4 pt after                     |
| Caption       | Calibri            |  9 pt | Italic, `#0E2841` | Centered, 10 pt after                       |
| Quote/callout | Calibri            | 11 pt | Italic, `#404040` | Centered with 43.2 pt side indents          |
| Header        | Calibri            | 11 pt | `#595959`         | 3 pt after, gray bottom rule                |
| Footer        | Calibri            | 11 pt | Black             | Right-aligned page number, black top rule   |

The OOXML theme declares Aptos Display/Aptos, but the document defaults explicitly use Calibri 11 pt. Calibri is therefore authoritative for reproduced content.

## Page and color system

- A4 portrait: 8.2681 × 11.6931 inches.
- Margins: 0.75 inch on all sides; header/footer distance 0.4917 inch.
- Primary red: `#C00000`.
- Table key-column fill: `#FAF0F0`.
- Table header: red fill, bold white centered text, thin black grid.
- Links: muted blue `#467886`; captions: dark blue `#0E2841`.

## Components

- Cover: client logo, bordered centered proposal identity panel, provider brand block, and highlighted variable markers.
- Header: fixed ATD visual shell; year, document type, confidentiality label, and version are variables.
- Footer: automatic right-aligned page number with a top rule.
- TOC: live Word TOC field; update fields before delivery.
- Figures: centered; use task-supplied images and a centered italic caption below.
- Tables: use the red/white header and pale-red key column consistently.

## Content boundary

This profile contains formatting only. It excludes requirements, scope, proposal narrative, commercial values, company-description prose, names, source screenshots, and source diagrams. Use the companion variable manifest for placeholders and yellow highlighting.
