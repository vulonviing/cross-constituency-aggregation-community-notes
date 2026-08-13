# data/

Every file here is derived from X's public Community Notes snapshot, retrieved
on **2026-05-08**. No raw snapshot file is redistributed. Row counts are the
canonical production values; a `TEST_MODE=1` smoke run writes its own copies
under `.artifacts/smoke/` and never touches these.

To find which file backs a specific claim in the paper, use
[REPRODUCING.md](../REPRODUCING.md).

## Not stored in Git

Three files exceed GitHub's limits and live on the
`vulonviing/community-notes-rescue-interim` Hugging Face dataset. Fetch them
with `scripts/fetch_interim_from_hf.sh`.

| File | Size | Produced by | Needed for |
|---|---|---|---|
| `master_full.parquet` | ~6.6 GB | `00_ingest` | re-running the pipeline from ingestion |
| `interim/ratings_filtered.parquet` | ~3 GB | `00_ingest` | re-running `01_clustering` |
| `interim/ratings_clustered.parquet` | ~3 GB | `01_clustering` | re-running `02_scoring`, `03_topics` |

In this checkout the two `interim/ratings_*.parquet` entries are symlinks to the
working repository's copies, so both checkouts share one physical file on disk.

The same dataset also carries `scale-ladder/`, the mirror of the scale-selection
study described under [`scale-ladder/`](scale-ladder/) below. Its small
diagnostics are committed here; its per-rater assignments are only on Hugging
Face. See [The Scale Ladder Mirror](../README.md#the-scale-ladder-mirror) for
what was kept, what was dropped, and why.

## interim/ — clustering stage (`notebooks/01_clustering.ipynb`)

| File | Rows | What it holds |
|---|---|---|
| `user_clusters_method_b_voteprofile.parquet` | 200,000 | **The canonical partition.** Every downstream stage reads this one. Outlier raters are placed by correlating their note-level voting against each camp's aggregate profile. |
| `user_clusters_method_a_embedding.parquet` | 200,000 | The alternative reassignment, by embedding-centroid distance. Kept for the robustness check; it disagrees with Method B about 29 raters. |
| `user_clusters.parquet` | 200,000 | The raw spectral labels before reassignment, with the third hyperactive cluster still separate. |
| `cluster_summary.parquet` | 3 | Per-cluster size, vote counts, and approval rates for the initial `k=3` partition. Source of the 107,680 / 92,256 / 64 split. |
| `stability_over_k.parquet` | 6 | Mean bootstrap ARI for `k=2..7`. This is what selects `k=3`. |
| `silhouette_over_k.parquet` | 6 | Silhouette score for `k=2..7`; reported alongside stability because the two criteria disagree. |
| `user_stats.parquet` | 200,000 | Per-rater totals: votes cast, positive/negative split, distinct notes. |
| `embedding.parquet` | 200,000 | The spectral embedding coordinates the clustering ran on. |
| `graph_diagnostics.parquet` | 1 | k-NN affinity graph shape: backend, neighbor count, edge counts. |
| `runtime_diagnostics.parquet` | 7 | Wall-clock seconds per clustering stage. |

## scale-ladder/ — the scale-selection study

Forty-two clustering runs at scales from 50k to 250k across three eigensolvers,
one directory each, holding only the five small diagnostic tables. This is the
evidence behind Table 1 of the paper and behind its footnote on what bootstrap
stability fails to certify. See [`scale-ladder/README.md`](scale-ladder/README.md).

## processed/ — scoring and selection (`notebooks/02_scoring.ipynb`)

| File | Rows | What it holds |
|---|---|---|
| `scores.parquet` | 100,000 | **The central results table.** One row per note in the dense slice: global approval, per-camp approval and rater counts, and the bridge score. Backs the −0.620 correlation and the 81.4% discriminating share. |
| `selection_log.parquet` | 268,332 | One row per (tweet, strategy) pick across all five strategies and three scopes. Backs every row of Table 4. |
| `rescue_summary.parquet` | 44,722 | Per-tweet outcome under each rule: what the majoritarian rule published, what the pluralistic and representative rules rescued. |
| `selection_status_summary.parquet` | 15 | Aggregate counts per strategy and status group. |
| `final_table.parquet` | 100,000 | Human-readable version of `scores.parquet` with note text and X's own label, for manual inspection. |
| `diagnostic_notes.parquet` | 11,226 | Notes whose between-camp approval gap is at least 0.90 with ≥3 raters per camp; the input to topic modeling. |
| `pluralistic_breakdown.parquet` | 2 | Tweets rescued by each camp's own top pick. |

## processed/topics/ — topic modeling (`notebooks/03_topics.ipynb`)

BERTopic output at three auditable layers. Fine-grained topics come first, a
30-topic parent layer groups them, and a super-parent layer produces the 13
subject areas Figure 5 plots.

| Group | Files | What it holds |
|---|---|---|
| Fine layer | `topic_notes`, `topic_cluster_stats`, `topic_exemplars`, `topic_salience`, `topic_salience_pivot`, `topic_rescue_stats` | Per-note topic assignment (44,722 notes, 589 topics), per-topic camp approval, representative notes, and rescue rates. |
| Parent layer | `topic_parent_notes`, `topic_parent_notes_reassigned`, `topic_parent_cluster_stats`, `topic_parent_crosswalk`, `topic_parent_exemplars`, `topic_parent_initial_topics`, `topic_parent_initial_topic_terms` | The 30-topic grouping. The `_reassigned` variant maps HDBSCAN outliers to their nearest parent centroid; the strict variant leaves them visible. |
| Super-parent layer | `topic_super_parent_notes`, `topic_super_parent_cluster_stats`, `topic_super_parent_crosswalk`, `topic_super_parent_candidate_crosswalk`, `topic_super_parent_candidate_quality`, `topic_super_parent_diagnostics` | The paper-facing layer, selected from candidate counts 6, 8, 10, and 12. |
| Audit trail | `topic_parent_diagnostics`, `topic_parent_meta_terms`, `topic_parent_meta_topic_diagnostics`, `topic_parent_reassignment_sensitivity`, `topic_strategy_summary`, `topic_strategy_pivot`, `topic_selection_overlap` | Which process/meta vocabulary was stripped from labels, how sensitive the outlier reassignment is, and how topics distribute across selection strategies. |

Labels are cleaned of process and meta vocabulary, but no note is ever removed
from the corpus on that basis.

## llm_validation/ — Gemma validation (`notebooks/llm_validation/`)

Three run directories under `runs/`, each self-contained and auditable:

| Run | What it did |
|---|---|
| `gemma-4-31b-it-scckn-v1` | **Stage 1** content screen over all 13,655 rescue-pool notes, plus the original strict Stage 2. |
| `gemma-4-31b-it-scckn-stage1-5-opinion-v1` | **Stage 1.5** recall check over the 1,703 opinion-labeled notes; recovers 280 with a sourced factual core. |
| `gemma-4-31b-it-scckn-stage2-expanded-v1` | **Stage 2 (expanded)** rescue-worthiness scoring of the merged 10,376-note population. `stage2_results.parquet` is where the final **8,558** comes from. |

Each directory carries the same audit set:

| File | What it is |
|---|---|
| `run_manifest.json` | Model identity, decoding settings, seeds, prompt hash, input manifest hash. |
| `*_prompt.txt` | The frozen prompt text, byte for byte as sent. |
| `input_manifest.{parquet,csv}` | Exactly which notes entered the run, in order. |
| `*_results.parquet` | The parsed per-note judgment. |
| `*_unresolved.parquet` | Notes that failed to produce a schema-valid response within three attempts. |
| `raw_calls.jsonl.gz` | Every raw model response, unparsed. |
| `calls.{sqlite3,parquet}` | Per-attempt call store: prompt, response, seed, attempt index, timing. |
| `checksums.sha256` | Integrity hashes for every file in the run directory. |
| `summary.json` | Aggregate counts for the run. |
| `shards/` | The per-batch checkpoints the run was assembled from, retained so the merge can be re-checked against its parts. |

Verify all three manifests at once:

```bash
bash scripts/verify_llm_checksums.sh
```

Two details about those hashes are worth stating plainly. The Stage 1 and Stage
1.5 manifests were written on the cluster when the runs finished, so their
hashes attest that nothing has changed since; the expanded Stage 2 manifest was
computed later, when this repository was packaged, and therefore only attests to
the state at packaging time. And each run also produced a `calls.backup.sqlite3`
checkpoint, roughly 96 MB across the three runs, which is an intermediate copy of
the call store rather than a result. Those files are kept locally and left out of
this checkout, and their entries were removed from the manifests so the
verification runs clean.

Generation is not schema-constrained; responses are parsed and validated against
a strict contract afterward, with at most three attempts before a judgment is
recorded as unresolved. Both production runs finished with zero schema errors.
