from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import signal
import time

from config import (
    DEFAULT_CONCURRENCY,
    SMOKE_NOTES,
    STAGE15_CONCURRENCY,
    STAGE1_SHARD_SIZE,
    STAGE2_EXPANDED_CONCURRENCY,
    STAGE2_EXPANDED_SHARD_SIZE,
    get_run_paths,
)
from pipeline import (
    ValidationRunner,
    export_run,
    export_stage15,
    export_stage2_expanded,
    load_manifest,
    merge_stage1_shards,
    merge_stage2_expanded_shards,
    prepare_run,
    prepare_stage15_run,
    prepare_stage1_shard,
    prepare_stage2_expanded_run,
    prepare_stage2_expanded_shard,
    print_stage15_status,
    print_status,
    stage1_shard_status,
    stage2_expanded_shard_status,
)
from storage import CallStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run checkpointed Gemma 4 31B note validation through local vLLM"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="use .artifacts/smoke instead of the production run directory",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="maximum independent requests in flight",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="freeze the exact input manifest without inference")
    subparsers.add_parser(
        "stage1-5-prepare", help="freeze resolved Stage 1 opinion notes for recall adjudication"
    )
    subparsers.add_parser(
        "stage1-5-status", help="rebuild Stage 1.5 exports and print current status"
    )
    subparsers.add_parser("preflight", help="run one strict local-vLLM compatibility call")
    subparsers.add_parser("smoke", help="run the fixed 128-note SCCKN Stage 1 benchmark")
    subparsers.add_parser("status", help="rebuild exports and print current run status")
    subparsers.add_parser("export", help="rebuild Parquet, JSON, raw, and backup artifacts")
    shard = subparsers.add_parser(
        "stage1-shard", help="run one deterministic Stage 1 production shard"
    )
    shard.add_argument("--batch-number", type=int, required=True)
    shard.add_argument("--batch-size", type=int, default=STAGE1_SHARD_SIZE)
    shard_status = subparsers.add_parser(
        "shard-status", help="report Stage 1 shard progress without merging"
    )
    shard_status.add_argument("--batch-size", type=int, default=STAGE1_SHARD_SIZE)
    merge_shards = subparsers.add_parser(
        "merge-stage1-shards", help="atomically merge reviewed Stage 1 shards"
    )
    merge_shards.add_argument("--batch-size", type=int, default=STAGE1_SHARD_SIZE)
    subparsers.add_parser(
        "stage2-expanded-prepare",
        help="freeze the strict plus Stage 1.5 expanded Stage 2 manifest",
    )
    stage2_expanded = subparsers.add_parser(
        "stage2-expanded-shard",
        help="run one deterministic expanded Stage 2 production shard",
    )
    stage2_expanded.add_argument("--batch-number", type=int, required=True)
    stage2_expanded.add_argument(
        "--batch-size", type=int, default=STAGE2_EXPANDED_SHARD_SIZE
    )
    stage2_expanded_status = subparsers.add_parser(
        "stage2-expanded-shard-status",
        help="report expanded Stage 2 shard progress without merging",
    )
    stage2_expanded_status.add_argument(
        "--batch-size", type=int, default=STAGE2_EXPANDED_SHARD_SIZE
    )
    merge_stage2_expanded = subparsers.add_parser(
        "merge-stage2-expanded-shards",
        help="atomically merge reviewed expanded Stage 2 shards",
    )
    merge_stage2_expanded.add_argument(
        "--batch-size", type=int, default=STAGE2_EXPANDED_SHARD_SIZE
    )
    for name in ("stage1", "stage2"):
        stage = subparsers.add_parser(name, help=f"run one bounded {name} batch")
        stage.add_argument(
            "--max-notes",
            type=int,
            required=True,
            help="maximum number of pending notes to process in this invocation",
        )
    stage15 = subparsers.add_parser(
        "stage1-5", help="run one bounded Stage 1.5 opinion-recall batch"
    )
    stage15.add_argument(
        "--max-notes",
        type=int,
        required=True,
        help="maximum number of pending Stage 1.5 notes to process",
    )
    return parser


