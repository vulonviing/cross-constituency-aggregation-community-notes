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
    line,
    outline_round_rect,
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
SOURCE = HERE / "community-notes-final-presentation-v16.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v17.pptx"
SOURCE_SHA256 = "294bd366983c5868dc5ecd2c306b29d989f46191e871fd7720ab72fbe59c8d53"
TARGET_SLIDE = "ppt/slides/slide31.xml"

EXPECTED_COUNTS = {
    "representative_picks": 44_722,
    "cca_qualified": 20_405,
    "already_shown": 6_750,
    "hidden_candidates": 13_655,
    "below_threshold": 24_317,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_counts() -> None:
    selection = pd.read_parquet(
        PROJECT_ROOT / "data" / "processed" / "selection_log.parquet",
        columns=["strategy", "status", "passes_bridge_threshold"],
    )
    representative = selection[selection["strategy"].eq("Representative")]
    qualified = representative["passes_bridge_threshold"].fillna(False).astype(bool)
    shown = representative["status"].eq("CURRENTLY_RATED_HELPFUL")

    actual = {
        "representative_picks": len(representative),
        "cca_qualified": int(qualified.sum()),
        "already_shown": int((qualified & shown).sum()),
        "hidden_candidates": int((qualified & ~shown).sum()),
        "below_threshold": int((~qualified).sum()),
    }
    if actual != EXPECTED_COUNTS:
        raise RuntimeError(f"Representative result counts changed: {actual}")


def result_node(
    slide,
    x: float,
    y: float,
    number: str,
    label: str,
    color: str,
    width: float,
    size: float = 29,
) -> None:
    textbox(slide, number, x, y, width, 0.52, size, color, True, PP_ALIGN.CENTER)
    bullet(
        slide,
        label,
        x,
        y + 0.66,
        width,
        11.8,
        MUTED,
        color,
        True,
        PP_ALIGN.CENTER,
    )


def representative_results(slide) -> None:
    title(slide, "RESULTS · REPRESENTATIVE", "What the platform shows—and hides", "13")

    # Full Representative selection universe.
    result_node(slide, 0.62, 2.54, "44,722", "Representative picks", INK, 2.20)
    line(slide, 2.88, 3.02, 3.55, 3.02, LIGHT, 1.5)
    textbox(slide, "→", 3.05, 2.83, 0.35, 0.30, 19, MUTED, True, PP_ALIGN.CENTER)

    # The common CCA threshold is applied before visibility is considered.
    outline_round_rect(slide, 3.58, 2.32, 1.78, 1.36, GREEN, 1.4)
    textbox(slide, "CCA BRIDGE SCORE", 3.73, 2.55, 1.48, 0.20, 8.7, GREEN, True,
            PP_ALIGN.CENTER)
    textbox(slide, "≥ 50%", 3.73, 2.86, 1.48, 0.44, 24, INK, True,
            PP_ALIGN.CENTER)

    line(slide, 5.38, 3.02, 6.03, 3.02, LIGHT, 1.5)
    textbox(slide, "→", 5.56, 2.83, 0.35, 0.30, 19, MUTED, True, PP_ALIGN.CENTER)
    result_node(slide, 6.00, 2.54, "20,405", "CCA-qualified · 46%", GREEN, 2.25)

    # Qualified notes split by their current platform visibility.
    line(slide, 8.30, 3.02, 8.78, 3.02, LIGHT, 1.5)
    line(slide, 8.78, 3.02, 9.30, 2.30, BLUE, 1.2)
    line(slide, 8.78, 3.02, 9.30, 4.12, GREEN, 1.2)
    result_node(slide, 9.25, 1.72, "6,750", "already shown · 33%", BLUE, 2.55, 28)
    result_node(
        slide,
        9.25,
        3.55,
        "13,655",
        "hidden rescue candidates · 67%",
        GREEN,
        2.85,
        28,
    )

    # Keep the rejected branch visible but subordinate to the qualified pool.
    line(slide, 4.47, 3.70, 4.47, 4.40, CORAL, 1.0)
    textbox(slide, "24,317", 3.62, 4.50, 1.70, 0.42, 21, CORAL, True,
            PP_ALIGN.CENTER)
    bullet(
        slide,
        "below threshold · 54%",
        3.35,
        5.04,
        2.25,
        10.2,
        MUTED,
        CORAL,
        True,
        PP_ALIGN.CENTER,
    )

    line(slide, 0.82, 5.75, 12.50, 5.75, LIGHT, 1.0)
    bullet(
        slide,
        "CCA identifies one qualified pool—some already shown, others hidden",
        2.17,
        6.08,
        9.00,
        16.0,
        INK,
        GREEN,
        True,
        PP_ALIGN.CENTER,
    )
    source(slide, "Authors’ 200k Representative pipeline")


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    representative_results(base_slide(presentation))
    presentation.save(path)


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V16 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(generated_path, "r") as generated_zip:
        replacement_slide = generated_zip.read("ppt/slides/slide1.xml")

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                payload = (
                    replacement_slide
                    if info.filename == TARGET_SLIDE
                    else source_zip.read(info.filename)
                )
                output_zip.writestr(info, payload)
        temporary.replace(OUTPUT)


def main() -> None:
    validate_counts()
    with tempfile.TemporaryDirectory() as directory:
        generated_path = Path(directory) / "representative-results.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
