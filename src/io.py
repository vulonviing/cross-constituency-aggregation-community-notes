from __future__ import annotations

from collections import Counter
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq

from .config import ProjectPaths

CLUSTERING_RATING_COLUMNS = [
    "noteId",
    "raterParticipantId",
    "helpfulnessLevel",
    "createdAtMillis",
    "noteCreatedAtMillis",
]

NOTE_METADATA_COLUMNS = [
    "noteId",
    "tweetId",
    "summary",
    "classification",
    "currentStatus",
    "firstNonNMRMillis",
]


def _normalize_fasttext_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return " ".join(text.replace("\n", " ").replace("\r", " ").split())


def _strip_fasttext_label(label: object) -> str:
    return str(label).replace("__label__", "")


def _predict_fasttext_with_python(
    model_path: Path,
    texts: list[str],
    batch_size: int,
) -> tuple[list[str], list[float]]:
    import fasttext

    model = fasttext.load_model(str(model_path))
    detected_labels = [""] * len(texts)
    detected_scores = [0.0] * len(texts)

    for start in range(0, len(texts), batch_size):
        indexed_batch = [
            (idx, text)
            for idx, text in enumerate(texts[start : start + batch_size], start=start)
            if text
        ]
        if not indexed_batch:
            continue

        batch_texts = [text for _, text in indexed_batch]
        labels, scores = model.predict(batch_texts, k=1)
        for (idx, _), label_item, score_item in zip(indexed_batch, labels, scores):
            label = label_item[0] if isinstance(label_item, (list, tuple)) else label_item
            score = score_item[0] if isinstance(score_item, (list, tuple)) else score_item
            detected_labels[idx] = _strip_fasttext_label(label)
            detected_scores[idx] = float(score)

    return detected_labels, detected_scores


