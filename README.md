# Cross-Constituency Aggregation for Community Notes

Emrecan Ulu and Jingyao Shi — University of Konstanz

On X, ordinary users write fact-checks on posts and rate each other's work. Only
the notes the crowd agrees on ever appear under a post. Defining that agreement
is the whole problem: count raw votes and the larger side wins every time, so a
note can be buried by the group it makes uncomfortable rather than by anything
wrong with it.

Cross-Constituency Aggregation (CCA) settles it differently. Readers are first
sorted into groups by how they actually vote, and a note then has to earn
approval from each group separately. Enthusiasm from one camp cannot make up for
rejection by another, no matter how large that camp is.

Run against real Community Notes data covering 44,722 posts, the rule qualifies
**20,405** notes — and **13,655** of them are notes X never showed to anyone. Of
those hidden notes, **8,558** still hold up when an independent language model
checks them for sourcing and quality.

Underneath, this is a 100k-note, 200k-rater pipeline: spectral clustering over a
co-rating graph, vote-profile reassignment of outlier raters, and a
geometric-mean score, validated end to end with Gemma 4 31B IT. Every number
above can be re-derived from the files in this repository.

## Start here

| If you want to | Go to |
|---|---|
| **Read the paper** | [`paper/main.pdf`](paper/main.pdf) |
| **See the final talk** (July 2026) | [`community-notes-final-presentation.pdf`](docs/presentations/11-07-2026-community-notes-final/community-notes-final-presentation.pdf) |
| **See the class talk** (June 2026) | [`CCA_presentation.pdf`](docs/presentations/25-06-2026-1408-class_presentation/CCA_presentation.pdf) |
| **Check a number in the paper** | [REPRODUCING.md](REPRODUCING.md) — maps every result to the file that produced it |
| **Verify the results yourself** | `python run_tests.py` — 68 tests, no data downloads needed ([last run](tests/RESULTS.md)) |
| **Read the method** | [`src/`](src/) for the implementation, [`notebooks/`](notebooks/) for the stages |
| **Find a data file** | [`data/README.md`](data/README.md) |
| **Reuse this work** | [Licensing](#licensing) |

## Repository Map

```text
.
├── paper/                   # The manuscript, source and PDF
├── REPRODUCING.md           # Paper result -> source file, with runnable snippets
├── run_tests.py             # Runs all 68 tests
├── tests/                   # Aggregation-rule units + paper-number regressions
├── src/                     # Reusable Python implementation
├── notebooks/               # Canonical pipeline notebooks
│   └── llm_validation/      # Gemma validation package and its own tests
├── data/                    # All derived artifacts (see data/README.md)
│   ├── interim/             # Clustering outputs and the canonical partition
│   ├── processed/           # Scoring, selection, and topic outputs
│   ├── scale-ladder/        # Diagnostics from all 42 scale runs, backing Table 1
│   └── llm_validation/      # Gemma run records, auditable call by call
├── figures/script_figures/  # Paper figures, each with its generating script
├── jobs/                    # Job scripts that run the notebooks on a cluster
├── scripts/                 # Hugging Face helpers and the checksum verifier
├── docs/
│   ├── presentations/       # The two talks given on this work
│   └── scale-selection/     # Why the analysis runs at 200k
└── raw/                     # Local snapshot inputs (contents gitignored)
```

## Canonical Stages

1. `notebooks/00_ingest.ipynb`
2. `notebooks/01_clustering.ipynb`
3. `notebooks/02_scoring.ipynb`
4. `notebooks/03_topics.ipynb`
5. `notebooks/llm_validation/` (canonical Gemma validation)
6. `notebooks/06_plots.ipynb`
7. `notebooks/07_paper_visuals.ipynb`

Each stage is submitted through one command:

```bash
jobs/submit_stage.sh [--dry-run] <stage>
```

Supported stages: `ingest`, `clustering`, `scoring`, `topics`, `plots`,
`paper_visuals`. Canonical validation uses the separate
`jobs/submit_llm_validation.sh` interface.

Notebooks are the single source of truth. Jobs execute them for their data and figure side-effects and do not persist executed copies.

`TEST_MODE=1` in `config.txt` isolates all smoke-test output under
`.artifacts/smoke/`. Production output always uses the root paths shown above.

The three oversized files below are not stored in Git. See
[Large Local Data](#large-local-data) for their Hugging Face paths, and fetch
or upload them with `scripts/fetch_interim_from_hf.sh` and
`scripts/upload_interim_to_hf.sh`.

## Large Local Data

Three files are never committed to Git (see `.gitignore`) because they exceed
GitHub's size limits. All three are mirrored on the
`vulonviing/community-notes-rescue-interim` Hugging Face dataset repo:

| File | Size | Hugging Face path |
|---|---|---|
| `data/master_full.parquet` | ~6.6 GB | `master/master_full.parquet` |
| `data/interim/ratings_filtered.parquet` | ~3 GB | `200k/ratings_filtered.parquet` |
| `data/interim/ratings_clustered.parquet` | ~3 GB | `200k/ratings_clustered.parquet` |

Fetch all three with:

```bash
scripts/fetch_interim_from_hf.sh
```

If the dataset is ever rotated or re-created, confirm it still holds current
uploads before relying on it (`hf download --repo-type=dataset
vulonviing/community-notes-rescue-interim --include "master/*.parquet"
"200k/*.parquet"` or check the HF web UI) — re-upload with
`scripts/upload_interim_to_hf.sh` if it does not.

### The Scale Ladder Mirror

**Read this first if you are coming back to the project after a long gap.**

Before settling on 200,000 raters, we ran the clustering at many scales and with
three different eigensolvers — forty-five runs in all, of which forty-two
produced output. Table 1 of the paper reports six of them, and its footnote
turns on the pattern across all nineteen AMG runs. Those runs lived only in
`/work/<user>/cnotes_all/data/full_spectral_fast_*/interim_B/` on the University
of Konstanz cluster, and a cluster account does not outlive a degree.

They are now mirrored under `scale-ladder/` on the same
`vulonviing/community-notes-rescue-interim` dataset, one folder per run:

| What | Where | Size |
|---|---|---|
| Small diagnostics (stability, silhouette, cluster summary, graph, runtime) | committed to this repo, [`data/scale-ladder/`](data/scale-ladder/) | ~1.3 MB |
| Per-rater cluster assignments and vote statistics (`user_clusters*`, `user_stats`) | Hugging Face `scale-ladder/<run>/` | ~845 MB |
| `ratings_filtered`, `ratings_clustered`, `embedding` | **kept nowhere** | 373 GB on the cluster |

The third row is deliberate. Those files are joins and embeddings derived from
`master_full.parquet`, which is mirrored in the same dataset, so they can be
rebuilt from what was kept. The first two rows cannot be rebuilt at all without
re-running days of cluster compute against a snapshot of X that no longer
exists — that is the whole reason for the mirror.

Fetch a run:

```bash
hf download vulonviing/community-notes-rescue-interim --repo-type=dataset \
    --include "scale-ladder/full_spectral_fast_amg_200k/*" --local-dir .
```

`scale-ladder/MANIFEST.md` in the dataset lists every run with its solver,
selected `k`, ARI, and cluster sizes, so the mirror stays readable on its own.
To refresh or rebuild it from the cluster, run
[`scripts/backup_scale_ladder_to_hf.sh`](scripts/backup_scale_ladder_to_hf.sh)
there; it uploads the whole selection in one commit, since the Hub allows only
128 commits an hour.

### Raw Data Provenance

`data/master_full.parquet` is the direct output of `notebooks/00_ingest.ipynb`
run against the official Community Notes snapshot
(`notes-*.tsv`, `ratings-*.tsv`, `noteStatusHistory-00000.tsv` from
<https://x.com/i/communitynotes/download-data>). X's published snapshot
changes continuously — new notes, ratings, and status updates are added over
time — so re-downloading it today and re-running ingest will **not**
reproduce the exact same `master_full.parquet`, and downstream
clustering/scoring numbers may shift as a result.

The snapshot behind this repository's `master_full.parquet` (and therefore
behind every committed `data/interim/`, `data/processed/`, and
`data/llm_validation/` artifact) was retrieved on **2026-05-08**. Anyone who
needs this exact historical result set should use the committed
`data/interim/`, `data/processed/`, and `data/llm_validation/` outputs (or
fetch `master_full.parquet` from Hugging Face above) rather than
re-downloading raw inputs from X.

## How To Run

### Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Place the Community Notes snapshot and FastText files under `raw/`; see
`raw/PUT_SOURCE_FILES_HERE.md`.

### Running From Scratch

How much you need to fetch or run depends on what you are trying to do:

1. **Just read the results / build the paper.** No download needed. Cloning
   this repository already gives you `data/processed/`, `data/interim/` (except
   the two oversized ratings files), and `data/llm_validation/` — everything
   the paper and its figures are built from. Skip straight to
   [Build The Paper](#build-the-paper).
2. **Re-run clustering/scoring/topics to check the pipeline.** You do not need
   the raw X snapshot. Run `scripts/fetch_interim_from_hf.sh` to pull
   `master_full.parquet` and the two interim ratings files (see
   [Large Local Data](#large-local-data)), then start from
   `notebooks/01_clustering.ipynb` onward — `data/master_full.parquet` is
   `01_clustering.ipynb`'s input.
3. **Reproduce ingestion itself from raw X data.** Download a fresh snapshot
   from the official links in `raw/PUT_SOURCE_FILES_HERE.md` and the FastText
   language model, place them under `raw/`, then run `00_ingest.ipynb` onward.
   Read [Raw Data Provenance](#raw-data-provenance) first: X's snapshot changes
   over time, so a newly downloaded snapshot will not reproduce this
   repository's exact `master_full.parquet` or its downstream numbers.

### Smoke Test

Set `TEST_MODE=1` in `config.txt`. Smoke runs use a small input slice and write
only under `.artifacts/smoke/`.

```bash
for stage in ingest clustering scoring topics plots paper_visuals; do
  jobs/submit_stage.sh --dry-run "$stage"
done
```

Submit the stages in order:

```bash
jobs/submit_stage.sh ingest
jobs/submit_stage.sh clustering
jobs/submit_stage.sh scoring
jobs/submit_stage.sh topics
jobs/submit_stage.sh plots
jobs/submit_stage.sh paper_visuals
```

### Production Run

1. Put the raw snapshot and FastText files in the root `raw/` directory.
2. Install any missing packages in the active Python environment, including `pyamg`.
3. Set `TEST_MODE=0` in `config.txt`.
4. Submit the six stages in the order shown above.

The production clustering configuration is fixed at 100,000 notes and 200,000
users. Downstream stages always consume Method-B reassigned clusters from
`data/interim/user_clusters_method_b_voteprofile.parquet`.

`jobs/submit_stage.sh` and `jobs/submit_llm_validation.sh` target an SGE-style
scheduler (`qsub`/`qstat`/`qacct`); adapt the queue names and resource flags to
whatever job scheduler is available, or run the underlying Python entry points
directly for a local run. Logs and status files are written under
`.artifacts/logs/`.

### Resume From Interim Data

```bash
scripts/fetch_interim_from_hf.sh
```

This populates `data/interim/ratings_filtered.parquet` and
`data/interim/ratings_clustered.parquet`. The remaining clustering artifacts,
especially the Method-B user assignment, must also exist before starting from
`scoring`.

### Canonical Gemma Validation

The canonical validation is implemented under
`notebooks/llm_validation/` and evaluates the frozen 13,655-note universe with
Gemma 4 31B IT in BF16 on two L40S-class GPUs. Prompts contain only note text:
no tweet retrieval, URL fetching, Gabriel scaffold, or upstream selection
score is supplied to the model.

Install the pinned runtime and model, then submit the 128-note Stage 1 smoke:

```bash
jobs/submit_llm_validation.sh setup
jobs/submit_llm_validation.sh smoke
jobs/submit_llm_validation.sh stage1-array 2-7 3 64
```

See [notebooks/llm_validation/README.md](notebooks/llm_validation/README.md)
for frozen prompts, adaptive batch sizing, parallel Stage 1 shards, checkpoint
behavior, and output schemas.

The separately reported Stage 1.5 sensitivity analysis rechecks only the
1,703 resolved Gemma opinion notes for a substantial sourced factual core. It
keeps canonical Stage 1 immutable and writes to a separate run directory:

```bash
jobs/submit_llm_validation.sh --dry-run stage1-5 1703 64
jobs/submit_llm_validation.sh stage1-5 1703 64
```

Its 280 additional admissions join the 10,096 strict sourced notes in a
10,376-note expanded Stage 2 run. The completed and merged run retains 8,527
strict-route notes and 31 Stage 1.5 recall-route notes at the frozen threshold
of 50. The canonical final rescue set therefore contains **8,558 notes**. The
admission route is audited but never shown to the model. Operational and audit
details are in `notebooks/llm_validation/README.md`.

### Build The Paper

```bash
cd paper
latexmk -pdf main.tex
```

The five figures and the three frozen prompt files the appendices quote are
pulled in from `figures/` and `data/`, so a fresh clone builds without any extra
downloads. See [paper/README.md](paper/README.md).

## Methodology

### 1. Ingestion

`notebooks/00_ingest.ipynb` reads the official Community Notes notes, ratings,
and status-history files.

- FastText retains English notes.
- Tweets must have at least three English notes.
- Ratings are joined to note metadata and status history.
- Output: `data/master_full.parquet` (large, ignored by Git).

### 2. Clustering

`notebooks/01_clustering.ipynb` selects a dense slice with 100,000 notes and
200,000 users. Only ratings cast within 48 hours of note creation are eligible,
and notes require at least three eligible ratings.

The clustering implementation in `src/spectral_fast.py`:

- builds a sparse mean-centered user-note matrix;
- constructs a symmetric 15-nearest-neighbor affinity graph;
- computes spectral embeddings with AMG for production;
- evaluates `k=2..7` using silhouette and repeated stability diagnostics.

Clusters smaller than `max(1% of users, 500 users)` are treated as outliers.
Method A assigns those users by embedding-centroid distance. Method B assigns
them by correlation with the main camps' note-level vote profiles. Method B is
the canonical downstream assignment; the initial spectral label remains
available as `initial_cluster`.

### 3. Scoring And Representative Selection

`notebooks/02_scoring.ipynb` computes global and camp-conditional approval.
Notes need at least three total ratings. A bridge score is computed only when
every camp has at least three ratings for the note:

```text
bridge score = geometric mean of camp-conditional approval rates
```

For each tweet, the Representative strategy selects the note with the highest
bridge score. A non-helpful note counts as rescued when its bridge score is
strictly above `0.5`.

Topic input is restricted to notes whose maximum-minus-minimum camp approval is
at least `0.90`, again requiring at least three ratings from every camp.

### 4. Representative Topics

`notebooks/03_topics.ipynb` runs BERTopic on the diagnostic note subset using
`all-MiniLM-L6-v2`, cosine UMAP, and the repository's fixed text-cleaning
rules.

Three auditable layers:

- fine-grained topics;
- a 30-topic parent layer;
- a paper-facing super-parent layer selected from candidate counts `6, 8, 10, 12`.

HDBSCAN outliers remain visible in the strict parent output. A separate
reassigned table maps them to the nearest parent centroid and records
similarity diagnostics. Process/meta vocabulary is removed from labels without
removing notes from the corpus.

### 5. Gemma Validation And Figures

The canonical Gemma pipeline first classifies all 13,655 Representative rescue
candidates, applies a targeted Stage 1.5 recall check to resolved opinion
notes, and scores the resulting 10,376 sourced candidates for rescue
worthiness. The final rescue definition is
`passes_rescue_threshold == True` in the merged expanded Stage 2 result, which
yields 8,558 notes.

`notebooks/06_plots.ipynb` produces exploratory analysis plots, and
`notebooks/07_paper_visuals.ipynb` is the historical manuscript-figure notebook.

Every figure in the current paper is produced by a standalone script in
`figures/script_figures/`, where the script and its `.pdf` and `.png` outputs
share one basename. Regenerate any of them in place:

```bash
python figures/script_figures/fig1-rater-dominance.py        # Figure 1
python figures/script_figures/fig2-dataset-construction.py   # Figure 2
python figures/script_figures/fig3-rescue-panels.py          # Figure 3
python figures/script_figures/cn-gemma-validation-funnel.py  # Figure 4
python figures/script_figures/cn-topic-signatures.py         # Figure 5
```

All but Figure 2 run on a fresh clone; that one also needs
`data/interim/ratings_clustered.parquet` from Hugging Face. See
[figures/README.md](figures/README.md).

Smoke mode changes scale and output location only. It does not redefine the
production methodology.

## Tests

```bash
python -m pip install -r requirements.txt
python run_tests.py          # all 68 tests
python run_tests.py -v       # per-test names
```

Three suites run: the aggregation rule on synthetic data, the paper's headline
numbers re-derived from the committed parquet files, and the Gemma validation
package with every model call mocked. The tests themselves need only `pandas`,
`numpy`, and `pyarrow` from that requirements file; `pytest` is not a dependency,
and no data has to be downloaded. [tests/RESULTS.md](tests/RESULTS.md) records
the last full run and lists what each suite asserts.

## Licensing

| Content | License |
|---|---|
| Code — `src/`, `notebooks/`, `jobs/`, `scripts/`, `tests/`, figure scripts | MIT, see [LICENSE](LICENSE) |
| Data, figures, manuscript, presentations | CC BY 4.0, see [LICENSE-DATA](LICENSE-DATA) |

The underlying Community Notes data remains subject to X's own terms; no raw
snapshot files are redistributed here. To cite this work, see
[CITATION.cff](CITATION.cff).

## Acknowledgments

The authors acknowledge support by the local computing resources through the
core facility [SCCKN](https://scc.uni-konstanz.de).

## References

- Paper: [paper/README.md](paper/README.md)
- Reproduction map: [REPRODUCING.md](REPRODUCING.md)
- Data catalogue: [data/README.md](data/README.md)
- Figures: [figures/README.md](figures/README.md)
- Presentations: [docs/README.md](docs/README.md)
