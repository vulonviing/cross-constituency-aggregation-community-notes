from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from client import _reasoning_text
from config import MAX_ATTEMPTS, RunPaths
from pipeline import (
    ValidationRunner,
    _is_expected_model,
    _request_seed,
    _source_manifest,
    _stable_manifest_hash,
    _stable_expanded_manifest_hash,
    aggregate_stage1,
    aggregate_stage15,
    aggregate_stage2,
    aggregate_stage2_expanded,
    export_stage2_expanded,
    export_stage15,
    merge_stage1_shards,
    merge_stage2_expanded_shards,
    prepare_stage1_shard,
    prepare_stage15_run,
    prepare_stage2_expanded_run,
    prepare_stage2_expanded_shard,
    stage1_shard_bounds,
    stage2_expanded_shard_bounds,
)
from prompts import (
    STAGE1_LABELS,
    STAGE1_TEMPLATE,
    STAGE15_LABELS,
    STAGE15_TEMPLATE,
    STAGE2_TEMPLATE,
    prompt_hash,
    render_stage1,
    render_stage15,
    render_stage2,
)
from run_validation import build_parser
from schemas import SchemaError, parse_stage1, parse_stage15, parse_stage2
from storage import CallStore


class SchemaTests(unittest.TestCase):
    def test_stage1_accepts_exact_contract(self) -> None:
        value = parse_stage1(
            json.dumps(
                {
                    "label": "sourced_factual_information",
                    "reason": "The note makes a sourced factual explanation.",
                }
            )
        )
        self.assertEqual(value.label, "sourced_factual_information")

    def test_stage1_rejects_extra_keys_and_unknown_labels(self) -> None:
        with self.assertRaises(SchemaError):
            parse_stage1('{"label":"other","reason":"No.","confidence":1}')

    def test_known_prefixes_are_normalized(self) -> None:
        value = parse_stage1(
            '{"{"label":"opinion_or_speculation","reason":"The note is subjective."}'
        )
        self.assertEqual(value.label, "opinion_or_speculation")
        fenced = parse_stage1(
            '```{"label":"sourced_factual_information","reason":"The note cites a source."}'
        )
        self.assertEqual(fenced.label, "sourced_factual_information")

    def test_stage2_requires_bounded_integer(self) -> None:
        self.assertEqual(
            parse_stage2(
                '{"rescue_worthiness":70,"reason":"Clear and traceable."}'
            ).rescue_worthiness,
            70,
        )
        for raw in (
            '{"rescue_worthiness":70.5,"reason":"No."}',
            '{"rescue_worthiness":101,"reason":"No."}',
        ):
            with self.assertRaises(SchemaError):
                parse_stage2(raw)

    def test_stage15_accepts_only_frozen_binary_contract(self) -> None:
        value = parse_stage15(
            '{"label":"sourced_factual_core_present","reason":"A substantial sourced core remains."}'
        )
        self.assertEqual(value.label, "sourced_factual_core_present")
        with self.assertRaises(SchemaError):
            parse_stage15(
                '{"label":"opinion_or_speculation","reason":"This is still opinion."}'
            )


class PromptContractTests(unittest.TestCase):
    def test_reasoning_supports_current_and_legacy_vllm_fields(self) -> None:
        current = SimpleNamespace(reasoning="current thinking")
        legacy = SimpleNamespace(reasoning_content="legacy thinking")
        extra = SimpleNamespace(model_extra={"reasoning_content": "extra thinking"})
        self.assertEqual(_reasoning_text(current), "current thinking")
        self.assertEqual(_reasoning_text(legacy), "legacy thinking")
        self.assertEqual(_reasoning_text(extra), "extra thinking")

    def test_prompts_are_unchanged_single_note_contracts(self) -> None:
        self.assertEqual(
            prompt_hash(STAGE1_TEMPLATE),
            "fbbd4bd93fb419ad66cce097bb18a8705fd331f38ec1a9bf433aa783281023d2",
        )
        self.assertEqual(
            prompt_hash(STAGE2_TEMPLATE),
            "8c98c54b9c413ee70c161f40ec8e89f0b19ac6420b2bfe669e7ee1f9b136c644",
        )
        self.assertEqual(
            prompt_hash(STAGE15_TEMPLATE),
            "26114bb8632357166cf4cee9a4f0ce356ed1e9e527477d56c842e53415bc930f",
        )
        note = "Example note https://example.com/source"
        combined = render_stage1(note) + render_stage15(note) + render_stage2(note)
        self.assertEqual(combined.count(note), 3)
        self.assertNotIn("Gabriel", combined)
        for label in STAGE1_LABELS:
            self.assertIn(label, combined)
        for label in STAGE15_LABELS:
            self.assertIn(label, combined)

    def test_attempt_seeds_are_stable_and_distinct(self) -> None:
        first = _request_seed("stage1", "123", 1)
        self.assertEqual(first, _request_seed("stage1", "123", 1))
        self.assertNotEqual(first, _request_seed("stage1", "123", 2))
        self.assertNotEqual(first, _request_seed("stage2", "123", 1))


class StorageAndAggregationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database = self.root / "calls.sqlite3"
        self.store = CallStore(self.database)
        self.manifest = pd.DataFrame(
            [
                {
                    "noteId": "1",
                    "note_text": "A sourced note https://example.com/a",
                    "old_gabriel_label": None,
                },
                {
                    "noteId": "2",
                    "note_text": "An invalid note",
                    "old_gabriel_label": None,
                },
            ]
        )

    def tearDown(self) -> None:
        self.store.close()
        self.tempdir.cleanup()

    def _save(self, *, stage: str, note_id: str, attempt_no: int, status: str, label=None, score=None) -> None:
        self.store.save_attempt(
            {
                "logical_key": f"{stage}:{note_id}:round1:run1",
                "stage": stage,
                "note_id": note_id,
                "round_no": 1,
                "run_no": 1,
                "attempt_no": attempt_no,
                "seed": attempt_no,
                "status": status,
                "returned_model": "google/gemma-4-31B-it",
                "finish_reason": "stop",
                "label": label,
                "score": score,
                "reason": "Valid reason." if status == "valid" else None,
                "raw_response": "{}",
                "reasoning": "private reasoning" if status == "valid" else None,
                "prompt_tokens": 10,
                "cached_tokens": 5,
                "completion_tokens": 3,
                "reasoning_tokens": 2,
                "latency_ms": 10,
            }
        )

    def test_nfs_safe_journal_and_integrity(self) -> None:
        mode = self.store._conn.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(str(mode).lower(), "delete")
        self.store.integrity_check()

    def test_resume_and_terminal_unresolved(self) -> None:
        self._save(
            stage="stage1",
            note_id="1",
            attempt_no=1,
            status="valid",
            label="sourced_factual_information",
        )
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._save(
                stage="stage1", note_id="2", attempt_no=attempt, status="schema_error"
            )
        stage1 = aggregate_stage1(self.manifest, self.store).set_index("noteId")
        self.assertEqual(stage1.loc["1", "status"], "resolved")
        self.assertEqual(stage1.loc["2", "status"], "unresolved")
        self.assertEqual(stage1.loc["1", "valid_call_count"], 1)

        self._save(stage="stage2", note_id="1", attempt_no=1, status="valid", score=70)
        stage2 = aggregate_stage2(self.manifest, stage1.reset_index(), self.store)
        self.assertEqual(stage2.iloc[0]["rescue_worthiness"], 70)
        self.assertEqual(stage2.iloc[0]["status"], "complete")

    def test_stage15_aggregation_is_isolated_from_stage1(self) -> None:
        self._save(
            stage="stage1_5",
            note_id="1",
            attempt_no=1,
            status="valid",
            label="sourced_factual_core_present",
        )
        results = aggregate_stage15(self.manifest, self.store).set_index("noteId")
        self.assertEqual(results.loc["1", "stage1_5_label"], "sourced_factual_core_present")
        self.assertEqual(results.loc["1", "status"], "resolved")
        self.assertEqual(results.loc["2", "status"], "pending")

    def test_stage15_export_reports_strict_and_expanded_counts(self) -> None:
        self._save(
            stage="stage1_5",
            note_id="1",
            attempt_no=1,
            status="valid",
            label="sourced_factual_core_present",
        )
        self._save(
            stage="stage1_5",
            note_id="2",
            attempt_no=1,
            status="valid",
            label="sourced_factual_core_absent",
        )
        paths = make_paths(self.root)
        paths.run_manifest.write_text(
            json.dumps(
                {
                    "parent_run_id": "parent-run",
                    "strict_sourced_rows": 10_096,
                }
            ),
            encoding="utf-8",
        )
        summary = export_stage15(self.manifest, paths, self.store)
        self.assertEqual(summary["newly_admitted_rows"], 1)
        self.assertEqual(summary["expanded_sourced_rows"], 10_097)
        self.assertEqual(summary["stage1_5_status"], {"resolved": 2})
        self.assertTrue(paths.stage1_results.exists())
        self.assertTrue(paths.raw_calls_export.exists())

    def test_expanded_stage2_threshold_and_routes_are_reported(self) -> None:
        manifest = self.manifest.copy()
        manifest["admission_route"] = ["strict_stage1", "stage1_5_recall"]
        self._save(
            stage="stage2_expanded", note_id="1", attempt_no=1,
            status="valid", score=50,
        )
        self._save(
            stage="stage2_expanded", note_id="2", attempt_no=1,
            status="valid", score=49,
        )
        results = aggregate_stage2_expanded(manifest, self.store).set_index("noteId")
        self.assertTrue(bool(results.loc["1", "passes_rescue_threshold"]))
        self.assertFalse(bool(results.loc["2", "passes_rescue_threshold"]))

        paths = make_paths(self.root)
        summary = export_stage2_expanded(manifest, paths, self.store)
        self.assertEqual(summary["strict_final_rows"], 1)
        self.assertEqual(summary["expanded_final_rows"], 1)
        self.assertEqual(summary["stage1_5_contribution_rows"], 0)
        self.assertTrue(paths.stage2_unresolved.exists())

    def test_atomic_backup_and_exports(self) -> None:
        self._save(
            stage="stage1",
            note_id="1",
            attempt_no=1,
            status="valid",
            label="sourced_factual_information",
        )
        backup = self.root / "calls.backup.sqlite3"
        parquet = self.root / "calls.parquet"
        raw = self.root / "raw.jsonl.gz"
        self.store.backup(backup)
        self.store.export(parquet, raw)
        self.assertTrue(backup.exists())
        self.assertTrue(parquet.exists())
        self.assertTrue(raw.exists())
        check = sqlite3.connect(backup).execute("PRAGMA integrity_check").fetchone()[0]
        self.assertEqual(check, "ok")
        self.assertFalse(list(self.root.glob("*.tmp*")))


class RunnerResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_graceful_stop_commits_and_resume_skips_completed_note(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = RunPaths(
                root=root,
                database=root / "calls.sqlite3",
                database_backup=root / "calls.backup.sqlite3",
                input_manifest=root / "input.parquet",
                input_csv=root / "input.csv",
                run_manifest=root / "manifest.json",
                stage1_results=root / "stage1.parquet",
                stage1_unresolved=root / "unresolved.parquet",
                stage2_results=root / "stage2.parquet",
                stage2_unresolved=root / "stage2_unresolved.parquet",
                calls_export=root / "calls.parquet",
                raw_calls_export=root / "raw.jsonl.gz",
                summary=root / "summary.json",
                benchmark=root / "benchmark.json",
            )
            manifest = pd.DataFrame(
                [
                    {"noteId": str(value), "note_text": f"Note {value}", "old_gabriel_label": None}
                    for value in range(1, 4)
                ]
            )

            runner = ValidationRunner(paths, concurrency=1)

            async def save_then_stop(note_id: str, _note_text: str) -> None:
                runner.store.save_attempt(
                    {
                        "logical_key": f"stage1:{note_id}:round1:run1",
                        "stage": "stage1", "note_id": note_id, "round_no": 1,
                        "run_no": 1, "attempt_no": 1, "seed": 1, "status": "valid",
                        "returned_model": "google/gemma-4-31B-it", "finish_reason": "stop",
                        "label": "unsourced_context_or_claim", "reason": "Valid reason.",
                        "raw_response": "{}", "reasoning": "reasoning",
                    }
                )
                runner.request_stop()

            runner._process_stage1_note = save_then_stop
            self.assertEqual(await runner.run_stage1(manifest, 3), 1)
            await runner.close()

            resumed = ValidationRunner(paths, concurrency=1)

            async def save_remaining(note_id: str, _note_text: str) -> None:
                resumed.store.save_attempt(
                    {
                        "logical_key": f"stage1:{note_id}:round1:run1",
                        "stage": "stage1", "note_id": note_id, "round_no": 1,
                        "run_no": 1, "attempt_no": 1, "seed": 1, "status": "valid",
                        "returned_model": "google/gemma-4-31B-it", "finish_reason": "stop",
                        "label": "unsourced_context_or_claim", "reason": "Valid reason.",
                        "raw_response": "{}", "reasoning": "reasoning",
                    }
                )

            resumed._process_stage1_note = save_remaining
            self.assertEqual(await resumed.run_stage1(manifest, 3), 2)
            stage1 = aggregate_stage1(manifest, resumed.store)
            self.assertEqual(stage1["status"].tolist(), ["resolved", "resolved", "resolved"])
            attempts = resumed.store.all_attempts()
            self.assertEqual(int(attempts["logical_key"].duplicated().sum()), 0)
            await resumed.close()


class SourceDataTests(unittest.TestCase):
    def test_exact_gabriel_input_universe(self) -> None:
        manifest = _source_manifest()
        self.assertEqual(len(manifest), 13_655)
        self.assertEqual(manifest["noteId"].nunique(), 13_655)
        self.assertEqual(int(manifest["note_text"].isna().sum()), 0)

    def test_stage15_manifest_is_exact_resolved_opinion_subset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stage15_paths = make_paths(Path(directory) / "stage15")
            stage15_paths = RunPaths(
                **{
                    **stage15_paths.__dict__,
                    "stage1_results": stage15_paths.root / "stage1_5_results.parquet",
                    "stage1_unresolved": stage15_paths.root / "stage1_5_unresolved.parquet",
                }
            )
            with patch("pipeline.get_stage15_paths", return_value=stage15_paths):
                manifest, _ = prepare_stage15_run()
        self.assertEqual(len(manifest), 1_703)
        self.assertEqual(manifest["noteId"].nunique(), 1_703)
        self.assertEqual(set(manifest["parent_stage1_status"]), {"resolved"})
        self.assertEqual(
            set(manifest["parent_stage1_label"]), {"opinion_or_speculation"}
        )

    def test_expanded_stage2_manifest_is_exact_union(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = make_paths(Path(directory) / "stage2-expanded")
            with patch("pipeline.get_stage2_expanded_paths", return_value=paths):
                manifest, _ = prepare_stage2_expanded_run()
                resumed, _ = prepare_stage2_expanded_run()
        self.assertEqual(len(manifest), 10_376)
        self.assertEqual(manifest["noteId"].nunique(), 10_376)
        self.assertEqual(
            manifest["admission_route"].value_counts().to_dict(),
            {"strict_stage1": 10_096, "stage1_5_recall": 280},
        )
        self.assertEqual(
            _stable_expanded_manifest_hash(manifest),
            _stable_expanded_manifest_hash(resumed),
        )


def _save_valid_stage1(path: Path, note_id: str, *, reason: str = "Valid reason.") -> None:
    store = CallStore(path)
    try:
        store.save_attempt(
            {
                "logical_key": f"stage1:{note_id}:round1:run1",
                "stage": "stage1",
                "note_id": note_id,
                "round_no": 1,
                "run_no": 1,
                "attempt_no": 1,
                "seed": 1,
                "status": "valid",
                "returned_model": "google/gemma-4-31B-it",
                "finish_reason": "stop",
                "label": "sourced_factual_information",
                "reason": reason,
                "raw_response": "{}",
                "reasoning": "reasoning",
                "prompt_tokens": 10,
                "cached_tokens": 5,
                "completion_tokens": 3,
                "reasoning_tokens": 0,
                "latency_ms": 10,
            }
        )
    finally:
        store.close()


def _save_valid_stage2(path: Path, note_id: str, *, score: int = 50) -> None:
    store = CallStore(path)
    try:
        store.save_attempt(
            {
                "logical_key": f"stage2_expanded:{note_id}:round1:run1",
                "stage": "stage2_expanded",
                "note_id": note_id,
                "round_no": 1,
                "run_no": 1,
                "attempt_no": 1,
                "seed": 1,
                "status": "valid",
                "returned_model": "google/gemma-4-31B-it",
                "finish_reason": "stop",
                "score": score,
                "reason": "Valid reason.",
                "raw_response": "{}",
                "reasoning": "reasoning",
            }
        )
    finally:
        store.close()


def _expanded_merge_fixture(root: Path) -> tuple[RunPaths, dict[int, RunPaths]]:
    canonical = make_paths(root / "expanded")
    canonical.root.mkdir(parents=True)
    manifest = pd.DataFrame(
        [
            {
                "noteId": str(value),
                "note_text": f"Note {value}",
                "admission_route": (
                    "strict_stage1" if value < 3 else "stage1_5_recall"
                ),
            }
            for value in range(4)
        ]
    )
    manifest.to_parquet(canonical.input_manifest, index=False)
    metadata = {
        "run_id": "expanded-test",
        "mode": "production-stage2-expanded",
        "parent_stage1_run_id": "stage1",
        "parent_stage15_run_id": "stage15",
        "parent_stage1_manifest_sha256": "stage1-manifest",
        "parent_stage1_results_sha256": "stage1-results",
        "parent_stage15_manifest_sha256": "stage15-manifest",
        "parent_stage15_results_sha256": "stage15-results",
        "selected_rows": 4,
        "strict_stage1_rows": 3,
        "stage1_5_recall_rows": 1,
        "route_overlap_rows": 0,
        "selected_manifest_sha256": _stable_expanded_manifest_hash(manifest),
        "model": "google/gemma-4-31B-it",
        "model_revision": "revision",
        "model_variant": "bf16-thinking",
        "thinking": True,
        "temperature": 0.2,
        "max_completion_tokens": 4096,
        "max_attempts_total": 3,
        "stage2_runs": 1,
        "rescue_threshold": 50,
        "random_seed": 42,
        "retrieval": False,
        "system_prompt": None,
        "structured_output_constraint": False,
        "stage2_prompt_sha256": prompt_hash(STAGE2_TEMPLATE),
        "vllm_version": "test",
    }
    canonical.run_manifest.write_text(json.dumps(metadata), encoding="utf-8")
    shards = {}
    for batch_number, start in ((1, 0), (2, 2)):
        shard = make_paths(
            canonical.root / "shards" / f"stage2-batch-{batch_number:04d}"
        )
        shard.root.mkdir(parents=True)
        selected = manifest.iloc[start:start + 2].reset_index(drop=True)
        selected.to_parquet(shard.input_manifest, index=False)
        shard_metadata = {
            **metadata,
            "mode": "production-stage2-expanded-shard",
            "parent_run_id": metadata["run_id"],
            "parent_manifest_sha256": metadata["selected_manifest_sha256"],
            "selected_rows": 2,
            "selected_manifest_sha256": _stable_expanded_manifest_hash(selected),
            "stage2_batch_number": batch_number,
            "stage2_batch_size": 2,
            "stage2_row_start": start,
            "stage2_row_stop": start + 2,
        }
        shard.run_manifest.write_text(json.dumps(shard_metadata), encoding="utf-8")
        for note_id in selected["noteId"]:
            _save_valid_stage2(shard.database, str(note_id), score=50 + start)
        shards[batch_number] = shard
    return canonical, shards


def _merge_fixture(root: Path) -> tuple[RunPaths, dict[int, RunPaths]]:
    canonical = make_paths(root / "canonical")
    canonical.root.mkdir(parents=True)
    manifest = pd.DataFrame(
        [
            {
                "noteId": str(value),
                "old_gabriel_label": "sourced_factual_information",
                "note_text": f"Note {value}",
                "note_sha256": f"hash-{value}",
            }
            for value in range(6)
        ]
    )
    manifest.to_parquet(canonical.input_manifest, index=False)
    metadata = {
        "run_id": "merge-test",
        "mode": "production",
        "source_universe_rows": 6,
        "selected_rows": 6,
        "source_universe_sha256": _stable_manifest_hash(manifest),
        "selected_manifest_sha256": _stable_manifest_hash(manifest),
        "model": "google/gemma-4-31B-it",
        "model_revision": "revision",
        "model_variant": "bf16-thinking",
        "thinking": True,
        "temperature": 0.2,
        "max_completion_tokens": 4096,
        "max_attempts_total": 3,
        "stage1_runs": 1,
        "stage2_runs": 1,
        "random_seed": 42,
        "retrieval": False,
        "system_prompt": None,
        "structured_output_constraint": False,
        "stage1_prompt_sha256": prompt_hash(STAGE1_TEMPLATE),
        "stage2_prompt_sha256": prompt_hash(STAGE2_TEMPLATE),
        "vllm_version": "test",
    }
    canonical.run_manifest.write_text(json.dumps(metadata), encoding="utf-8")
    for note_id in ("0", "1"):
        _save_valid_stage1(canonical.database, note_id)

    shards = {}
    for batch_number, start in ((2, 2), (3, 4)):
        shard = make_paths(canonical.root / "shards" / f"stage1-batch-{batch_number:04d}")
        shard.root.mkdir(parents=True)
        selected = manifest.iloc[start:start + 2].reset_index(drop=True)
        selected.to_parquet(shard.input_manifest, index=False)
        shard_metadata = {
            **metadata,
            "mode": "production-stage1-shard",
            "selected_rows": 2,
            "selected_manifest_sha256": _stable_manifest_hash(selected),
            "parent_run_id": metadata["run_id"],
            "parent_manifest_sha256": metadata["selected_manifest_sha256"],
            "stage1_batch_number": batch_number,
            "stage1_batch_size": 2,
            "stage1_row_start": start,
            "stage1_row_stop": start + 2,
        }
        shard.run_manifest.write_text(json.dumps(shard_metadata), encoding="utf-8")
        for note_id in selected["noteId"]:
            _save_valid_stage1(shard.database, str(note_id))
        shards[batch_number] = shard
    return canonical, shards


class Stage1ShardTests(unittest.TestCase):
    def test_batches_cover_remaining_universe_without_overlap(self) -> None:
        ranges = [stage1_shard_bounds(batch, 13_655, 2_000) for batch in range(2, 8)]
        self.assertEqual(
            ranges,
            [(2_000, 4_000), (4_000, 6_000), (6_000, 8_000),
             (8_000, 10_000), (10_000, 12_000), (12_000, 13_655)],
        )
        assigned = [index for start, stop in ranges for index in range(start, stop)]
        self.assertEqual(len(assigned), 11_655)
        self.assertEqual(len(set(assigned)), 11_655)
        self.assertTrue(set(assigned).isdisjoint(range(0, 2_000)))

    def test_prepare_shard_freezes_exact_slice_and_reuses_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = make_paths(root / "canonical")
            shard_paths = make_paths(root / "canonical" / "shards" / "stage1-batch-0002")
            canonical.root.mkdir(parents=True)
            manifest = pd.DataFrame(
                [
                    {
                        "noteId": str(value),
                        "note_text": f"Note {value}",
                        "old_gabriel_label": None,
                    }
                    for value in range(6)
                ]
            )
            manifest.to_parquet(canonical.input_manifest, index=False)
            canonical.run_manifest.write_text(
                json.dumps(
                    {
                        "run_id": "test",
                        "mode": "production",
                        "selected_manifest_sha256": _stable_manifest_hash(manifest),
                        "model": "google/gemma-4-31B-it",
                        "model_revision": "revision",
                        "stage1_prompt_sha256": prompt_hash(STAGE1_TEMPLATE),
                        "stage2_prompt_sha256": prompt_hash(STAGE2_TEMPLATE),
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch("pipeline.get_run_paths", return_value=canonical),
                patch("pipeline.get_stage1_shard_paths", return_value=shard_paths),
            ):
                shard, paths = prepare_stage1_shard(2, 2)
                resumed, resumed_paths = prepare_stage1_shard(2, 2)
            self.assertEqual(shard["noteId"].tolist(), ["2", "3"])
            self.assertEqual(resumed["noteId"].tolist(), ["2", "3"])
            self.assertEqual(paths, resumed_paths)
            metadata = json.loads(paths.run_manifest.read_text(encoding="utf-8"))
            self.assertEqual(metadata["stage1_row_start"], 2)
            self.assertEqual(metadata["stage1_row_stop"], 4)

    def test_array_dry_run_has_task_and_concurrency_caps(self) -> None:
        result = subprocess.run(
            ["bash", "jobs/submit_llm_validation.sh", "--dry-run", "stage1-array", "2-7", "3", "64"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("-t 2-7", result.stdout)
        self.assertIn("-tc 3", result.stdout)
        self.assertIn("-q gpu@scc213", result.stdout)
        self.assertIn("LLM_VALIDATION_CONCURRENCY=64", result.stdout)

    def test_stage15_dry_run_is_isolated_and_bounded(self) -> None:
        result = subprocess.run(
            ["bash", "jobs/submit_llm_validation.sh", "--dry-run", "stage1-5", "1703", "64"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("-N cn_gemma_s15", result.stdout)
        self.assertIn("gemma-4-31b-it-scckn-stage1-5-opinion-v1", result.stdout)
        self.assertIn("LLM_VALIDATION_ACTION=stage1-5", result.stdout)
        self.assertIn("LLM_VALIDATION_MAX_NOTES=1703", result.stdout)

    def test_reviewed_shards_merge_atomically_and_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical, shards = _merge_fixture(Path(directory))
            with (
                patch("pipeline.get_run_paths", return_value=canonical),
                patch(
                    "pipeline.get_stage1_shard_paths",
                    side_effect=lambda batch: shards[batch],
                ),
            ):
                first = merge_stage1_shards(batch_size=2)
                second = merge_stage1_shards(batch_size=2)

            self.assertEqual(first["inserted_attempts"], 4)
            self.assertEqual(first["existing_attempts"], 0)
            self.assertEqual(first["stage1_status"], {"resolved": 6})
            self.assertEqual(second["inserted_attempts"], 0)
            self.assertEqual(second["existing_attempts"], 4)
            self.assertEqual(second["attempts"], 6)
            self.assertTrue(canonical.database_backup.exists())
            self.assertFalse(canonical.database.with_name("calls.sqlite3.merge.tmp").exists())


class ExpandedStage2ShardTests(unittest.TestCase):
    def test_six_batches_cover_exact_expanded_universe(self) -> None:
        ranges = [
            stage2_expanded_shard_bounds(batch, 10_376, 2_000)
            for batch in range(1, 7)
        ]
        self.assertEqual(
            ranges,
            [
                (0, 2_000), (2_000, 4_000), (4_000, 6_000),
                (6_000, 8_000), (8_000, 10_000), (10_000, 10_376),
            ],
        )
        assigned = [index for start, stop in ranges for index in range(start, stop)]
        self.assertEqual(len(assigned), 10_376)
        self.assertEqual(len(set(assigned)), 10_376)

    def test_prepare_expanded_shard_freezes_route_aware_slice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = make_paths(Path(directory) / "canonical")
            shard_paths = make_paths(canonical.root / "shards" / "stage2-batch-0001")
            canonical.root.mkdir(parents=True)
            manifest = pd.DataFrame(
                [
                    {
                        "noteId": str(value),
                        "note_text": f"Note {value}",
                        "admission_route": "strict_stage1",
                    }
                    for value in range(4)
                ]
            )
            manifest.to_parquet(canonical.input_manifest, index=False)
            canonical.run_manifest.write_text(
                json.dumps(
                    {
                        "run_id": "test",
                        "selected_manifest_sha256": _stable_expanded_manifest_hash(manifest),
                        "model": "google/gemma-4-31B-it",
                        "model_revision": "revision",
                        "stage2_prompt_sha256": prompt_hash(STAGE2_TEMPLATE),
                        "rescue_threshold": 50,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch(
                    "pipeline.prepare_stage2_expanded_run",
                    return_value=(manifest, canonical),
                ),
                patch(
                    "pipeline.get_stage2_expanded_shard_paths",
                    return_value=shard_paths,
                ),
            ):
                shard, _ = prepare_stage2_expanded_shard(1, 2)
                resumed, _ = prepare_stage2_expanded_shard(1, 2)
            self.assertEqual(shard["noteId"].tolist(), ["0", "1"])
            self.assertTrue(shard.equals(resumed))

    def test_array_dry_run_is_pinned_and_bounded(self) -> None:
        result = subprocess.run(
            [
                "bash", "jobs/submit_llm_validation.sh", "--dry-run",
                "stage2-expanded-array", "1-6", "3", "64",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("-N cn_gemma_s2e", result.stdout)
        self.assertIn("-t 1-6", result.stdout)
        self.assertIn("-tc 3", result.stdout)
        self.assertIn("-q gpu@scc213", result.stdout)
        self.assertIn("LLM_VALIDATION_CONCURRENCY=64", result.stdout)

    def test_expanded_merge_is_atomic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical, shards = _expanded_merge_fixture(Path(directory))
            with (
                patch("pipeline.get_stage2_expanded_paths", return_value=canonical),
                patch(
                    "pipeline.get_stage2_expanded_shard_paths",
                    side_effect=lambda batch: shards[batch],
                ),
            ):
                first = merge_stage2_expanded_shards(batch_size=2)
                second = merge_stage2_expanded_shards(batch_size=2)
            self.assertEqual(first["inserted_attempts"], 4)
            self.assertEqual(first["expanded_final_rows"], 4)
            self.assertEqual(second["inserted_attempts"], 0)
            self.assertEqual(second["existing_attempts"], 4)
            self.assertTrue(canonical.database_backup.exists())
            self.assertFalse(
                canonical.database.with_name("calls.sqlite3.merge.tmp").exists()
            )

    def test_conflicting_attempt_stops_merge_without_replacing_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical, shards = _merge_fixture(Path(directory))
            _save_valid_stage1(canonical.database, "2", reason="Conflicting reason.")
            before = canonical.database.read_bytes()
            with (
                patch("pipeline.get_run_paths", return_value=canonical),
                patch(
                    "pipeline.get_stage1_shard_paths",
                    side_effect=lambda batch: shards[batch],
                ),
                self.assertRaisesRegex(RuntimeError, "conflicts with canonical attempt"),
            ):
                merge_stage1_shards(batch_size=2)
            self.assertEqual(canonical.database.read_bytes(), before)
            self.assertFalse(canonical.database.with_name("calls.sqlite3.merge.tmp").exists())


class SafetyTests(unittest.TestCase):
    def test_expected_model_aliases_are_accepted(self) -> None:
        self.assertTrue(_is_expected_model("google/gemma-4-31B-it"))
        self.assertTrue(_is_expected_model("gemma-4-31b-it"))
        self.assertFalse(_is_expected_model("mimo-v2.5-pro"))

    def test_stage_commands_require_explicit_note_bound(self) -> None:
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["stage1"])
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["stage1-5"])

    def test_stage1_shard_requires_explicit_batch_number(self) -> None:
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["stage1-shard"])


def make_paths(root: Path) -> RunPaths:
    return RunPaths(
        root=root,
        database=root / "calls.sqlite3",
        database_backup=root / "calls.backup.sqlite3",
        input_manifest=root / "input_manifest.parquet",
        input_csv=root / "input_manifest.csv",
        run_manifest=root / "run_manifest.json",
        stage1_results=root / "stage1_results.parquet",
        stage1_unresolved=root / "stage1_unresolved.parquet",
        stage2_results=root / "stage2_results.parquet",
        stage2_unresolved=root / "stage2_unresolved.parquet",
        calls_export=root / "calls.parquet",
        raw_calls_export=root / "raw_calls.jsonl.gz",
        summary=root / "summary.json",
        benchmark=root / "benchmark.json",
    )


if __name__ == "__main__":
    unittest.main()
