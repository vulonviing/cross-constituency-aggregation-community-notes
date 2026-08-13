# figures/

Every figure in the paper lives in `script_figures/` and is produced by a
standalone script. There is no notebook execution step and no separate figure
directory in this checkout.

## The five paper figures

| Script | Paper | What it shows |
|---|---|---|
| `fig1-rater-dominance.py` | Figure 1 | Conceptual schematic: repeated participation gives a small set of highly active raters outsized weight. Self-contained, no data dependency. |
| `fig2-dataset-construction.py` | Figure 2 | The sample-construction funnel, 1.7M English notes down to the 100k dense slice. |
| `fig3-rescue-panels.py` | Figure 3 | Coverage, cluster, and validation panels for the CCA outcome. |
| `cn-gemma-validation-funnel.py` | Figure 4 | The two-stage Gemma validation of the 13,655-note rescue pool. |
| `cn-topic-signatures.py` | Figure 5 | Average approval by constituency across 13 subject areas. |

Regenerate any of them in place:

```bash
python figures/script_figures/fig2-dataset-construction.py
```

Each script writes its own `.pdf` and `.png` beside itself at 300 dpi with
`bbox_inches="tight"`. The paper includes the `.pdf` versions directly, so a
regenerated figure flows into the manuscript on the next `latexmk` run.

## The naming rule

Each figure exists as **three files sharing one basename**:

```
figures/script_figures/
    <name>.py        ← generating script
    <name>.pdf       ← vector output, used by the paper
    <name>.png       ← raster output, for slides and previews
```

The figure and the code that produces it always sit side by side. This rule is
also stated in `AGENTS.md`.

Figures 1 through 3 are named for what they show; the `cn-` prefix on Figures 4
and 5 is historical and carries no meaning beyond the project name.
