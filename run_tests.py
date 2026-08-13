#!/usr/bin/env python3
"""Run every test in the repository with one command.

    python run_tests.py            # everything
    python run_tests.py -v         # per-test output

Three suites run, in this order:

  1. tests/test_scoring_units.py  — the aggregation rule, on synthetic data.
  2. tests/test_paper_numbers.py  — the paper's headline numbers, re-derived
                                    from the parquet files committed here.
  3. notebooks/llm_validation/    — the Gemma validation pipeline, with every
                                    model call mocked.

Only the standard library is needed to run them; pytest is not required. The
third suite imports its modules by bare name, so its directory is placed on
`sys.path` before discovery.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LLM_VALIDATION = REPO_ROOT / "notebooks" / "llm_validation"

SUITES = (
    ("pipeline and paper regressions", REPO_ROOT / "tests", REPO_ROOT),
    ("Gemma validation", LLM_VALIDATION, LLM_VALIDATION),
)


def main(argv: list[str]) -> int:
    verbosity = 2 if any(arg in {"-v", "--verbose"} for arg in argv) else 1

    for path in (REPO_ROOT, LLM_VALIDATION):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    loader = unittest.TestLoader()
    combined = unittest.TestSuite()
    for label, start_dir, top_level in SUITES:
        if not start_dir.is_dir():
            print(f"skipping {label}: {start_dir} not found", file=sys.stderr)
            continue
        combined.addTests(
            loader.discover(
                start_dir=str(start_dir), pattern="test_*.py", top_level_dir=str(top_level)
            )
        )

    result = unittest.TextTestRunner(verbosity=verbosity).run(combined)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