def _resolve_fasttext_binary(fasttext_binary: str | Path | None) -> str | None:
    candidates: list[str] = []
    if fasttext_binary:
        candidates.append(str(fasttext_binary))
    candidates.append("fasttext")

    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path)
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _predict_fasttext_with_cli(
    model_path: Path,
    texts: list[str],
    batch_size: int,
    fasttext_binary: str | Path | None = None,
) -> tuple[list[str], list[float]]:
    binary = _resolve_fasttext_binary(fasttext_binary)
    if binary is None:
        raise FileNotFoundError(
            "No FastText CLI binary found. Set FASTTEXT_BINARY=raw/fasttext "
            "or put a `fasttext` executable on PATH."
        )

    detected_labels = [""] * len(texts)
    detected_scores = [0.0] * len(texts)

    for start in range(0, len(texts), batch_size):
        indexed_batch = [
            (idx, text)
            for idx, text in enumerate(texts[start : start + batch_size], start=start)
            if text
        ]
        if not indexed_batch:
            continue

        batch_texts = [text for _, text in indexed_batch]
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".txt",
            delete=True,
        ) as batch_file:
            batch_file.write("\n".join(batch_texts) + "\n")
            batch_file.flush()
            completed = subprocess.run(
                [binary, "predict-prob", str(model_path), batch_file.name, "1"],
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                signal_name = ""
                if completed.returncode < 0:
                    try:
                        signal_name = f" ({signal.Signals(-completed.returncode).name})"
                    except ValueError:
                        signal_name = ""
                raise RuntimeError(
                    "FastText CLI language prediction failed "
                    f"(returncode={completed.returncode}{signal_name}, binary={binary}, "
                    f"model={model_path}, batch_file={batch_file.name}):\n"
                    f"stderr={completed.stderr.strip()}\n"
                    f"stdout={completed.stdout.strip()}"
                )

        output_lines = completed.stdout.splitlines()
        if len(output_lines) != len(indexed_batch):
            raise RuntimeError(
                "FastText CLI returned an unexpected number of predictions: "
                f"expected {len(indexed_batch)}, got {len(output_lines)}"
            )

        for (idx, _), line in zip(indexed_batch, output_lines):
            parts = line.strip().split()
            if len(parts) >= 2:
                detected_labels[idx] = _strip_fasttext_label(parts[0])
                detected_scores[idx] = float(parts[1])

    return detected_labels, detected_scores


def filter_notes_by_fasttext_language(
    notes: pd.DataFrame,
    model_path: str | Path,
    language: str = "en",
    min_confidence: float = 0.5,
    text_column: str = "summary",
    batch_size: int = 10_000,
    fasttext_binary: str | Path | None = None,
) -> pd.DataFrame:
    """Keep only notes whose FastText language prediction matches `language`.

    The FastText language-id model returns labels such as `__label__en`.
    We store the stripped label and confidence on the returned dataframe so
    downstream notebooks can audit the language filter if needed. The Python
    fasttext binding is used when available; otherwise the standalone FastText
    CLI binary is used via `FASTTEXT_BINARY`.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"FastText language model not found: {model_path}. "
            "Download lid.176.ftz or lid.176.bin and point FASTTEXT_LID_MODEL to it."
        )

    texts = notes[text_column].map(_normalize_fasttext_text).tolist()

    try:
        detected_labels, detected_scores = _predict_fasttext_with_python(
            model_path=model_path,
            texts=texts,
            batch_size=batch_size,
        )
    except ImportError:
        detected_labels, detected_scores = _predict_fasttext_with_cli(
            model_path=model_path,
            texts=texts,
            batch_size=batch_size,
            fasttext_binary=fasttext_binary,
        )

    filtered = notes.copy()
    filtered["noteLanguage"] = detected_labels
    filtered["noteLanguageScore"] = detected_scores
    mask = filtered["noteLanguage"].eq(language) & filtered["noteLanguageScore"].ge(min_confidence)
    return filtered[mask].copy()


def ensure_project_dirs(paths: ProjectPaths) -> None:
    for directory in (paths.data_dir, paths.interim_dir, paths.processed_dir, paths.notebook_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)


def load_master_sample(master_csv: str | Path) -> pd.DataFrame:
    df = pd.read_csv(master_csv, low_memory=False)
    df = df[df["helpfulnessLevel"].isin(["HELPFUL", "NOT_HELPFUL"])].copy()
    df["vote"] = df["helpfulnessLevel"].map({"HELPFUL": 1, "NOT_HELPFUL": 0})
    return df


def load_master_table(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Like load_master_sample but dispatches on file suffix.

    Accepts either the legacy `master_sample.csv` or the cluster
    `master_full.parquet`. Output schema is identical.
    """
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path, columns=columns)
    else:
        df = pd.read_csv(path, usecols=columns, low_memory=False)

    if "helpfulnessLevel" in df.columns:
        df = df[df["helpfulnessLevel"].isin(["HELPFUL", "NOT_HELPFUL"])].copy()
        df["vote"] = df["helpfulnessLevel"].map({"HELPFUL": 1, "NOT_HELPFUL": 0}).astype("int8")
    elif "vote" not in df.columns:
        raise KeyError("Expected either helpfulnessLevel or vote in master table")
    return df


def load_clustering_ratings(path: str | Path) -> pd.DataFrame:
    """Load only the columns needed to select and cluster rating behavior.

    The full master parquet duplicates note text/status metadata on every
    rating row. Reading those text columns for full data is memory-heavy, so
    clustering loads a narrow ratings table first and merges note metadata only
    after the dense note/user slice has been selected.
    """
    df = load_master_table(path, columns=CLUSTERING_RATING_COLUMNS)
    return df.drop(columns=["helpfulnessLevel"], errors="ignore")


