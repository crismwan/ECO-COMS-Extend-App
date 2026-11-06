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
