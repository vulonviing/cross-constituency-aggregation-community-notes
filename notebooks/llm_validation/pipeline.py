from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable

import pandas as pd
from openai import APIConnectionError, APIStatusError, APITimeoutError

from client import (
    EmptyContentError,
    LocalVLLMClient,
    TruncatedResponseError,
)
from config import (
    BASE_URL,
    DEFAULT_CONCURRENCY,
    EXPORT_EVERY,
    MAX_ATTEMPTS,
    MAX_COMPLETION_TOKENS,
    MODEL,
    MODEL_REVISION,
    MODEL_VARIANT,
    PROJECT_ROOT,
    RANDOM_SEED,
    RUN_ID,
    SMOKE_NOTES,
    STAGE15_CONCURRENCY,
    STAGE15_RUN_ID,
    STAGE1_SHARD_SIZE,
    STAGE1_RUNS,
    STAGE2_EXPANDED_CONCURRENCY,
    STAGE2_EXPANDED_RUN_ID,
    STAGE2_EXPANDED_SHARD_SIZE,
    STAGE2_RESCUE_THRESHOLD,
    STAGE2_RUNS,
    TEMPERATURE,
    RunPaths,
    get_run_paths,
    get_stage15_paths,
    get_stage1_shard_paths,
    get_stage2_expanded_paths,
    get_stage2_expanded_shard_paths,
)
from prompts import (
    STAGE1_TEMPLATE,
    STAGE15_TEMPLATE,
    STAGE2_TEMPLATE,
    prompt_hash,
    render_stage1,
    render_stage15,
    render_stage2,
)
from schemas import (
    SchemaError,
    Stage1Response,
    Stage2Response,
    parse_stage1,
    parse_stage15,
    parse_stage2,
)
from storage import CallStore


_ATTEMPT_COLUMNS = (
    "logical_key",
    "stage",
    "note_id",
    "round_no",
    "run_no",
    "attempt_no",
    "seed",
    "status",
    "error_type",
    "error_message",
    "http_status",
    "returned_model",
    "finish_reason",
    "label",
    "score",
    "reason",
    "raw_response_gzip",
    "reasoning_gzip",
    "prompt_tokens",
    "cached_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "latency_ms",
    "created_at",
)

_SHARD_METADATA_KEYS = (
    "run_id",
    "source_universe_rows",
    "source_universe_sha256",
    "model",
    "model_revision",
    "model_variant",
    "thinking",
    "temperature",
    "max_completion_tokens",
    "max_attempts_total",
    "stage1_runs",
    "stage2_runs",
    "random_seed",
    "retrieval",
    "system_prompt",
    "structured_output_constraint",
    "stage1_prompt_sha256",
    "stage2_prompt_sha256",
    "vllm_version",
)


def _stable_manifest_hash(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    for row in frame.sort_values("noteId")[["noteId", "note_text"]].itertuples(index=False):
        for value in (str(row.noteId), str(row.note_text)):
            encoded = value.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
    return digest.hexdigest()


def _stable_expanded_manifest_hash(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    columns = ["noteId", "note_text", "admission_route"]
    for row in frame.sort_values("noteId")[columns].itertuples(index=False):
        for value in row:
            encoded = str(value).encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_manifest() -> pd.DataFrame:
    source_path = (
        PROJECT_ROOT
        / "data"
        / "llm_validation"
        / "runs"
        / "gemma-4-31b-it-scckn-v1"
        / "input_manifest.parquet"
    )
    if not source_path.exists():
        raise FileNotFoundError(f"Frozen Gemma input manifest not found: {source_path}")

    manifest = pd.read_parquet(source_path)
    required = ["noteId", "note_text", "old_gabriel_label", "note_sha256"]
    if not set(required).issubset(manifest.columns):
        raise ValueError(
            f"Frozen Gemma input manifest lacks columns: "
            f"{sorted(set(required) - set(manifest.columns))}"
        )
    manifest = manifest[list(required)].copy()
    manifest["noteId"] = manifest["noteId"].astype(str)
    if len(manifest) != 13_655 or manifest["noteId"].nunique() != 13_655:
        raise ValueError("Expected exactly 13,655 unique frozen Gemma noteIds")
    if manifest["note_text"].isna().any():
        raise ValueError(
            f"{int(manifest['note_text'].isna().sum())} frozen noteIds have no raw text"
        )
    manifest["note_text"] = manifest["note_text"].astype(str)
    actual_hashes = manifest["note_text"].map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )
    if not actual_hashes.equals(manifest["note_sha256"]):
        raise ValueError("Frozen Gemma input manifest contains invalid note text hashes")
    return manifest.sort_values("noteId").reset_index(drop=True)


def _atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.stem + ".tmp.parquet")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def prepare_run(*, smoke: bool) -> tuple[pd.DataFrame, RunPaths]:
    paths = get_run_paths(smoke=smoke)
    paths.root.mkdir(parents=True, exist_ok=True)
    full = _source_manifest()
    full_hash = _stable_manifest_hash(full)
    if smoke:
        manifest = full.sample(n=SMOKE_NOTES, random_state=RANDOM_SEED).reset_index(drop=True)
    else:
        manifest = full
    selected_hash = _stable_manifest_hash(manifest)
    run_manifest = {
        "run_id": RUN_ID,
        "mode": "smoke" if smoke else "production",
        "source_universe_rows": len(full),
        "selected_rows": len(manifest),
        "source_universe_sha256": full_hash,
        "selected_manifest_sha256": selected_hash,
        "source_note_ids": "data/llm_validation/runs/gemma-4-31b-it-scckn-v1/input_manifest.parquet",
        "source_note_text": "frozen input_manifest.parquet:note_text",
        "model": MODEL,
        "model_revision": MODEL_REVISION,
        "model_variant": MODEL_VARIANT,
        "base_url": BASE_URL,
        "thinking": True,
        "temperature": TEMPERATURE,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "default_concurrency": DEFAULT_CONCURRENCY,
        "max_attempts_total": MAX_ATTEMPTS,
        "stage1_runs": STAGE1_RUNS,
        "stage2_runs": STAGE2_RUNS,
        "rescue_threshold": None,
        "random_seed": RANDOM_SEED,
        "retrieval": False,
        "system_prompt": None,
        "structured_output_constraint": False,
        "stage1_prompt_sha256": prompt_hash(STAGE1_TEMPLATE),
        "stage2_prompt_sha256": prompt_hash(STAGE2_TEMPLATE),
        "vllm_version": os.environ.get("VLLM_VERSION"),
    }
    if paths.run_manifest.exists():
        existing = json.loads(paths.run_manifest.read_text(encoding="utf-8"))
        immutable = (
            "run_id", "mode", "selected_manifest_sha256", "model", "model_revision",
            "thinking", "temperature", "stage1_prompt_sha256", "stage2_prompt_sha256",
        )
        mismatches = [key for key in immutable if existing.get(key) != run_manifest.get(key)]
        if mismatches:
            raise RuntimeError(f"Existing run manifest conflicts on: {', '.join(mismatches)}")
    else:
        manifest.to_parquet(paths.input_manifest, index=False)
        manifest.to_csv(paths.input_csv, index=False)
        (paths.root / "stage1_prompt.txt").write_text(STAGE1_TEMPLATE + "\n", encoding="utf-8")
        (paths.root / "stage2_prompt.txt").write_text(STAGE2_TEMPLATE + "\n", encoding="utf-8")
        _atomic_json(paths.run_manifest, run_manifest)
    return load_manifest(paths), paths


