# COMS presentation, 7 November 2026

The full COMS on Workday Extend deck, refreshed for 7 November (32 slides).

| File | What it is |
|---|---|
| `ECO-COMS-Presentation-2026-11-07.pptx` | The deck, with speaker notes on every slide |
| `ECO-COMS-Presentation-2026-11-07.pdf` | The same deck as a PDF |
| `ECO-COMS-Presentation-2026-11-07.mp4` | Narrated video: each slide shown for the length of its narration |
| `audio/slide-NN.mp3` | The narration for each slide on its own, to play or replace one slide at a time |
| `narration.md` | The narration text for every slide (what the audio says) |

## What changed from the 6 November deck

- Title slide dated 7 November.
- Slide 8, **This week**: the changes of 6–7 November (picked from Workday, checked twice at scale, rules or regex, the value stream map, the XTND / IORC naming standard, more gates on deploy).
- Slide 14, new, **Product tour · 5: Picked from Workday, not typed**: three screenshots from the development tenant (the Subject list, the Academic Period list, the filled form). The later product-tour slides moved up by one.
- Slide 22, schema-driven: rules or regex per column, and the Workday checks are built (they were "still to do").
- Slide 26, engineering: App Builder validation and Arcane Auditor in every deploy; 513 commits, 32 test suites.
- Slide 27, at a glance: counts from the repository on 7 November.

## How it was made

The deck was edited from the 6 November deck with python-pptx. The narration comes from each slide's speaker notes (headings, delivery tips and bracketed prompts left out), read by the Kokoro text-to-speech model (voice am_michael), the same voice as the 5 November videos. The video is each slide rendered at 1920×1080 with its narration, joined with ffmpeg. To change one slide's narration, edit its speaker notes and rebuild that slide's audio and the video.
