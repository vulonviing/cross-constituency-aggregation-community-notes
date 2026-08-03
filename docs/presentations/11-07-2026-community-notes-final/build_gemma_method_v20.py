from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from build_two_problems_v4 import (
    BLUE,
    CORAL,
    GREEN,
    INK,
    LIGHT,
    MUTED,
    H,
    W,
    base_slide,
    bullet,
    circle,
    line,
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
SOURCE = HERE / "community-notes-final-presentation-v19.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v20.pptx"
SOURCE_SHA256 = "51351651071fad84daaf246e41fe8d83e7984626c2e1273cf53f56e10a5e7634"

CASE_SLIDE = "ppt/slides/slide35.xml"
METHOD_SLIDE = "ppt/slides/slide32.xml"
RUBRIC_SLIDE = "ppt/slides/slide34.xml"
CASE_NOTE_ID = "1741110453764239596"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def validate_case_score() -> None:
    stage1 = pd.read_parquet(
        PROJECT_ROOT
        / "data"
        / "llm_validation"
        / "runs"
        / "gemma-4-31b-it-scckn-v1"
        / "stage1_results.parquet"
    )
    stage2 = pd.read_parquet(
        PROJECT_ROOT
        / "data"
        / "llm_validation"
        / "runs"
        / "gemma-4-31b-it-scckn-stage2-expanded-v1"
        / "stage2_results.parquet"
    )
    stage1_row = stage1[stage1["noteId"].astype(str).eq(CASE_NOTE_ID)]
    stage2_row = stage2[stage2["noteId"].astype(str).eq(CASE_NOTE_ID)]
    if len(stage1_row) != 1 or len(stage2_row) != 1:
        raise RuntimeError("Canonical Gemma result for the case-study note is missing")
    if stage1_row.iloc[0]["final_label"] != "sourced_factual_information":
        raise RuntimeError("Case-study note no longer passes canonical Gemma Stage 1")
    score = int(stage2_row.iloc[0]["rescue_worthiness"])
    passed = bool(stage2_row.iloc[0]["passes_rescue_threshold"])
    if score != 82 or not passed:
        raise RuntimeError(
            f"Case-study Gemma result changed: score={score}, passed={passed}"
        )


def stage_label(slide, text: str, x: float, y: float, color: str) -> None:
    circle(slide, x, y + 0.01, 0.22, color)
    textbox(slide, text, x + 0.34, y, 1.90, 0.22, 10, color, True)


def gemma_method(slide) -> None:
    title(slide, "VALIDATION", "Gemma Validation", "13")
    line(slide, 6.66, 1.75, 6.66, 5.66, LIGHT, 1.0)

    # Stage 1 and targeted Stage 1.5 recall.
    stage_label(slide, "STAGE 1", 0.90, 1.78, BLUE)
    textbox(slide, "Nature + sourcing", 0.90, 2.18, 3.60, 0.32,
            19, INK, True)
    textbox(slide, "PASS", 0.92, 2.82, 0.72, 0.20, 8.5, GREEN, True)
    bullet(slide, "sourced factual information", 1.66, 2.77, 3.70,
           13, INK, GREEN, True)

    textbox(slide, "RECHECK", 0.92, 3.30, 0.85, 0.20, 8.5, BLUE, True)
    bullet(slide, "opinion / speculation", 1.78, 3.22, 3.55,
           11.8, MUTED, BLUE)
    textbox(slide, "STAGE 1.5 · SOURCED FACTUAL CORE", 1.78, 3.61, 3.45, 0.20,
            8.8, BLUE, True)

    textbox(slide, "STOP", 0.92, 4.05, 0.60, 0.20, 8.5, CORAL, True)
    for index, text in enumerate([
        "unsourced context / claim",
        "hostile / derogatory",
        "irrelevant / spam",
    ]):
        bullet(slide, text, 1.55, 3.98 + index * 0.40, 3.72,
               11.3, MUTED, CORAL)

    textbox(slide, "VISIBLE EXTERNAL SOURCE POINTER REQUIRED",
            0.92, 5.26, 4.95, 0.24, 10.5, BLUE, True)

    # Stage 2 rubric remains the same canonical prompt contract.
    stage_label(slide, "STAGE 2", 7.05, 1.78, GREEN)
    textbox(slide, "Rescue worthiness", 7.05, 2.18, 3.20, 0.32,
            19, INK, True)
    textbox(slide, "0–100", 10.82, 2.07, 1.35, 0.46,
            27, GREEN, True, PP_ALIGN.RIGHT)

    criteria = [
        "source traceability",
        "claim–source connection",
        "clarity and neutrality",
        "constructive presentation",
    ]
    for index, text in enumerate(criteria):
        bullet(slide, text, 7.08, 2.88 + index * 0.48, 3.55,
               12.5, MUTED, GREEN)

    line(slide, 7.06, 4.95, 12.15, 4.95, LIGHT, 0.9)
    textbox(slide, "≥50", 7.08, 5.17, 1.12, 0.40, 24, GREEN, True)
    textbox(slide, "→  VALIDATED", 8.22, 5.24, 2.55, 0.30,
            16, INK, True)

    line(slide, 0.82, 5.88, 12.50, 5.88, LIGHT, 1.0)
    bullet(
        slide,
        "Missing sourcing is a validation failure—not proof that the claim is false",
        1.50,
        6.20,
        10.35,
        14.5,
        INK,
        CORAL,
        True,
        PP_ALIGN.CENTER,
    )
    source(slide, "Canonical Gemma prompts · model-based validation")


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    gemma_method(base_slide(presentation))
    presentation.save(path)


def update_case_slide(payload: bytes) -> bytes:
    payload = replace_once(
        payload,
        b"<a:t>GABRIEL  70/100</a:t>",
        b"<a:t>GEMMA  82/100</a:t>",
        "case-study model score",
    )
    return replace_once(
        payload,
        "<a:t>• Authors’ Representative selection · historical Gabriel output</a:t>".encode("utf-8"),
        "<a:t>• Authors’ Representative selection · canonical Gemma output</a:t>".encode("utf-8"),
        "case-study source line",
    )


def update_rubric_slide(payload: bytes) -> bytes:
    return replace_once(
        payload,
        "<a:t>• Gabriel Stage-2 prompt · historical threshold ≥50</a:t>".encode("utf-8"),
        "<a:t>• Canonical Gemma Stage-2 prompt · threshold ≥50</a:t>".encode("utf-8"),
        "Stage-2 source line",
    )


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V19 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(generated_path, "r") as generated_zip:
        replacement_method = generated_zip.read("ppt/slides/slide1.xml")

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        replacements = {
            CASE_SLIDE: update_case_slide(source_zip.read(CASE_SLIDE)),
            METHOD_SLIDE: replacement_method,
            RUBRIC_SLIDE: update_rubric_slide(source_zip.read(RUBRIC_SLIDE)),
        }
        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                output_zip.writestr(
                    info, replacements.get(info.filename, source_zip.read(info.filename))
                )
        temporary.replace(OUTPUT)


def main() -> None:
    validate_case_score()
    with tempfile.TemporaryDirectory() as directory:
        generated_path = Path(directory) / "gemma-method.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