def prepare_stage15_run() -> tuple[pd.DataFrame, RunPaths]:
    parent_paths = get_run_paths(smoke=False)
    parent_manifest = load_manifest(parent_paths)
    if not parent_paths.run_manifest.exists() or not parent_paths.stage1_results.exists():
        raise FileNotFoundError("Canonical Stage 1 manifest and results are required")

    parent_metadata = _read_json(parent_paths.run_manifest)
    parent_hash = _stable_manifest_hash(parent_manifest)
    if parent_metadata.get("selected_manifest_sha256") != parent_hash:
        raise RuntimeError("Canonical input manifest hash does not match its run manifest")

    parent_results = pd.read_parquet(parent_paths.stage1_results)
    required = {"noteId", "status", "final_label"}
    if not required.issubset(parent_results.columns):
        raise ValueError(
            f"Canonical Stage 1 results lack columns: {sorted(required - set(parent_results.columns))}"
        )
    parent_results = parent_results.copy()
    parent_results["noteId"] = parent_results["noteId"].astype(str)
    if parent_results["noteId"].duplicated().any():
        raise ValueError("Canonical Stage 1 results contain duplicate noteIds")
    if set(parent_results["noteId"]) != set(parent_manifest["noteId"]):
        raise ValueError("Canonical Stage 1 results do not exactly cover the input manifest")

    opinion = parent_results[
        parent_results["status"].eq("resolved")
        & parent_results["final_label"].eq("opinion_or_speculation")
    ]
    if len(opinion) != 1_703:
        raise ValueError(f"Expected exactly 1,703 resolved opinion notes; found {len(opinion)}")

    selected_ids = set(opinion["noteId"])
    manifest = parent_manifest[parent_manifest["noteId"].isin(selected_ids)].copy()
    manifest["parent_stage1_status"] = "resolved"
    manifest["parent_stage1_label"] = "opinion_or_speculation"
    manifest = manifest.sort_values("noteId").reset_index(drop=True)
    selected_hash = _stable_manifest_hash(manifest)
    strict_sourced_rows = int(
        parent_results["final_label"].eq("sourced_factual_information").sum()
    )

    paths = get_stage15_paths()
    paths.root.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "run_id": STAGE15_RUN_ID,
        "mode": "production-stage1-5-opinion-recall",
        "parent_run_id": parent_metadata.get("run_id"),
        "parent_manifest_sha256": parent_hash,
        "parent_stage1_results_sha256": _file_sha256(parent_paths.stage1_results),
        "parent_stage1_prompt_sha256": parent_metadata.get("stage1_prompt_sha256"),
        "parent_rows": len(parent_manifest),
        "strict_sourced_rows": strict_sourced_rows,
        "selection": "status=resolved AND final_label=opinion_or_speculation",
        "selected_rows": len(manifest),
        "selected_manifest_sha256": selected_hash,
        "model": MODEL,
        "model_revision": MODEL_REVISION,
        "model_variant": MODEL_VARIANT,
        "base_url": BASE_URL,
        "thinking": True,
        "temperature": TEMPERATURE,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "default_concurrency": STAGE15_CONCURRENCY,
        "max_attempts_total": MAX_ATTEMPTS,
        "stage1_5_runs": 1,
        "random_seed": RANDOM_SEED,
        "retrieval": False,
        "system_prompt": None,
        "structured_output_constraint": False,
        "stage1_5_prompt_sha256": prompt_hash(STAGE15_TEMPLATE),
        "stage2": False,
        "human_audit": False,
        "vllm_version": os.environ.get("VLLM_VERSION")
        or parent_metadata.get("vllm_version"),
    }
    if paths.run_manifest.exists():
        existing = _read_json(paths.run_manifest)
        immutable = (
            "run_id",
            "parent_run_id",
            "parent_manifest_sha256",
            "parent_stage1_results_sha256",
            "selected_manifest_sha256",
            "model",
            "model_revision",
            "thinking",
            "temperature",
            "default_concurrency",
            "stage1_5_prompt_sha256",
            "vllm_version",
        )
        mismatches = [key for key in immutable if existing.get(key) != run_manifest.get(key)]
        if mismatches:
            raise RuntimeError(f"Existing Stage 1.5 manifest conflicts on: {', '.join(mismatches)}")
    else:
        manifest.to_parquet(paths.input_manifest, index=False)
        manifest.to_csv(paths.input_csv, index=False)
        (paths.root / "stage1_5_prompt.txt").write_text(
            STAGE15_TEMPLATE + "\n", encoding="utf-8"
        )
        _atomic_json(paths.run_manifest, run_manifest)
    return load_manifest(paths), paths


def prepare_stage2_expanded_run() -> tuple[pd.DataFrame, RunPaths]:
    stage1_paths = get_run_paths(smoke=False)
    stage15_paths = get_stage15_paths()
    for required in (
        stage1_paths.input_manifest,
        stage1_paths.run_manifest,
        stage1_paths.stage1_results,
        stage15_paths.input_manifest,
        stage15_paths.run_manifest,
        stage15_paths.stage1_results,
    ):
        if not required.exists():
            raise FileNotFoundError(f"Expanded Stage 2 parent artifact is missing: {required}")

    stage1_manifest = load_manifest(stage1_paths)
    stage1_metadata = _read_json(stage1_paths.run_manifest)
    if stage1_metadata.get("selected_manifest_sha256") != _stable_manifest_hash(stage1_manifest):
        raise RuntimeError("Canonical Stage 1 manifest hash does not match its run manifest")

    stage1 = pd.read_parquet(stage1_paths.stage1_results)
    stage15 = pd.read_parquet(stage15_paths.stage1_results)
    for frame, required, name in (
        (stage1, {"noteId", "status", "final_label"}, "Stage 1"),
        (stage15, {"noteId", "status", "stage1_5_label"}, "Stage 1.5"),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name} results lack columns: {sorted(missing)}")
        frame["noteId"] = frame["noteId"].astype(str)
        if frame["noteId"].duplicated().any():
            raise ValueError(f"{name} results contain duplicate noteIds")

    if set(stage1["noteId"]) != set(stage1_manifest["noteId"]):
        raise ValueError("Canonical Stage 1 results do not exactly cover its input manifest")
    stage15_manifest = load_manifest(stage15_paths)
    if set(stage15["noteId"]) != set(stage15_manifest["noteId"]):
        raise ValueError("Stage 1.5 results do not exactly cover its input manifest")

    strict_ids = set(
        stage1.loc[
            stage1["status"].eq("resolved")
            & stage1["final_label"].eq("sourced_factual_information"),
            "noteId",
        ]
    )
    recall_ids = set(
        stage15.loc[
            stage15["status"].eq("resolved")
            & stage15["stage1_5_label"].eq("sourced_factual_core_present"),
            "noteId",
        ]
    )
    if len(strict_ids) != 10_096:
        raise ValueError(f"Expected 10,096 strict Stage 1 candidates; found {len(strict_ids)}")
    if len(recall_ids) != 280:
        raise ValueError(f"Expected 280 Stage 1.5 recall candidates; found {len(recall_ids)}")
    overlap = strict_ids & recall_ids
    if overlap:
        raise ValueError(f"Strict and recall admission routes overlap for {len(overlap)} notes")

    selected_ids = strict_ids | recall_ids
    manifest = stage1_manifest[stage1_manifest["noteId"].isin(selected_ids)].copy()
    manifest["admission_route"] = manifest["noteId"].map(
        lambda note_id: "strict_stage1" if note_id in strict_ids else "stage1_5_recall"
    )
    manifest = manifest.sort_values("noteId").reset_index(drop=True)
    if len(manifest) != 10_376:
        raise ValueError(f"Expected 10,376 expanded Stage 2 candidates; found {len(manifest)}")

    paths = get_stage2_expanded_paths()
    paths.root.mkdir(parents=True, exist_ok=True)
    selected_hash = _stable_expanded_manifest_hash(manifest)
    stage15_metadata = _read_json(stage15_paths.run_manifest)
    run_manifest = {
        "run_id": STAGE2_EXPANDED_RUN_ID,
        "mode": "production-stage2-expanded",
        "parent_stage1_run_id": stage1_metadata.get("run_id"),
        "parent_stage15_run_id": stage15_metadata.get("run_id"),
        "parent_stage1_manifest_sha256": stage1_metadata.get("selected_manifest_sha256"),
        "parent_stage1_results_sha256": _file_sha256(stage1_paths.stage1_results),
        "parent_stage15_manifest_sha256": stage15_metadata.get("selected_manifest_sha256"),
        "parent_stage15_results_sha256": _file_sha256(stage15_paths.stage1_results),
        "selected_rows": len(manifest),
        "strict_stage1_rows": len(strict_ids),
        "stage1_5_recall_rows": len(recall_ids),
        "route_overlap_rows": 0,
        "selected_manifest_sha256": selected_hash,
        "selection": "strict Stage 1 sourced union Stage 1.5 sourced factual core present",
        "admission_route_sent_to_model": False,
        "model": MODEL,
        "model_revision": MODEL_REVISION,
        "model_variant": MODEL_VARIANT,
        "base_url": BASE_URL,
        "thinking": True,
        "temperature": TEMPERATURE,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "default_concurrency": STAGE2_EXPANDED_CONCURRENCY,
        "max_attempts_total": MAX_ATTEMPTS,
        "stage2_runs": 1,
        "rescue_threshold": STAGE2_RESCUE_THRESHOLD,
        "random_seed": RANDOM_SEED,
        "retrieval": False,
        "system_prompt": None,
        "structured_output_constraint": False,
        "stage2_prompt_sha256": prompt_hash(STAGE2_TEMPLATE),
        "vllm_version": os.environ.get("VLLM_VERSION")
        or stage15_metadata.get("vllm_version")
        or stage1_metadata.get("vllm_version"),
    }
    if paths.run_manifest.exists():
        existing = _read_json(paths.run_manifest)
        immutable = (
            "run_id", "parent_stage1_run_id", "parent_stage15_run_id",
            "parent_stage1_results_sha256", "parent_stage15_results_sha256",
            "selected_manifest_sha256", "model", "model_revision", "thinking",
            "temperature", "default_concurrency", "stage2_runs", "rescue_threshold",
            "stage2_prompt_sha256", "vllm_version",
        )
        mismatches = [key for key in immutable if existing.get(key) != run_manifest.get(key)]
        if mismatches:
            raise RuntimeError(
                f"Existing expanded Stage 2 manifest conflicts on: {', '.join(mismatches)}"
            )
    else:
        manifest.to_parquet(paths.input_manifest, index=False)
        manifest.to_csv(paths.input_csv, index=False)
        (paths.root / "stage2_prompt.txt").write_text(STAGE2_TEMPLATE + "\n", encoding="utf-8")
        _atomic_json(paths.run_manifest, run_manifest)
    return load_manifest(paths), paths


