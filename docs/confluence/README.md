# Confluence pages 01 and 02 (2026-11-05)

Builds the filled UBC SDLC template pages "01: Business Requirements" and "02 Solutions Design" for ECO-COMS from the
templates exported from Confluence (Requirements folder, `.doc` = Confluence MHTML export).

1. Extract the HTML part of each template export to `01_part1.html` / `02_part1.html` (Python `email` module).
2. Render the diagrams: `mmdc -i diagrams/<name>.mmd -o img/<file>.png -c diagrams/cfg.json -b white -s 2 -w 1600`
   (file names used by the pages: future-state, user-journey, solution-architecture, navigation-map, data-flow,
   orchestration-flow, process-workflow), plus `img/current-architecture.png` and the `img/ux-*.png` screenshots.
3. `python3 c01.py out01.html`, `python3 c02.py out02.html`.
4. `python3 package.py out01.html "01 Business Requirements - ECO-COMS"` (and 02): writes a `.docx` (landscape,
   images embedded; import with Confluence "Import Word Document") and a `.doc` in Confluence's own MHTML export format.

Unknowns (owners, tickets, production IDs, sign-off) are marked `[TBC]` in the pages.

## Filling the live pages as drafts (2026-11-06)

The template pages were created in Confluence (ISC space, under XTND-0037-XFD_SEC-Custom_Organization_Management), so
the content goes in through the editor and stays an unpublished draft:

1. `python3 record.py c01.py <01 template export> out/ops01.json` (and c02): records each change c01/c02 make,
   anchored to a table's first-cell text, a paragraph's text or a "Diagram — …" block.
2. `python3 gliffy.py diagrams/<x>.mmd out/<x>.gliffy "<name>"` then `node gliffy_png.js out/<x>.gliffy out/<x>.png`:
   real Gliffy diagrams (editable in Gliffy) plus the PNG preview the Gliffy macro shows.
3. In the browser (signed in to Confluence): upload each diagram and its PNG as page attachments, convert the page to
   editor format, replay the operations, and set the editor content, which Confluence saves as a draft.
Dev-tenant screenshots aren't published from this public repository; the Wireframes block gets placeholders.
