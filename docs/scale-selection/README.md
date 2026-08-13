# docs/scale-selection/

Why the analysis runs at 200,000 raters and not at some other size.

Two reports, written while the decision was being made, in the order they were
produced:

| Report | What it does |
|---|---|
| [`SCALE_UP_V2_INTERIM_REPORT.md`](SCALE_UP_V2_INTERIM_REPORT.md) | The full technical comparison: every variant, every `k`, all three eigensolvers, with a glossary and the rules the experiment was run under. |
| [`SCALE_UP_V3_DECISION_REPORT.md`](SCALE_UP_V3_DECISION_REPORT.md) | The decision document: four options laid out with their trade-offs, and the case for the one that was chosen. |

Together they source every number in Table 1 of the paper, including the
between-camp Pearson correlations and discriminating shares, which the committed
diagnostics alone cannot reproduce.

## Reading the path references

Both reports were written against the cluster's directory layout and refer to
paths that do not exist in this repository. The mapping:

| Path in the reports | Where it is now |
|---|---|
| `data/full_spectral_fast_<solver>_<scale>/interim_B/` | Small diagnostics in [`data/scale-ladder/<run>/`](../../data/scale-ladder/); the heavy files are on Hugging Face or dropped, see that directory's README |
| `data/full_spectral_fast_amg_200k_reassigned/interim_B/` | The production run, promoted to [`data/interim/`](../../data/interim/) |
| `hedge/src/spectral_fast.py` | [`src/spectral_fast.py`](../../src/spectral_fast.py) |
| `hedge/SCALE_UP_V2_PLAN.md`, `hedge/SCALE_UP_MEMO.md` | Planning documents, not part of this checkout |
| `data/full/interim_expanded_20260509_1756/` (30k) | The earlier 30k baseline, superseded and not carried here |

## Two things the reports do not reflect

They were written before the manuscript was finished, so their terminology drifts
from the paper's in two places. The paper calls the vote-profile rule **Method
B**, which the reports sometimes call the reassignment or Option C. And the
reports describe 30k as the then-current baseline; the paper reports only the
200k production run.

The numbers themselves did not change. Where a report and the paper state the
same quantity, they agree.