def load_manifest(paths: RunPaths) -> pd.DataFrame:
    if not paths.input_manifest.exists():
        raise FileNotFoundError(f"Run is not prepared: {paths.input_manifest}")
    frame = pd.read_parquet(paths.input_manifest)
    frame["noteId"] = frame["noteId"].astype(str)
    return frame


def stage1_shard_bounds(
    batch_number: int, total_notes: int, batch_size: int = STAGE1_SHARD_SIZE
) -> tuple[int, int]:
    if batch_number < 2:
        raise ValueError("Stage 1 shard batch_number must be at least 2")
    if batch_size <= 0:
        raise ValueError("Stage 1 shard batch_size must be positive")
    start = (batch_number - 1) * batch_size
    stop = min(start + batch_size, total_notes)
    if start >= total_notes:
        raise ValueError(
            f"Stage 1 batch {batch_number} starts at {start}, beyond {total_notes} notes"
        )
    return start, stop


def prepare_stage1_shard(
    batch_number: int, batch_size: int = STAGE1_SHARD_SIZE
) -> tuple[pd.DataFrame, RunPaths]:
    canonical = get_run_paths(smoke=False)
    global_manifest = load_manifest(canonical)
    canonical_metadata = json.loads(canonical.run_manifest.read_text(encoding="utf-8"))
    global_hash = _stable_manifest_hash(global_manifest)
    if canonical_metadata.get("selected_manifest_sha256") != global_hash:
        raise RuntimeError("Canonical input manifest hash does not match its run manifest")

    start, stop = stage1_shard_bounds(batch_number, len(global_manifest), batch_size)
    shard = global_manifest.iloc[start:stop].reset_index(drop=True)
    paths = get_stage1_shard_paths(batch_number)
    paths.root.mkdir(parents=True, exist_ok=True)
    metadata = dict(canonical_metadata)
    metadata.update(
        {
            "mode": "production-stage1-shard",
            "parent_run_id": RUN_ID,
            "parent_manifest_sha256": global_hash,
            "selected_rows": len(shard),
            "selected_manifest_sha256": _stable_manifest_hash(shard),
            "stage1_batch_number": batch_number,
            "stage1_batch_size": batch_size,
            "stage1_row_start": start,
            "stage1_row_stop": stop,
        }
    )
    if paths.run_manifest.exists():
        existing = json.loads(paths.run_manifest.read_text(encoding="utf-8"))
        immutable = (
            "parent_manifest_sha256",
            "selected_manifest_sha256",
            "model",
            "model_revision",
            "stage1_prompt_sha256",
            "stage1_batch_number",
            "stage1_batch_size",
            "stage1_row_start",
            "stage1_row_stop",
        )
        mismatches = [key for key in immutable if existing.get(key) != metadata.get(key)]
        if mismatches:
            raise RuntimeError(
                f"Existing Stage 1 shard manifest conflicts on: {', '.join(mismatches)}"
            )
    else:
        shard.to_parquet(paths.input_manifest, index=False)
        shard.to_csv(paths.input_csv, index=False)
        (paths.root / "stage1_prompt.txt").write_text(STAGE1_TEMPLATE + "\n", encoding="utf-8")
        (paths.root / "stage2_prompt.txt").write_text(STAGE2_TEMPLATE + "\n", encoding="utf-8")
        _atomic_json(paths.run_manifest, metadata)
    return load_manifest(paths), paths


def stage1_shard_status(batch_size: int = STAGE1_SHARD_SIZE) -> dict:
    canonical = get_run_paths(smoke=False)
    manifest = load_manifest(canonical)
    last_batch = (len(manifest) + batch_size - 1) // batch_size
    batches = []
    for batch_number in range(2, last_batch + 1):
        start, stop = stage1_shard_bounds(batch_number, len(manifest), batch_size)
        paths = get_stage1_shard_paths(batch_number)
        expected = stop - start
        if not paths.database.exists():
            batches.append(
                {
                    "batch_number": batch_number,
                    "expected": expected,
                    "resolved": 0,
                    "pending": expected,
                    "unresolved": 0,
                    "attempts": 0,
                    "retry_attempts": 0,
                    "reasoning_missing": 0,
                    "integrity": "not_started",
                }
            )
            continue
        shard = load_manifest(paths)
        store = CallStore(paths.database)
        try:
            store.integrity_check()
            results = aggregate_stage1(shard, store)
            attempts = store.all_attempts()
        finally:
            store.close()
        counts = results["status"].value_counts().to_dict()
        valid = attempts[attempts["status"] == "valid"]
        batches.append(
            {
                "batch_number": batch_number,
                "expected": expected,
                "resolved": int(counts.get("resolved", 0)),
                "pending": int(counts.get("pending", 0)),
                "unresolved": int(counts.get("unresolved", 0)),
                "attempts": len(attempts),
                "retry_attempts": int((attempts["attempt_no"] > 1).sum()),
                "reasoning_missing": int((valid["reasoning_present"] == 0).sum()),
                "integrity": "ok",
            }
        )
    return {
        "batch_size": batch_size,
        "remaining_universe": sum(row["expected"] for row in batches),
        "resolved": sum(row["resolved"] for row in batches),
        "pending": sum(row["pending"] for row in batches),
        "unresolved": sum(row["unresolved"] for row in batches),
        "retry_attempts": sum(row["retry_attempts"] for row in batches),
        "reasoning_missing": sum(row["reasoning_missing"] for row in batches),
        "batches": batches,
    }


def stage2_expanded_shard_bounds(
    batch_number: int,
    total_notes: int,
    batch_size: int = STAGE2_EXPANDED_SHARD_SIZE,
) -> tuple[int, int]:
    if batch_number < 1:
        raise ValueError("Expanded Stage 2 shard batch_number must be at least 1")
    if batch_size <= 0:
        raise ValueError("Expanded Stage 2 shard batch_size must be positive")
    start = (batch_number - 1) * batch_size
    stop = min(start + batch_size, total_notes)
    if start >= total_notes:
        raise ValueError(
            f"Expanded Stage 2 batch {batch_number} starts at {start}, "
            f"beyond {total_notes} notes"
        )
    return start, stop


def prepare_stage2_expanded_shard(
    batch_number: int, batch_size: int = STAGE2_EXPANDED_SHARD_SIZE
) -> tuple[pd.DataFrame, RunPaths]:
    canonical_manifest, canonical = prepare_stage2_expanded_run()
    canonical_metadata = _read_json(canonical.run_manifest)
    canonical_hash = _stable_expanded_manifest_hash(canonical_manifest)
    if canonical_metadata.get("selected_manifest_sha256") != canonical_hash:
        raise RuntimeError("Expanded Stage 2 manifest hash does not match its run manifest")

    start, stop = stage2_expanded_shard_bounds(
        batch_number, len(canonical_manifest), batch_size
    )
    shard = canonical_manifest.iloc[start:stop].reset_index(drop=True)
    paths = get_stage2_expanded_shard_paths(batch_number)
    paths.root.mkdir(parents=True, exist_ok=True)
    metadata = dict(canonical_metadata)
    metadata.update(
        {
            "mode": "production-stage2-expanded-shard",
            "parent_run_id": STAGE2_EXPANDED_RUN_ID,
            "parent_manifest_sha256": canonical_hash,
            "selected_rows": len(shard),
            "selected_manifest_sha256": _stable_expanded_manifest_hash(shard),
            "stage2_batch_number": batch_number,
            "stage2_batch_size": batch_size,
            "stage2_row_start": start,
            "stage2_row_stop": stop,
        }
    )
    if paths.run_manifest.exists():
        existing = _read_json(paths.run_manifest)
        immutable = (
            "parent_manifest_sha256", "selected_manifest_sha256", "model",
            "model_revision", "stage2_prompt_sha256", "rescue_threshold",
            "stage2_batch_number", "stage2_batch_size", "stage2_row_start",
            "stage2_row_stop",
        )
        mismatches = [key for key in immutable if existing.get(key) != metadata.get(key)]
        if mismatches:
            raise RuntimeError(
                f"Existing expanded Stage 2 shard conflicts on: {', '.join(mismatches)}"
            )
    else:
        shard.to_parquet(paths.input_manifest, index=False)
        shard.to_csv(paths.input_csv, index=False)
        (paths.root / "stage2_prompt.txt").write_text(STAGE2_TEMPLATE + "\n", encoding="utf-8")
        _atomic_json(paths.run_manifest, metadata)
    return load_manifest(paths), paths