async def _with_runner(paths, concurrency, operation, *, exporter=None) -> bool:
    runner = ValidationRunner(paths, concurrency=concurrency, exporter=exporter)
    loop = asyncio.get_running_loop()
    installed = []
    for signum in (signal.SIGUSR1, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, runner.request_stop)
            installed.append(signum)
        except NotImplementedError:
            pass
    try:
        await operation(runner)
        return runner.stop_event.is_set()
    finally:
        for signum in installed:
            loop.remove_signal_handler(signum)
        await runner.close()


def _run(paths, concurrency, operation, *, exporter=None) -> None:
    stopped = asyncio.run(
        _with_runner(paths, concurrency, operation, exporter=exporter)
    )
    if stopped:
        print("Graceful scheduler stop completed; committed calls will resume next job.")
        raise SystemExit(75)


def _atomic_benchmark(path, value) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_smoke() -> None:
    manifest, paths = prepare_run(smoke=True)

    _run(paths, 16, lambda runner: runner.preflight(manifest))
    phases = ((16, 32), (32, 48), (64, 48))
    phase_results = []
    for concurrency, max_notes in phases:
        started = time.perf_counter()
        processed_holder = {"count": 0}

        async def operation(runner, limit=max_notes) -> None:
            processed_holder["count"] = await runner.run_stage1(manifest, limit)

        _run(paths, concurrency, operation)
        elapsed = time.perf_counter() - started
        count = processed_holder["count"]
        phase_results.append(
            {
                "concurrency": concurrency,
                "notes": count,
                "seconds": round(elapsed, 3),
                "notes_per_second": round(count / elapsed, 6) if elapsed else 0.0,
            }
        )

    store = CallStore(paths.database)
    try:
        summary = export_run(manifest, paths, store)
        store.integrity_check()
        store.backup(paths.database_backup)
        attempts = store.all_attempts()
    finally:
        store.close()

    valid_stage1 = attempts[(attempts["stage"] == "stage1") & (attempts["status"] == "valid")]
    duplicate_valid = int(valid_stage1["logical_key"].duplicated().sum())
    reasoning_missing = int((valid_stage1["reasoning_present"] == 0).sum())
    best = max(phase_results, key=lambda row: row["notes_per_second"])
    model_load_seconds = float(os.environ.get("VLLM_LOAD_SECONDS", "0"))
    usable_seconds = max(0.0, 9 * 3600 - model_load_seconds)
    estimated_notes = usable_seconds * float(best["notes_per_second"])
    batch_cap = min(2000, max(250, math.floor(estimated_notes / 250) * 250))
    stage1_status = summary["stage1_status"]
    accepted = (
        int(stage1_status.get("resolved", 0)) == SMOKE_NOTES
        and int(stage1_status.get("pending", 0)) == 0
        and int(stage1_status.get("unresolved", 0)) == 0
        and duplicate_valid == 0
        and reasoning_missing == 0
        and float(summary["first_attempt_valid_rate"] or 0.0) >= 0.99
    )
    benchmark = {
        "accepted": accepted,
        "smoke_notes": SMOKE_NOTES,
        "model_load_seconds": round(model_load_seconds, 3),
        "phases": phase_results,
        "selected_concurrency": int(best["concurrency"]),
        "recommended_batch_cap": int(batch_cap),
        "duplicate_valid_calls": duplicate_valid,
        "valid_calls_missing_reasoning": reasoning_missing,
        "first_attempt_valid_rate": summary["first_attempt_valid_rate"],
        "stage1_status": stage1_status,
    }
    _atomic_benchmark(paths.benchmark, benchmark)
    print(json.dumps(benchmark, indent=2, ensure_ascii=False))
    if not accepted:
        raise RuntimeError("Smoke acceptance criteria failed; production must not start")


