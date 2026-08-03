# Figure Quality Overhaul and Script Isolation

- **Date:** 2026-06-26 21:18 +0200
- **Source:** Paper discussion

## Context
The current figures are not of publishable quality. Both the hand-made
`figures/script_figures/` outputs and the notebook-generated
`figures/notebook_figures/` outputs need substantial refinement before they
can support the manuscript. The existing scripts are interleaved with notebook
logic and side-effect rendering, which makes targeted updates hard.

## Idea
Acknowledge the current state of the figures as a known weak spot, then run a
dedicated pass: isolate the script behind each existing figure so it can be
edited and re-rendered independently of the notebooks. Once each script stands
alone, update the rendering (styling, labels, data plumbing) to bring the
figures up to paper standard. Documentation-only is not enough; the work is to
re-derive clean, isolated generators from the old figure scripts and refresh
the outputs.

## Why It Matters
Figures are load-bearing in the paper. Readers evaluate the cluster
signatures, rescue panels, and topic distributions visually before reading the
surrounding prose. Weak or inconsistent figure quality undermines the
credibility of the analysis and makes the manuscript harder to revise. Isolating
each figure script also makes future iterations cheaper: a single style change
or data update no longer requires re-running an entire notebook.

## Follow-up
Start with the hand-made figures in `figures/script_figures/` (the four
existing triplets) and extract each into a self-contained script that reads
from `data/` and writes to `figures/script_figures/`. Then move to the
notebook-generated figures in `figures/notebook_figures/` and produce matching
standalone scripts for each. Track progress in the step log as each figure is
isolated and refreshed.