def stage2_expanded_shard_status(
    batch_size: int = STAGE2_EXPANDED_SHARD_SIZE,
) -> dict:
    canonical = get_stage2_expanded_paths()
    manifest = load_manifest(canonical)
    last_batch = (len(manifest) + batch_size - 1) // batch_size
    batches = []
    for batch_number in range(1, last_batch + 1):
        start, stop = stage2_expanded_shard_bounds(batch_number, len(manifest), batch_size)
        paths = get_stage2_expanded_shard_paths(batch_number)
        expected = stop - start
        if not paths.database.exists():
            batches.append(
                {
                    "batch_number": batch_number,
                    "expected": expected,
                    "complete": 0,
                    "pending": expected,
                    "unresolved": 0,
                    "attempts": 0,
                    "retry_attempts": 0,
                    "reasoning_missing": 0,
                    "integrity": "not_started",
                }
            )
            continue
        shard = load_manifest(paths)
        store = CallStore(paths.database)
        try:
            store.integrity_check()
            results = aggregate_stage2_expanded(shard, store)
            attempts = store.all_attempts()
        finally:
            store.close()
        counts = results["status"].value_counts().to_dict()
        valid = attempts[
            (attempts["stage"] == "stage2_expanded") & (attempts["status"] == "valid")
        ]
        batches.append(
            {
                "batch_number": batch_number,
                "expected": expected,
                "complete": int(counts.get("complete", 0)),
                "pending": int(counts.get("pending", 0)),
                "unresolved": int(counts.get("unresolved", 0)),
                "attempts": len(attempts),
                "retry_attempts": int((attempts["attempt_no"] > 1).sum()),
                "reasoning_missing": int((valid["reasoning_present"] == 0).sum()),
                "integrity": "ok",
            }
        )
    return {
        "run_id": STAGE2_EXPANDED_RUN_ID,
        "batch_size": batch_size,
        "notes": len(manifest),
        "complete": sum(row["complete"] for row in batches),
        "pending": sum(row["pending"] for row in batches),
        "unresolved": sum(row["unresolved"] for row in batches),
        "retry_attempts": sum(row["retry_attempts"] for row in batches),
        "reasoning_missing": sum(row["reasoning_missing"] for row in batches),
        "batches": batches,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_sqlite(source: Path, destination: Path) -> None:
    destination.unlink(missing_ok=True)
    with (
        sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_conn,
        sqlite3.connect(destination) as destination_conn,
    ):
        source_conn.backup(destination_conn)
        row = destination_conn.execute("PRAGMA integrity_check").fetchone()
        if row is None or str(row[0]).lower() != "ok":
            raise RuntimeError(f"Copied SQLite integrity check failed: {row}")


def _validate_shard_metadata(
    canonical_metadata: dict,
    shard_metadata: dict,
    shard_manifest: pd.DataFrame,
    *,
    batch_number: int,
    batch_size: int,
    start: int,
    stop: int,
) -> None:
    for key in _SHARD_METADATA_KEYS:
        if shard_metadata.get(key) != canonical_metadata.get(key):
            raise RuntimeError(f"Batch {batch_number} metadata mismatch for {key}")
    expected = {
        "mode": "production-stage1-shard",
        "parent_run_id": canonical_metadata.get("run_id"),
        "parent_manifest_sha256": canonical_metadata.get("selected_manifest_sha256"),
        "selected_rows": stop - start,
        "selected_manifest_sha256": _stable_manifest_hash(shard_manifest),
        "stage1_batch_number": batch_number,
        "stage1_batch_size": batch_size,
        "stage1_row_start": start,
        "stage1_row_stop": stop,
    }
    for key, value in expected.items():
        if shard_metadata.get(key) != value:
            raise RuntimeError(f"Batch {batch_number} metadata mismatch for {key}")


def _merge_attempt_rows(
    destination: sqlite3.Connection,
    source_path: Path,
    expected_note_ids: set[str],
    *,
    batch_number: int,
    stage: str = "stage1",
) -> tuple[int, int]:
    columns_sql = ", ".join(_ATTEMPT_COLUMNS)
    placeholders = ", ".join("?" for _ in _ATTEMPT_COLUMNS)
    inserted = 0
    existing = 0
    with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        integrity = source.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or str(integrity[0]).lower() != "ok":
            raise RuntimeError(f"Batch {batch_number} SQLite integrity check failed")
        rows = source.execute(f"SELECT {columns_sql} FROM attempts ORDER BY id").fetchall()

    attempted_note_ids = {str(row["note_id"]) for row in rows}
    if attempted_note_ids != expected_note_ids:
        raise RuntimeError(f"Batch {batch_number} attempt note IDs do not match its manifest")

    for row in rows:
        note_id = str(row["note_id"])
        if row["stage"] != stage or row["logical_key"] != _logical_key(stage, note_id):
            raise RuntimeError(
                f"Batch {batch_number} contains an invalid {stage} logical key"
            )
        values = tuple(row[column] for column in _ATTEMPT_COLUMNS)
        current = destination.execute(
            f"SELECT {columns_sql} FROM attempts WHERE logical_key = ? AND attempt_no = ?",
            (row["logical_key"], row["attempt_no"]),
        ).fetchone()
        if current is not None:
            current_values = tuple(current[index] for index in range(len(_ATTEMPT_COLUMNS)))
            if current_values != values:
                raise RuntimeError(
                    f"Batch {batch_number} conflicts with canonical attempt "
                    f"{row['logical_key']} attempt {row['attempt_no']}"
                )
            existing += 1
            continue
        destination.execute(
            f"INSERT INTO attempts ({columns_sql}) VALUES ({placeholders})",
            values,
        )
        inserted += 1
    return inserted, existing


def merge_stage1_shards(batch_size: int = STAGE1_SHARD_SIZE) -> dict:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    paths = get_run_paths(smoke=False)
    manifest = load_manifest(paths)
    canonical_metadata = _read_json(paths.run_manifest)
    expected_manifest_hash = _stable_manifest_hash(manifest)
    if canonical_metadata.get("mode") != "production":
        raise RuntimeError("Canonical run manifest is not a production run")
    if canonical_metadata.get("selected_rows") != len(manifest):
        raise RuntimeError("Canonical run manifest row count does not match its input manifest")
    if canonical_metadata.get("selected_manifest_sha256") != expected_manifest_hash:
        raise RuntimeError("Canonical run manifest hash does not match its input manifest")
    last_batch = (len(manifest) + batch_size - 1) // batch_size
    temp_database = paths.database.with_name(paths.database.name + ".merge.tmp")
    temp_database.unlink(missing_ok=True)
    merged_batches = []
    replaced = False

    try:
        _copy_sqlite(paths.database, temp_database)
        destination = sqlite3.connect(temp_database)
        try:
            destination.execute("PRAGMA journal_mode=DELETE")
            destination.execute("PRAGMA synchronous=FULL")
            stage_rows = destination.execute(
                "SELECT DISTINCT stage FROM attempts"
            ).fetchall()
            if any(str(row[0]) != "stage1" for row in stage_rows):
                raise RuntimeError("Canonical database already contains non-Stage-1 attempts")
            destination.execute("BEGIN IMMEDIATE")
            for batch_number in range(2, last_batch + 1):
                start, stop = stage1_shard_bounds(batch_number, len(manifest), batch_size)
                shard_paths = get_stage1_shard_paths(batch_number)
                expected_manifest = manifest.iloc[start:stop].reset_index(drop=True)
                shard_manifest = load_manifest(shard_paths).reset_index(drop=True)
                if not shard_manifest.equals(expected_manifest):
                    raise RuntimeError(
                        f"Batch {batch_number} manifest does not match canonical rows {start}:{stop}"
                    )
                _validate_shard_metadata(
                    canonical_metadata,
                    _read_json(shard_paths.run_manifest),
                    shard_manifest,
                    batch_number=batch_number,
                    batch_size=batch_size,
                    start=start,
                    stop=stop,
                )
                inserted, existing = _merge_attempt_rows(
                    destination,
                    shard_paths.database,
                    set(shard_manifest["noteId"].astype(str)),
                    batch_number=batch_number,
                )
                merged_batches.append(
                    {
                        "batch_number": batch_number,
                        "notes": len(shard_manifest),
                        "inserted_attempts": inserted,
                        "existing_attempts": existing,
                    }
                )
            destination.commit()
        except Exception:
            destination.rollback()
            raise
        finally:
            destination.close()

        store = CallStore(temp_database)
        try:
            store.integrity_check()
            stage1 = aggregate_stage1(manifest, store)
            attempts = store.all_attempts()
            counts = stage1["status"].value_counts().to_dict()
            valid = attempts[(attempts["stage"] == "stage1") & (attempts["status"] == "valid")]
            if int(counts.get("pending", 0)) != 0:
                raise RuntimeError("Merged Stage 1 database still contains pending notes")
            if int(valid["logical_key"].duplicated().sum()) != 0:
                raise RuntimeError("Merged Stage 1 database contains duplicate valid calls")
            if int((valid["reasoning_present"] == 0).sum()) != 0:
                raise RuntimeError("Merged Stage 1 database contains valid calls without reasoning")
            if set(attempts["note_id"].astype(str)) != set(manifest["noteId"].astype(str)):
                raise RuntimeError("Merged Stage 1 attempt IDs do not match the canonical manifest")
        finally:
            store.close()

        with temp_database.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp_database, paths.database)
        replaced = True

        store = CallStore(paths.database)
        try:
            store.integrity_check()
            summary = export_run(manifest, paths, store)
            store.backup(paths.database_backup)
            store.integrity_check()
            attempts = store.all_attempts()
        finally:
            store.close()
        return {
            "run_id": RUN_ID,
            "batches": merged_batches,
            "attempts": len(attempts),
            "inserted_attempts": sum(row["inserted_attempts"] for row in merged_batches),
            "existing_attempts": sum(row["existing_attempts"] for row in merged_batches),
            "stage1_status": summary["stage1_status"],
            "reasoning_missing": int(
                (
                    (attempts["stage"] == "stage1")
                    & (attempts["status"] == "valid")
                    & (attempts["reasoning_present"] == 0)
                ).sum()
            ),
        }
    finally:
        if not replaced:
            temp_database.unlink(missing_ok=True)