def _iter_filtered_rating_batches(
    path: str | Path,
    hours_window: int,
    batch_size: int,
    note_ids: Iterable | None = None,
    user_ids: Iterable | None = None,
):
    """Yield memory-bounded rating batches from master_full.parquet."""
    path = Path(path)
    note_ids = set(note_ids) if note_ids is not None else None
    user_ids = set(user_ids) if user_ids is not None else None
    if path.suffix != ".parquet":
        df = load_clustering_ratings(path)
        df = apply_timeliness_filter(df, hours_window=hours_window)
        if note_ids is not None:
            df = df[df["noteId"].isin(note_ids)]
        if user_ids is not None:
            df = df[df["raterParticipantId"].isin(user_ids)]
        yield df.loc[:, ["noteId", "raterParticipantId", "vote"]].copy()
        return

    parquet = pq.ParquetFile(path)
    millis_window = hours_window * 3600 * 1000

    for batch in parquet.iter_batches(batch_size=batch_size, columns=CLUSTERING_RATING_COLUMNS):
        df = batch.to_pandas()

        mask = df["helpfulnessLevel"].isin(["HELPFUL", "NOT_HELPFUL"])
        if "createdAtMillis" in df.columns and "noteCreatedAtMillis" in df.columns:
            diff_millis = df["createdAtMillis"] - df["noteCreatedAtMillis"]
            mask &= diff_millis.ge(0) & diff_millis.le(millis_window)
        if note_ids is not None:
            mask &= df["noteId"].isin(note_ids)
        if user_ids is not None:
            mask &= df["raterParticipantId"].isin(user_ids)

        if not mask.any():
            continue

        filtered = df.loc[mask, ["noteId", "raterParticipantId", "helpfulnessLevel"]].copy()
        filtered["vote"] = filtered["helpfulnessLevel"].map({"HELPFUL": 1, "NOT_HELPFUL": 0}).astype("int8")
        yield filtered.drop(columns=["helpfulnessLevel"])


def _add_value_counts(counter: Counter, values: pd.Series) -> None:
    counts = values.value_counts(dropna=True)
    counter.update(counts.to_dict())


def load_clustering_slice(
    path: str | Path,
    target_note_count: int,
    target_user_count: int,
    hours_window: int,
    min_note_ratings: int = 3,
    batch_size: int = 250_000,
    progress_every: int = 25,
) -> pd.DataFrame:
    """Build the dense note/user clustering slice without loading full master.

    Full `master_full.parquet` can contain more than 100M rating rows. Even a
    narrow column read can exceed a small SGE memory request if pandas copies the
    whole table. This function streams the parquet in bounded batches:

    1. count top notes after helpfulness + 48h timeliness filters
    2. count top users inside those notes
    3. materialize only the final top-note/top-user rating slice
    """
    note_counts: Counter = Counter()
    print(
        "[clustering-slice] pass 1/3: counting top notes "
        f"(batch_size={batch_size:,}, hours_window={hours_window}, "
        f"min_note_ratings={min_note_ratings})",
        flush=True,
    )
    for batch_idx, batch_df in enumerate(
        _iter_filtered_rating_batches(path, hours_window=hours_window, batch_size=batch_size),
        start=1,
    ):
        _add_value_counts(note_counts, batch_df["noteId"])
        if progress_every and batch_idx % progress_every == 0:
            print(
                f"[clustering-slice] pass 1 batches={batch_idx:,} "
                f"unique_notes={len(note_counts):,}",
                flush=True,
            )

    eligible_notes = [
        (note_id, count)
        for note_id, count in note_counts.most_common()
        if count >= min_note_ratings
    ]
    top_notes = {note_id for note_id, _ in eligible_notes[:target_note_count]}
    print(
        f"[clustering-slice] eligible_notes_min_{min_note_ratings}_ratings={len(eligible_notes):,}",
        flush=True,
    )
    print(f"[clustering-slice] selected top_notes={len(top_notes):,}", flush=True)
    if not top_notes:
        return pd.DataFrame(columns=["noteId", "raterParticipantId", "vote"])

    user_counts: Counter = Counter()
    print("[clustering-slice] pass 2/3: counting top users inside selected notes", flush=True)
    for batch_idx, batch_df in enumerate(
        _iter_filtered_rating_batches(
            path,
            hours_window=hours_window,
            batch_size=batch_size,
            note_ids=top_notes,
        ),
        start=1,
    ):
        _add_value_counts(user_counts, batch_df["raterParticipantId"])
        if progress_every and batch_idx % progress_every == 0:
            print(
                f"[clustering-slice] pass 2 batches={batch_idx:,} "
                f"unique_users={len(user_counts):,}",
                flush=True,
            )

    top_users = {user_id for user_id, _ in user_counts.most_common(target_user_count)}
    print(f"[clustering-slice] selected top_users={len(top_users):,}", flush=True)
    if not top_users:
        return pd.DataFrame(columns=["noteId", "raterParticipantId", "vote"])

    frames: list[pd.DataFrame] = []
    total_rows = 0
    print("[clustering-slice] pass 3/3: materializing selected note/user slice", flush=True)
    for batch_idx, batch_df in enumerate(
        _iter_filtered_rating_batches(
            path,
            hours_window=hours_window,
            batch_size=batch_size,
            note_ids=top_notes,
            user_ids=top_users,
        ),
        start=1,
    ):
        frames.append(batch_df)
        total_rows += len(batch_df)
        if progress_every and batch_idx % progress_every == 0:
            print(
                f"[clustering-slice] pass 3 batches={batch_idx:,} rows={total_rows:,}",
                flush=True,
            )

    if not frames:
        return pd.DataFrame(columns=["noteId", "raterParticipantId", "vote"])

    result = pd.concat(frames, ignore_index=True)
    print(f"[clustering-slice] final slice rows={len(result):,}", flush=True)
    return result


