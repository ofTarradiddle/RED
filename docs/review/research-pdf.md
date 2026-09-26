# Research report print edition

The downloadable report is generated from the same article served at
`/research/the-measure-of-fire.html`, using `assets/research-print.css`.
The source figures and their captions are retained. Navigation, browser image
controls, the disclaimer dialog, and the table of contents are omitted from print.

The PDF is a static website asset. A content edit to the article does not regenerate
it automatically; refresh the PDF and rebuild the site together when publishing
a revised report.

## Reproduce

1. Build the site with `python -m publishing.build`.
2. Serve its output at `http://127.0.0.1:8080`.
3. Run `node scripts/export_research_pdf.cjs` with Playwright available on Node's
   module path. The script defaults to Chrome on macOS. `CHROME_PATH` selects a
   different installed Chromium browser; `RESEARCH_URL` selects another preview
   URL, and `RESEARCH_PDF_OUTPUT` selects another output location.
4. Render and inspect all PDF pages before publishing.
5. Build the site again so the final PDF is copied from
   `assets/research/the-measure-of-fire.pdf` into the generated site.

The exporter waits for fonts and source images, rejects missing content sections,
and creates a tagged PDF with document headings, page numbers, and a consistent
Hetzerk research running header.

## Verification

The current edition was exported from the completed local report and rendered
with Poppler. All six A4 pages were inspected: titles and paragraphs remain within
the page area, the selection table is intact, both source figures retain their
captions, and source notes fit without clipping. The PDF is tagged, contains
selectable text and embedded fonts, and has no PDF JavaScript or form fields.
Its opening summary matches the current article copy.