def _validate_stage2_expanded_shard_metadata(
    canonical_metadata: dict,
    shard_metadata: dict,
    shard_manifest: pd.DataFrame,
    *,
    batch_number: int,
    batch_size: int,
    start: int,
    stop: int,
) -> None:
    shared_keys = (
        "run_id", "parent_stage1_run_id", "parent_stage15_run_id",
        "parent_stage1_manifest_sha256", "parent_stage1_results_sha256",
        "parent_stage15_manifest_sha256", "parent_stage15_results_sha256",
        "strict_stage1_rows", "stage1_5_recall_rows", "route_overlap_rows",
        "model", "model_revision", "model_variant", "thinking", "temperature",
        "max_completion_tokens", "max_attempts_total", "stage2_runs",
        "rescue_threshold", "random_seed", "retrieval", "system_prompt",
        "structured_output_constraint", "stage2_prompt_sha256", "vllm_version",
    )
    for key in shared_keys:
        if shard_metadata.get(key) != canonical_metadata.get(key):
            raise RuntimeError(f"Batch {batch_number} metadata mismatch for {key}")
    expected = {
        "mode": "production-stage2-expanded-shard",
        "parent_run_id": canonical_metadata.get("run_id"),
        "parent_manifest_sha256": canonical_metadata.get("selected_manifest_sha256"),
        "selected_rows": stop - start,
        "selected_manifest_sha256": _stable_expanded_manifest_hash(shard_manifest),
        "stage2_batch_number": batch_number,
        "stage2_batch_size": batch_size,
        "stage2_row_start": start,
        "stage2_row_stop": stop,
    }
    for key, value in expected.items():
        if shard_metadata.get(key) != value:
            raise RuntimeError(f"Batch {batch_number} metadata mismatch for {key}")


def merge_stage2_expanded_shards(
    batch_size: int = STAGE2_EXPANDED_SHARD_SIZE,
) -> dict:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    paths = get_stage2_expanded_paths()
    manifest = load_manifest(paths).reset_index(drop=True)
    canonical_metadata = _read_json(paths.run_manifest)
    expected_hash = _stable_expanded_manifest_hash(manifest)
    if canonical_metadata.get("mode") != "production-stage2-expanded":
        raise RuntimeError("Expanded Stage 2 run manifest has the wrong mode")
    if canonical_metadata.get("selected_rows") != len(manifest):
        raise RuntimeError("Expanded Stage 2 row count does not match its manifest")
    if canonical_metadata.get("selected_manifest_sha256") != expected_hash:
        raise RuntimeError("Expanded Stage 2 hash does not match its manifest")

    last_batch = (len(manifest) + batch_size - 1) // batch_size
    temp_database = paths.database.with_name(paths.database.name + ".merge.tmp")
    temp_database.unlink(missing_ok=True)
    merged_batches = []
    replaced = False
    try:
        if paths.database.exists():
            _copy_sqlite(paths.database, temp_database)
        else:
            empty = CallStore(temp_database)
            empty.close()
        destination = sqlite3.connect(temp_database)
        try:
            destination.execute("PRAGMA journal_mode=DELETE")
            destination.execute("PRAGMA synchronous=FULL")
            stages = destination.execute("SELECT DISTINCT stage FROM attempts").fetchall()
            if any(str(row[0]) != "stage2_expanded" for row in stages):
                raise RuntimeError("Expanded Stage 2 database contains another stage")
            destination.execute("BEGIN IMMEDIATE")
            for batch_number in range(1, last_batch + 1):
                start, stop = stage2_expanded_shard_bounds(
                    batch_number, len(manifest), batch_size
                )
                shard_paths = get_stage2_expanded_shard_paths(batch_number)
                expected_manifest = manifest.iloc[start:stop].reset_index(drop=True)
                shard_manifest = load_manifest(shard_paths).reset_index(drop=True)
                if not shard_manifest.equals(expected_manifest):
                    raise RuntimeError(
                        f"Batch {batch_number} manifest does not match expanded rows {start}:{stop}"
                    )
                _validate_stage2_expanded_shard_metadata(
                    canonical_metadata,
                    _read_json(shard_paths.run_manifest),
                    shard_manifest,
                    batch_number=batch_number,
                    batch_size=batch_size,
                    start=start,
                    stop=stop,
                )
                inserted, existing = _merge_attempt_rows(
                    destination,
                    shard_paths.database,
                    set(shard_manifest["noteId"].astype(str)),
                    batch_number=batch_number,
                    stage="stage2_expanded",
                )
                merged_batches.append(
                    {
                        "batch_number": batch_number,
                        "notes": len(shard_manifest),
                        "inserted_attempts": inserted,
                        "existing_attempts": existing,
                    }
                )
            destination.commit()
        except Exception:
            destination.rollback()
            raise
        finally:
            destination.close()

        store = CallStore(temp_database)
        try:
            store.integrity_check()
            results = aggregate_stage2_expanded(manifest, store)
            attempts = store.all_attempts()
            counts = results["status"].value_counts().to_dict()
            valid = attempts[
                (attempts["stage"] == "stage2_expanded")
                & (attempts["status"] == "valid")
            ]
            if int(counts.get("pending", 0)) != 0:
                raise RuntimeError("Merged expanded Stage 2 database still has pending notes")
            if int(valid["logical_key"].duplicated().sum()) != 0:
                raise RuntimeError("Merged expanded Stage 2 database has duplicate valid calls")
            if int((valid["reasoning_present"] == 0).sum()) != 0:
                raise RuntimeError("Merged expanded Stage 2 valid calls lack reasoning")
            if set(attempts["note_id"].astype(str)) != set(manifest["noteId"].astype(str)):
                raise RuntimeError("Merged attempt IDs do not match the expanded manifest")
        finally:
            store.close()

        with temp_database.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp_database, paths.database)
        replaced = True
        store = CallStore(paths.database)
        try:
            store.integrity_check()
            summary = export_stage2_expanded(manifest, paths, store)
            store.backup(paths.database_backup)
            attempts = store.all_attempts()
        finally:
            store.close()
        return {
            "run_id": STAGE2_EXPANDED_RUN_ID,
            "batches": merged_batches,
            "attempts": len(attempts),
            "inserted_attempts": sum(row["inserted_attempts"] for row in merged_batches),
            "existing_attempts": sum(row["existing_attempts"] for row in merged_batches),
            "stage2_status": summary["stage2_status"],
            "strict_final_rows": summary["strict_final_rows"],
            "expanded_final_rows": summary["expanded_final_rows"],
            "stage1_5_contribution_rows": summary["stage1_5_contribution_rows"],
        }
    finally:
        if not replaced:
            temp_database.unlink(missing_ok=True)