def load_note_metadata(raw_dir: str | Path, note_ids) -> pd.DataFrame:
    """Load note metadata for a selected note set from the raw TSV files."""
    raw_dir = Path(raw_dir)
    note_id_index = pd.Index(note_ids).dropna().unique()
    if len(note_id_index) == 0:
        return pd.DataFrame(columns=NOTE_METADATA_COLUMNS)

    note_frames: list[pd.DataFrame] = []
    for path in sorted(raw_dir.glob("notes-*.tsv")):
        chunk = pd.read_csv(
            path,
            sep="\t",
            usecols=["noteId", "tweetId", "summary", "classification"],
            low_memory=False,
        )
        chunk = chunk[chunk["noteId"].isin(note_id_index)]
        if not chunk.empty:
            note_frames.append(chunk)

    if note_frames:
        notes = pd.concat(note_frames, ignore_index=True).drop_duplicates(subset=["noteId"])
    else:
        notes = pd.DataFrame(columns=["noteId", "tweetId", "summary", "classification"])

    status_path = raw_dir / "noteStatusHistory-00000.tsv"
    if status_path.exists():
        status = pd.read_csv(
            status_path,
            sep="\t",
            usecols=["noteId", "currentStatus", "timestampMillisOfFirstNonNMRStatus"],
            low_memory=False,
        )
        status = status[status["noteId"].isin(note_id_index)].rename(
            columns={"timestampMillisOfFirstNonNMRStatus": "firstNonNMRMillis"}
        )
        status = status.drop_duplicates(subset=["noteId"])
    else:
        status = pd.DataFrame(columns=["noteId", "currentStatus", "firstNonNMRMillis"])

    metadata = notes.merge(status, on="noteId", how="left")
    for column in NOTE_METADATA_COLUMNS:
        if column not in metadata.columns:
            metadata[column] = pd.NA
    return metadata.loc[:, NOTE_METADATA_COLUMNS]