def main() -> None:
    args = build_parser().parse_args()
    if args.concurrency <= 0:
        raise ValueError("--concurrency must be positive")
    smoke = bool(args.smoke or args.command == "smoke")

    if args.command == "prepare":
        manifest, paths = prepare_run(smoke=smoke)
        print(f"Prepared {len(manifest):,} notes at {paths.root}")
        return
    if args.command == "stage1-5-prepare":
        manifest, paths = prepare_stage15_run()
        print(f"Prepared {len(manifest):,} Stage 1.5 notes at {paths.root}")
        return
    if args.command == "stage2-expanded-prepare":
        manifest, paths = prepare_stage2_expanded_run()
        print(f"Prepared {len(manifest):,} expanded Stage 2 notes at {paths.root}")
        return
    if args.command == "stage1-5-status":
        print_stage15_status()
        return
    if args.command == "stage1-5":
        if args.max_notes <= 0:
            raise ValueError("--max-notes must be positive")
        if args.concurrency != STAGE15_CONCURRENCY:
            raise ValueError(
                f"Stage 1.5 concurrency is frozen at {STAGE15_CONCURRENCY}"
            )
        manifest, paths = prepare_stage15_run()

        async def run_stage15(runner) -> None:
            preflight_calls = await runner.preflight_stage15(manifest)
            await runner.run_stage15(manifest, args.max_notes - preflight_calls)

        _run(
            paths,
            args.concurrency,
            run_stage15,
            exporter=export_stage15,
        )
        return
    if args.command == "smoke":
        run_smoke()
        return
    if args.command == "stage1-shard":
        manifest, paths = prepare_stage1_shard(args.batch_number, args.batch_size)
        _run(
            paths,
            args.concurrency,
            lambda runner: runner.run_stage1(manifest, len(manifest)),
        )
        return
    if args.command == "shard-status":
        print(json.dumps(stage1_shard_status(args.batch_size), indent=2, ensure_ascii=False))
        return
    if args.command == "merge-stage1-shards":
        print(json.dumps(merge_stage1_shards(args.batch_size), indent=2, ensure_ascii=False))
        return
    if args.command == "stage2-expanded-shard":
        if args.concurrency != STAGE2_EXPANDED_CONCURRENCY:
            raise ValueError(
                f"Expanded Stage 2 concurrency is frozen at {STAGE2_EXPANDED_CONCURRENCY}"
            )
        manifest, paths = prepare_stage2_expanded_shard(
            args.batch_number, args.batch_size
        )

        async def run_stage2_expanded(runner) -> None:
            preflight_calls = await runner.preflight_stage2_expanded(manifest)
            await runner.run_stage2_expanded(manifest, len(manifest) - preflight_calls)

        _run(
            paths,
            args.concurrency,
            run_stage2_expanded,
            exporter=export_stage2_expanded,
        )
        return
    if args.command == "stage2-expanded-shard-status":
        print(
            json.dumps(
                stage2_expanded_shard_status(args.batch_size),
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if args.command == "merge-stage2-expanded-shards":
        print(
            json.dumps(
                merge_stage2_expanded_shards(args.batch_size),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    paths = get_run_paths(smoke=smoke)
    if not paths.input_manifest.exists():
        prepare_run(smoke=smoke)
    manifest = load_manifest(paths)

    if args.command == "preflight":
        _run(paths, args.concurrency, lambda runner: runner.preflight(manifest))
    elif args.command == "stage1":
        if args.max_notes <= 0:
            raise ValueError("--max-notes must be positive")
        _run(
            paths,
            args.concurrency,
            lambda runner: runner.run_stage1(manifest, args.max_notes),
        )
    elif args.command == "stage2":
        if args.max_notes <= 0:
            raise ValueError("--max-notes must be positive")
        _run(
            paths,
            args.concurrency,
            lambda runner: runner.run_stage2(manifest, args.max_notes),
        )
    elif args.command == "status":
        print_status(smoke=smoke)
    elif args.command == "export":
        store = CallStore(paths.database)
        try:
            summary = export_run(manifest, paths, store)
            store.backup(paths.database_backup)
        finally:
            store.close()
        print(f"Exports refreshed: {summary}")


if __name__ == "__main__":
    main()