def _logical_key(stage: str, note_id: str) -> str:
    return f"{stage}:{note_id}:round1:run1"


def _request_seed(stage: str, note_id: str, attempt_no: int) -> int:
    value = f"{RANDOM_SEED}:{stage}:{note_id}:{attempt_no}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(value).digest()[:4], "big") & 0x7FFFFFFF


def _http_status(exc: Exception) -> int | None:
    return int(exc.status_code) if isinstance(exc, APIStatusError) else None


def _normalize_model_name(value: str) -> str:
    return value.lower().replace(".", "").replace("-", "").replace("_", "").replace("/", "")


def _is_expected_model(returned_model: str) -> bool:
    returned = _normalize_model_name(returned_model)
    expected = _normalize_model_name(MODEL)
    return expected in returned or returned in expected


class ValidationRunner:
    def __init__(
        self,
        paths: RunPaths,
        *,
        concurrency: int = DEFAULT_CONCURRENCY,
        exporter: Callable[[pd.DataFrame, RunPaths, CallStore], dict] | None = None,
    ):
        if concurrency <= 0:
            raise ValueError("concurrency must be positive")
        self.paths = paths
        self.concurrency = concurrency
        self.store = CallStore(paths.database)
        self.store.integrity_check()
        self.client = LocalVLLMClient()
        self.exporter = exporter or export_run
        self.stop_event = asyncio.Event()
        self._checkpoint_lock = asyncio.Lock()
        self._processed_since_checkpoint = 0

    def request_stop(self) -> None:
        self.stop_event.set()

    async def close(self) -> None:
        await self.client.close()
        self.store.integrity_check()
        self.store.close()

    async def checkpoint(self, manifest: pd.DataFrame) -> None:
        async with self._checkpoint_lock:
            self.exporter(manifest, self.paths, self.store)
            self.store.backup(self.paths.database_backup)

    async def _obtain(
        self,
        *,
        stage: str,
        note_id: str,
        prompt: str,
        parser: Callable[[str], Stage1Response | Stage2Response],
    ) -> Stage1Response | Stage2Response | None:
        logical_key = _logical_key(stage, note_id)
        existing = self.store.valid_call(logical_key)
        if existing:
            if existing["label"] is not None:
                return Stage1Response(label=existing["label"], reason=existing["reason"])
            return Stage2Response(rescue_worthiness=int(existing["score"]), reason=existing["reason"])

        infrastructure_failures = 0
        while self.store.attempt_count(logical_key) < MAX_ATTEMPTS:
            if self.stop_event.is_set():
                return None
            attempt_no = self.store.next_attempt_no(logical_key)
            seed = _request_seed(stage, note_id, attempt_no)
            started = time.perf_counter()
            response = None
            try:
                response = await self.client.complete(prompt, seed=seed)
                parsed = parser(response.raw_response)
                self.store.save_attempt(
                    {
                        "logical_key": logical_key,
                        "stage": stage,
                        "note_id": note_id,
                        "round_no": 1,
                        "run_no": 1,
                        "attempt_no": attempt_no,
                        "seed": seed,
                        "status": "valid",
                        "returned_model": response.returned_model,
                        "finish_reason": response.finish_reason,
                        "label": getattr(parsed, "label", None),
                        "score": getattr(parsed, "rescue_worthiness", None),
                        "reason": parsed.reason,
                        "raw_response": response.raw_response,
                        "reasoning": response.reasoning,
                        "latency_ms": int((time.perf_counter() - started) * 1000),
                        **response.usage,
                    }
                )
                return parsed
            except SchemaError as exc:
                self.store.save_attempt(
                    {
                        "logical_key": logical_key, "stage": stage, "note_id": note_id,
                        "round_no": 1, "run_no": 1, "attempt_no": attempt_no,
                        "seed": seed, "status": "schema_error",
                        "error_type": type(exc).__name__, "error_message": str(exc),
                        "returned_model": response.returned_model if response else None,
                        "finish_reason": response.finish_reason if response else None,
                        "raw_response": response.raw_response if response else None,
                        "reasoning": response.reasoning if response else None,
                        "latency_ms": int((time.perf_counter() - started) * 1000),
                        **(response.usage if response else {}),
                    }
                )
            except Exception as exc:
                status = _http_status(exc)
                infrastructure = isinstance(
                    exc, (APIConnectionError, APITimeoutError, APIStatusError)
                )
                infrastructure_failures += int(infrastructure)
                self.store.save_attempt(
                    {
                        "logical_key": logical_key, "stage": stage, "note_id": note_id,
                        "round_no": 1, "run_no": 1, "attempt_no": attempt_no,
                        "seed": seed, "status": "response_error",
                        "error_type": type(exc).__name__, "error_message": str(exc)[:2000],
                        "http_status": status,
                        "returned_model": response.returned_model if response else None,
                        "finish_reason": response.finish_reason if response else None,
                        "raw_response": response.raw_response if response else None,
                        "reasoning": response.reasoning if response else None,
                        "latency_ms": int((time.perf_counter() - started) * 1000),
                        **(response.usage if response else {}),
                    }
                )
                if status in {400, 401, 403, 404}:
                    raise RuntimeError(f"Permanent local vLLM API error ({status}): {exc}") from exc
                if not infrastructure and not isinstance(
                    exc, (EmptyContentError, TruncatedResponseError)
                ):
                    raise
            if self.store.attempt_count(logical_key) < MAX_ATTEMPTS:
                await asyncio.sleep((2 ** (attempt_no - 1)) + random.random())

        if infrastructure_failures == MAX_ATTEMPTS:
            raise RuntimeError(f"vLLM infrastructure failed {MAX_ATTEMPTS} times for note {note_id}")
        return None

    async def preflight(self, manifest: pd.DataFrame) -> None:
        row = manifest.iloc[0]
        note_id = str(row["noteId"])
        result = await self._obtain(
            stage="preflight",
            note_id=note_id,
            prompt=render_stage1(str(row["note_text"])),
            parser=parse_stage1,
        )
        if result is None:
            raise RuntimeError("vLLM preflight did not produce valid Stage 1 JSON")
        record = self.store.valid_call(_logical_key("preflight", note_id))
        if not _is_expected_model(str(record["returned_model"] or "")):
            raise RuntimeError(
                f"Preflight returned {record['returned_model']!r}; expected {MODEL!r}"
            )
        if not record["reasoning_gzip"]:
            raise RuntimeError("Preflight returned no parsed Gemma thinking content")
        print(f"Preflight OK: model={record['returned_model']} label={result.label}")

    async def preflight_stage15(self, manifest: pd.DataFrame) -> int:
        row = manifest.iloc[0]
        note_id = str(row["noteId"])
        was_pending = self.store.valid_call(_logical_key("stage1_5", note_id)) is None
        result = await self._obtain(
            stage="stage1_5",
            note_id=note_id,
            prompt=render_stage15(str(row["note_text"])),
            parser=parse_stage15,
        )
        if result is None:
            raise RuntimeError("vLLM preflight did not produce valid Stage 1.5 JSON")
        record = self.store.valid_call(_logical_key("stage1_5", note_id))
        if not _is_expected_model(str(record["returned_model"] or "")):
            raise RuntimeError(
                f"Stage 1.5 preflight returned {record['returned_model']!r}; expected {MODEL!r}"
            )
        if not record["reasoning_gzip"]:
            raise RuntimeError("Stage 1.5 preflight returned no parsed Gemma thinking content")
        print(f"Stage 1.5 preflight OK: model={record['returned_model']} label={result.label}")
        return int(was_pending)

    async def preflight_stage2_expanded(self, manifest: pd.DataFrame) -> int:
        row = manifest.iloc[0]
        note_id = str(row["noteId"])
        logical_key = _logical_key("stage2_expanded", note_id)
        was_pending = self.store.valid_call(logical_key) is None
        result = await self._obtain(
            stage="stage2_expanded",
            note_id=note_id,
            prompt=render_stage2(str(row["note_text"])),
            parser=parse_stage2,
        )
        if result is None:
            raise RuntimeError("vLLM preflight did not produce valid expanded Stage 2 JSON")
        record = self.store.valid_call(logical_key)
        if not _is_expected_model(str(record["returned_model"] or "")):
            raise RuntimeError(
                f"Expanded Stage 2 preflight returned {record['returned_model']!r}; "
                f"expected {MODEL!r}"
            )
        if not record["reasoning_gzip"]:
            raise RuntimeError("Expanded Stage 2 preflight returned no Gemma thinking content")
        print(
            "Expanded Stage 2 preflight OK: "
            f"model={record['returned_model']} score={result.rescue_worthiness}"
        )
        return int(was_pending)

    async def _process_stage1_note(self, note_id: str, note_text: str) -> None:
        await self._obtain(
            stage="stage1", note_id=note_id, prompt=render_stage1(note_text), parser=parse_stage1
        )

    async def _process_stage2_note(self, note_id: str, note_text: str) -> None:
        await self._obtain(
            stage="stage2", note_id=note_id, prompt=render_stage2(note_text), parser=parse_stage2
        )

    async def _process_stage2_expanded_note(self, note_id: str, note_text: str) -> None:
        await self._obtain(
            stage="stage2_expanded",
            note_id=note_id,
            prompt=render_stage2(note_text),
            parser=parse_stage2,
        )

    async def _process_stage15_note(self, note_id: str, note_text: str) -> None:
        await self._obtain(
            stage="stage1_5",
            note_id=note_id,
            prompt=render_stage15(note_text),
            parser=parse_stage15,
        )

    async def _run_queue(
        self,
        manifest: pd.DataFrame,
        selected: pd.DataFrame,
        processor: Callable[[str, str], asyncio.Future],
    ) -> int:
        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        for row in selected.itertuples(index=False):
            queue.put_nowait((str(row.noteId), str(row.note_text)))
        failures: list[BaseException] = []
        processed = 0
        processed_lock = asyncio.Lock()

        async def worker() -> None:
            nonlocal processed
            while not self.stop_event.is_set():
                try:
                    note_id, note_text = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    await processor(note_id, note_text)
                    async with processed_lock:
                        processed += 1
                        self._processed_since_checkpoint += 1
                        should_checkpoint = self._processed_since_checkpoint >= EXPORT_EVERY
                        if should_checkpoint:
                            self._processed_since_checkpoint = 0
                    if should_checkpoint:
                        await self.checkpoint(manifest)
                except BaseException as exc:
                    failures.append(exc)
                    self.stop_event.set()
                finally:
                    queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(self.concurrency)]
        await asyncio.gather(*workers)
        await self.checkpoint(manifest)
        if failures:
            raise failures[0]
        return processed

    async def run_stage1(self, manifest: pd.DataFrame, max_notes: int) -> int:
        results = aggregate_stage1(manifest, self.store)
        pending = set(results.loc[results["status"] == "pending", "noteId"])
        selected = manifest[manifest["noteId"].isin(pending)].head(max_notes)
        print(
            f"Stage 1 batch: {len(selected)} pending notes "
            f"(max_notes={max_notes}, concurrency={self.concurrency})"
        )
        return await self._run_queue(manifest, selected, self._process_stage1_note)

    async def run_stage2(self, manifest: pd.DataFrame, max_notes: int) -> int:
        stage1 = aggregate_stage1(manifest, self.store)
        blocking = stage1[stage1["status"] == "pending"]
        if not blocking.empty:
            raise RuntimeError(f"Stage 1 is incomplete for {len(blocking)} notes")
        passes = set(
            stage1.loc[stage1["final_label"] == "sourced_factual_information", "noteId"]
        )
        stage2 = aggregate_stage2(manifest, stage1, self.store)
        complete = set(stage2.loc[stage2["status"].isin(["complete", "unresolved"]), "noteId"])
        selected = manifest[
            manifest["noteId"].isin(passes) & ~manifest["noteId"].isin(complete)
        ].head(max_notes)
        print(
            f"Stage 2 batch: {len(selected)} pending sourced notes "
            f"(max_notes={max_notes}, concurrency={self.concurrency})"
        )
        return await self._run_queue(manifest, selected, self._process_stage2_note)

    async def run_stage15(self, manifest: pd.DataFrame, max_notes: int) -> int:
        results = aggregate_stage15(manifest, self.store)
        pending = set(results.loc[results["status"] == "pending", "noteId"])
        selected = manifest[manifest["noteId"].isin(pending)].head(max_notes)
        print(
            f"Stage 1.5 batch: {len(selected)} pending opinion notes "
            f"(max_notes={max_notes}, concurrency={self.concurrency})"
        )
        return await self._run_queue(manifest, selected, self._process_stage15_note)

    async def run_stage2_expanded(self, manifest: pd.DataFrame, max_notes: int) -> int:
        results = aggregate_stage2_expanded(manifest, self.store)
        pending = set(results.loc[results["status"] == "pending", "noteId"])
        selected = manifest[manifest["noteId"].isin(pending)].head(max_notes)
        print(
            f"Expanded Stage 2 batch: {len(selected)} pending notes "
            f"(max_notes={max_notes}, concurrency={self.concurrency})"
        )
        return await self._run_queue(
            manifest, selected, self._process_stage2_expanded_note
        )


