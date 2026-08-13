# figures/

Every figure in the paper lives in `script_figures/` and is produced by a
standalone script. There is no notebook execution step and no separate figure
directory in this checkout.

## The five paper figures

| Script | Paper | What it shows | Needs |
|---|---|---|---|
| `fig1-rater-dominance.py` | Figure 1 | Conceptual schematic: repeated participation gives a small set of highly active raters outsized weight. | nothing |
| `fig2-dataset-construction.py` | Figure 2 | The sample-construction funnel, 1.7M English notes down to the 100k dense slice. | committed data **plus** `data/interim/ratings_clustered.parquet` |
| `fig3-rescue-panels.py` | Figure 3 | Coverage, cluster, and validation panels for the CCA outcome. | committed data |
| `cn-gemma-validation-funnel.py` | Figure 4 | The two-stage Gemma validation of the 13,655-note rescue pool. | committed data |
| `cn-topic-signatures.py` | Figure 5 | Average approval by constituency across 13 subject areas. | nothing (values baked in) |

Regenerate any of them in place:

```bash
python figures/script_figures/fig3-rescue-panels.py
```

Four of the five run on a fresh clone. Figure 2 additionally reports the total
rating-edge count, which only `ratings_clustered.parquet` carries; that file is
too large for Git and is fetched with `scripts/fetch_interim_from_hf.sh` (see
[REPRODUCING.md](../REPRODUCING.md), tier B). Running it without that file stops
with a message saying so.

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