def attach_note_metadata(df: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Attach note-level text/status metadata without creating duplicate columns."""
    metadata_cols = [column for column in metadata.columns if column != "noteId"]
    cleaned = df.drop(columns=[column for column in metadata_cols if column in df.columns], errors="ignore")
    return cleaned.merge(metadata, on="noteId", how="left")


def apply_timeliness_filter(df: pd.DataFrame, hours_window: int) -> pd.DataFrame:
    if "noteCreatedAtMillis" not in df.columns or "createdAtMillis" not in df.columns:
        return df.copy()

    filtered = df.copy()
    filtered["time_diff_hours"] = (
        filtered["createdAtMillis"] - filtered["noteCreatedAtMillis"]
    ) / (1000 * 3600)
    return filtered[
        filtered["time_diff_hours"].between(0, hours_window, inclusive="both")
    ].copy()


def save_table(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
        return
    df.to_csv(path, index=False)


def load_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def get_test_mode() -> int:
    """Read TEST_MODE from config.txt at the project root.

    Returns 1 for smoke-test mode, 0 for full data run.
    Defaults to 0 if config.txt is missing or unreadable.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        cfg = parent / "config.txt"
        if not cfg.exists():
            continue
        for raw_line in cfg.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TEST_MODE="):
                value = line.split("=", 1)[1].strip()
                try:
                    return int(value)
                except ValueError:
                    return 0
        return 0
    return 0


def read_pipeline_config() -> dict[str, str]:
    """Read KEY=VALUE entries from the nearest config.txt."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        cfg = parent / "config.txt"
        if not cfg.exists():
            continue
        values: dict[str, str] = {}
        for raw_line in cfg.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values
    return {}


def get_config_value(key: str, default: str) -> str:
    return read_pipeline_config().get(key, default)


def get_config_int(key: str, default: int) -> int:
    raw_value = get_config_value(key, str(default))
    try:
        return int(raw_value)
    except ValueError:
        return default


def get_config_float(key: str, default: float) -> float:
    raw_value = get_config_value(key, str(default))
    try:
        return float(raw_value)
    except ValueError:
        return default


def get_project_root() -> Path:
    """Return the repository root, identified by config.txt."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config.txt").exists():
            return parent
    raise FileNotFoundError("config.txt not found; cannot locate project root")


def get_run_root() -> Path:
    """Return the output root for the current run.

    Production writes to the repository root. Smoke tests are isolated under
    `.artifacts/smoke/` so they cannot overwrite canonical data or figures.
    """
    root = get_project_root()
    return root / ".artifacts" / "smoke" if get_test_mode() == 1 else root


def get_data_root() -> Path:
    return get_run_root() / "data"


def get_interim_dir() -> Path:
    return get_data_root() / "interim"


def get_processed_dir() -> Path:
    return get_data_root() / "processed"


def get_topic_dir() -> Path:
    return get_processed_dir() / "topics"


def get_gabriel_dir() -> Path:
    """Return the historical Gabriel artifact directory."""
    return get_data_root() / "gabriel"


def get_llm_validation_run_dir(run_id: str) -> Path:
    """Return one canonical Gemma validation run directory."""
    return get_data_root() / "llm_validation" / "runs" / run_id


def get_stage1_validation_dir() -> Path:
    return get_llm_validation_run_dir("gemma-4-31b-it-scckn-v1")


def get_stage15_validation_dir() -> Path:
    return get_llm_validation_run_dir("gemma-4-31b-it-scckn-stage1-5-opinion-v1")


def get_expanded_stage2_validation_dir() -> Path:
    return get_llm_validation_run_dir("gemma-4-31b-it-scckn-stage2-expanded-v1")


def get_figure_dir() -> Path:
    return get_run_root() / "figures" / "notebook_figures"


def load_ratings_with_final_cluster() -> pd.DataFrame:
    """Load ratings with the canonical Method-B reassigned camp labels.

    The spectral label is retained as `initial_cluster`; `cluster` is the final
    two-camp assignment used by scoring and all downstream stages.
    """
    interim = get_interim_dir()
    ratings = pd.read_parquet(interim / "ratings_clustered.parquet")
    method_b = pd.read_parquet(
        interim / "user_clusters_method_b_voteprofile.parquet"
    )
    ratings = ratings.rename(columns={"cluster": "initial_cluster"})
    ratings = ratings.merge(
        method_b[["raterParticipantId", "cluster"]],
        on="raterParticipantId",
        how="left",
        validate="many_to_one",
    )
    if ratings["cluster"].isna().any():
        missing = int(ratings["cluster"].isna().sum())
        raise ValueError(f"Method-B cluster assignment missing for {missing:,} ratings")
    return ratings