def _valid_by_note(store: CallStore, stage: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in store.valid_calls(stage):
        grouped[str(row["note_id"])].append(row)
    return grouped


def aggregate_stage1(manifest: pd.DataFrame, store: CallStore) -> pd.DataFrame:
    grouped = _valid_by_note(store, "stage1")
    rows = []
    for note in manifest.itertuples(index=False):
        note_id = str(note.noteId)
        values = grouped[note_id]
        label = str(values[0]["label"]) if values else None
        attempts = store.attempt_count(_logical_key("stage1", note_id))
        status = "resolved" if label else ("unresolved" if attempts >= MAX_ATTEMPTS else "pending")
        rows.append(
            {
                "noteId": note_id,
                "note_text": note.note_text,
                "old_gabriel_label": note.old_gabriel_label,
                "status": status,
                "final_label": label,
                "attempt_count": attempts,
                "valid_call_count": len(values),
            }
        )
    return pd.DataFrame(rows)


def aggregate_stage15(manifest: pd.DataFrame, store: CallStore) -> pd.DataFrame:
    grouped = _valid_by_note(store, "stage1_5")
    rows = []
    for note in manifest.itertuples(index=False):
        note_id = str(note.noteId)
        values = grouped[note_id]
        label = str(values[0]["label"]) if values else None
        attempts = store.attempt_count(_logical_key("stage1_5", note_id))
        status = "resolved" if label else ("unresolved" if attempts >= MAX_ATTEMPTS else "pending")
        rows.append(
            {
                "noteId": note_id,
                "note_text": note.note_text,
                "old_gabriel_label": getattr(note, "old_gabriel_label", None),
                "parent_stage1_status": getattr(note, "parent_stage1_status", "resolved"),
                "parent_stage1_label": getattr(
                    note, "parent_stage1_label", "opinion_or_speculation"
                ),
                "status": status,
                "stage1_5_label": label,
                "attempt_count": attempts,
                "valid_call_count": len(values),
            }
        )
    return pd.DataFrame(rows)


def aggregate_stage2(
    manifest: pd.DataFrame, stage1: pd.DataFrame, store: CallStore
) -> pd.DataFrame:
    grouped = _valid_by_note(store, "stage2")
    pass_ids = set(
        stage1.loc[stage1["final_label"] == "sourced_factual_information", "noteId"]
    )
    rows = []
    for note in manifest[manifest["noteId"].isin(pass_ids)].itertuples(index=False):
        note_id = str(note.noteId)
        values = grouped[note_id]
        score = int(values[0]["score"]) if values else None
        attempts = store.attempt_count(_logical_key("stage2", note_id))
        status = "complete" if score is not None else (
            "unresolved" if attempts >= MAX_ATTEMPTS else "pending"
        )
        rows.append(
            {
                "noteId": note_id,
                "note_text": note.note_text,
                "status": status,
                "rescue_worthiness": score,
                "attempt_count": attempts,
                "valid_call_count": len(values),
            }
        )
    return pd.DataFrame(
        rows,
        columns=(
            "noteId", "note_text", "status", "rescue_worthiness",
            "attempt_count", "valid_call_count",
        ),
    )


def aggregate_stage2_expanded(manifest: pd.DataFrame, store: CallStore) -> pd.DataFrame:
    grouped = _valid_by_note(store, "stage2_expanded")
    rows = []
    for note in manifest.itertuples(index=False):
        note_id = str(note.noteId)
        values = grouped[note_id]
        score = int(values[0]["score"]) if values else None
        attempts = store.attempt_count(_logical_key("stage2_expanded", note_id))
        status = "complete" if score is not None else (
            "unresolved" if attempts >= MAX_ATTEMPTS else "pending"
        )
        rows.append(
            {
                "noteId": note_id,
                "note_text": note.note_text,
                "admission_route": note.admission_route,
                "status": status,
                "rescue_worthiness": score,
                "passes_rescue_threshold": (
                    score >= STAGE2_RESCUE_THRESHOLD if score is not None else None
                ),
                "attempt_count": attempts,
                "valid_call_count": len(values),
            }
        )
    return pd.DataFrame(rows)


def export_run(manifest: pd.DataFrame, paths: RunPaths, store: CallStore) -> dict:
    paths.root.mkdir(parents=True, exist_ok=True)
    stage1 = aggregate_stage1(manifest, store)
    stage2 = aggregate_stage2(manifest, stage1, store)
    _atomic_parquet(stage1, paths.stage1_results)
    _atomic_parquet(stage1[stage1["status"] == "unresolved"], paths.stage1_unresolved)
    _atomic_parquet(stage2, paths.stage2_results)
    _atomic_parquet(stage2[stage2["status"] == "unresolved"], paths.stage2_unresolved)
    store.export(paths.calls_export, paths.raw_calls_export)
    attempts = store.all_attempts()
    first_attempts = attempts[attempts["attempt_no"] == 1] if not attempts.empty else attempts
    summary = {
        "run_id": RUN_ID,
        "notes": len(manifest),
        "stage1_status": stage1["status"].value_counts(dropna=False).to_dict(),
        "stage1_labels": stage1["final_label"].value_counts(dropna=False).to_dict(),
        "stage2_status": stage2["status"].value_counts(dropna=False).to_dict() if not stage2.empty else {},
        "attempt_status": attempts["status"].value_counts(dropna=False).to_dict() if not attempts.empty else {},
        "first_attempt_valid_rate": (
            float((first_attempts["status"] == "valid").mean()) if not first_attempts.empty else None
        ),
        "prompt_tokens": int(attempts["prompt_tokens"].fillna(0).sum()) if not attempts.empty else 0,
        "completion_tokens": int(attempts["completion_tokens"].fillna(0).sum()) if not attempts.empty else 0,
        "reasoning_tokens": int(attempts["reasoning_tokens"].fillna(0).sum()) if not attempts.empty else 0,
    }
    _atomic_json(paths.summary, summary)
    return summary


def export_stage2_expanded(
    manifest: pd.DataFrame, paths: RunPaths, store: CallStore
) -> dict:
    paths.root.mkdir(parents=True, exist_ok=True)
    results = aggregate_stage2_expanded(manifest, store)
    _atomic_parquet(results, paths.stage2_results)
    _atomic_parquet(
        results[results["status"] == "unresolved"], paths.stage2_unresolved
    )
    store.export(paths.calls_export, paths.raw_calls_export)
    attempts = store.all_attempts()
    relevant = attempts[attempts["stage"] == "stage2_expanded"] if not attempts.empty else attempts
    first_attempts = relevant[relevant["attempt_no"] == 1] if not relevant.empty else relevant
    passed = results[results["passes_rescue_threshold"].eq(True)]
    strict_final = int(passed["admission_route"].eq("strict_stage1").sum())
    recall_final = int(passed["admission_route"].eq("stage1_5_recall").sum())
    score_bins = pd.cut(
        results["rescue_worthiness"],
        bins=[-1, 9, 39, 49, 69, 89, 100],
        labels=["0-9", "10-39", "40-49", "50-69", "70-89", "90-100"],
    ).value_counts(sort=False)
    summary = {
        "run_id": STAGE2_EXPANDED_RUN_ID,
        "notes": len(manifest),
        "rescue_threshold": STAGE2_RESCUE_THRESHOLD,
        "stage2_status": {
            str(key): int(value) for key, value in results["status"].value_counts().items()
        },
        "route_counts": {
            str(key): int(value)
            for key, value in results["admission_route"].value_counts().items()
        },
        "strict_final_rows": strict_final,
        "expanded_final_rows": strict_final + recall_final,
        "stage1_5_contribution_rows": recall_final,
        "score_bins": {str(key): int(value) for key, value in score_bins.items()},
        "attempt_status": (
            {str(key): int(value) for key, value in relevant["status"].value_counts().items()}
            if not relevant.empty else {}
        ),
        "first_attempt_valid_rate": (
            float((first_attempts["status"] == "valid").mean())
            if not first_attempts.empty else None
        ),
        "retry_attempts": (
            int((relevant["attempt_no"] > 1).sum()) if not relevant.empty else 0
        ),
        "valid_calls_missing_reasoning": (
            int(
                (
                    (relevant["status"] == "valid")
                    & (relevant["reasoning_present"] == 0)
                ).sum()
            )
            if not relevant.empty else 0
        ),
        "prompt_tokens": int(relevant["prompt_tokens"].fillna(0).sum()) if not relevant.empty else 0,
        "completion_tokens": int(relevant["completion_tokens"].fillna(0).sum()) if not relevant.empty else 0,
        "reasoning_tokens": int(relevant["reasoning_tokens"].fillna(0).sum()) if not relevant.empty else 0,
    }
    _atomic_json(paths.summary, summary)
    return summary


def export_stage15(manifest: pd.DataFrame, paths: RunPaths, store: CallStore) -> dict:
    results = aggregate_stage15(manifest, store)
    _atomic_parquet(results, paths.stage1_results)
    _atomic_parquet(results[results["status"] == "unresolved"], paths.stage1_unresolved)
    store.export(paths.calls_export, paths.raw_calls_export)

    attempts = store.all_attempts()
    first_attempts = attempts[attempts["attempt_no"] == 1] if not attempts.empty else attempts
    resolved = results[results["status"] == "resolved"].copy()
    resolved["has_url"] = resolved["note_text"].str.contains(
        r"https?://|www\.", case=False, regex=True, na=False
    )

    labels_by_url: dict[str, dict[str, int]] = {}
    for has_url, group in resolved.groupby("has_url", dropna=False):
        key = "url" if bool(has_url) else "no_url"
        labels_by_url[key] = {
            str(label): int(count)
            for label, count in group["stage1_5_label"].value_counts().items()
        }

    labels_by_old: dict[str, dict[str, int]] = {}
    old_labels = resolved["old_gabriel_label"].fillna("missing")
    for old_label, group in resolved.assign(_old_label=old_labels).groupby("_old_label"):
        labels_by_old[str(old_label)] = {
            str(label): int(count)
            for label, count in group["stage1_5_label"].value_counts().items()
        }

    metadata = _read_json(paths.run_manifest)
    new_passes = int(
        results["stage1_5_label"].eq("sourced_factual_core_present").sum()
    )
    strict_sourced = int(metadata["strict_sourced_rows"])
    summary = {
        "run_id": STAGE15_RUN_ID,
        "parent_run_id": metadata["parent_run_id"],
        "notes": len(manifest),
        "stage1_5_status": {
            str(key): int(value) for key, value in results["status"].value_counts().items()
        },
        "stage1_5_labels": {
            str(key): int(value)
            for key, value in results["stage1_5_label"].value_counts(dropna=False).items()
        },
        "strict_sourced_rows": strict_sourced,
        "newly_admitted_rows": new_passes,
        "expanded_sourced_rows": strict_sourced + new_passes,
        "labels_by_url_presence": labels_by_url,
        "labels_by_old_gabriel_label": labels_by_old,
        "attempt_status": (
            {str(key): int(value) for key, value in attempts["status"].value_counts().items()}
            if not attempts.empty
            else {}
        ),
        "first_attempt_valid_rate": (
            float((first_attempts["status"] == "valid").mean())
            if not first_attempts.empty
            else None
        ),
        "valid_calls_missing_reasoning": int(
            (
                (attempts["stage"] == "stage1_5")
                & (attempts["status"] == "valid")
                & (attempts["reasoning_present"] == 0)
            ).sum()
        ) if not attempts.empty else 0,
        "prompt_tokens": int(attempts["prompt_tokens"].fillna(0).sum()) if not attempts.empty else 0,
        "completion_tokens": (
            int(attempts["completion_tokens"].fillna(0).sum()) if not attempts.empty else 0
        ),
        "reasoning_tokens": (
            int(attempts["reasoning_tokens"].fillna(0).sum()) if not attempts.empty else 0
        ),
    }
    _atomic_json(paths.summary, summary)
    return summary


def print_stage15_status() -> dict:
    paths = get_stage15_paths()
    manifest = load_manifest(paths)
    store = CallStore(paths.database)
    try:
        store.integrity_check()
        summary = export_stage15(manifest, paths, store)
    finally:
        store.close()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def print_status(*, smoke: bool) -> dict:
    paths = get_run_paths(smoke=smoke)
    manifest = load_manifest(paths)
    store = CallStore(paths.database)
    try:
        store.integrity_check()
        summary = export_run(manifest, paths, store)
    finally:
        store.close()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
