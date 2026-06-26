# Figma / FigJam AI prompt — FundRadar coverage & expansion diagram

Paste the prompt below into FigJam AI ("Generate"), Figma First Draft, or any
AI diagram plugin. Tweak numbers if your coverage changes.

---

## PROMPT

Create a clean, professional, presentation-ready flow diagram titled
**"FundRadar — Funding Source Coverage & Expansion"**.

Layout: horizontal, left-to-right, split into THREE clearly labelled zones
separated by thin vertical dividers. Modern flat style, rounded rectangles,
sans-serif font, no drop shadows. Palette: primary blue #1D4ED8, deep navy
#1E3A8A, green #047857 for "covered / done", amber #B45309 for "pending /
blockers", light grey #F1F5F9 for surfaces.

**ZONE 1 — "Where we are today"** (left)
A 2×2 grid of metric cards, each a big number above a short label:
- 41 — Funding organisations in the database
- 11 — Organisations with data extracted
- 25 — Live opportunities collected
- 18 — Countries / blocs covered
Below the grid, a horizontal progress bar filled ~27% (11 of 41), with the
caption "30 organisations queued for processing".

**ZONE 2 — "How we cover more"** (centre)
A horizontal pipeline of four connected steps, left to right, joined by arrows:
1. Source list
2. Scraper — finds the funding pages on each site
3. AI — extracts amount, deadline, eligibility, research area
4. Dashboard + Chatbot
Beneath the "Scraper" step, attach two amber "Coverage blockers" callout boxes
with dotted connectors, each showing the problem and the fix:
- JavaScript-heavy sites  →  Fix: add Playwright (headless browser)
- PDF-only calls  →  Fix: add PDF text extraction

**ZONE 3 — "How to find & add more"** (right), two stacked parts:
(a) "Where to find them" — a central node labelled "Sources" with five small
nodes radiating from it:
- Government research councils
- Foundations & trusts
- University research offices
- Industry / CSR funds
- International & bilateral bodies
(b) "How to add one" — a vertical 3-step numbered flow:
1. Enter name + website + category in the source database
2. Run seed + pipeline (one command)
3. New opportunities appear automatically in the dashboard & chatbot
Footnote under it: "No code changes needed — the same pipeline handles any new source."

Finally, draw a curved arrow from Zone 3 back to the start of the Zone 2 pipeline,
labelled "new sources feed the pipeline", to show the growth loop.

Use small icons where helpful (database, robot/AI, magnifying glass, plus sign,
globe). Keep all text concise. Make it look like a polished slide for a project
review.

---

## Tip
If the tool makes it too busy, generate each zone as its own frame, then place
them side by side. The three zones answer, in order: *how many we cover now*,
*how we cover more*, and *how to find and add more*.
