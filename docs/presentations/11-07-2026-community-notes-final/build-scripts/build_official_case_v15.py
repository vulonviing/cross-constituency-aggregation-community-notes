from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from build_cherry_pick_v14 import metric
from build_two_problems_v4 import (
    BLUE,
    CORAL,
    GREEN,
    INK,
    LIGHT,
    MUTED,
    W,
    H,
    base_slide,
    bullet,
    line,
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v14.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v15.pptx"
SOURCE_SHA256 = "b318b6bd5ee538e96a1f48914cc222ccb69507e381ff4255bcfd190fbbaaaa2c"

PLATFORM_NOTE_ID = "1741061371389743362"
CCA_NOTE_ID = "1741110453764239596"

PLATFORM_TEXT = (
    "Russian state-controlled television regularly promotes shooting people who don’t "
    "want to live under Russian occupation, advocating for raping Ukrainian grannies "
    "and drowning Ukrainian children, and nuking the UK & invading further west."
)
CCA_TEXT = (
    "Russia does in fact consider western countries to be its enemies (a practice which "
    "actually predates the illegal full-scale Russian invasion of Ukraine) and regularly "
    "threatens them with nuclear and other strikes. Labelling Russia as enemy state is "
    "fully accurate."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def official_case(slide) -> None:
    title(slide, "CHERRY-PICKED CASE · RUSSIA / UKRAINE",
          "Same claim. Different standard.", "13")
    line(slide, 6.67, 1.70, 6.67, 5.74, LIGHT, 1.0)

    # Left: a provocative formulation that the platform currently displays.
    textbox(slide, "PLATFORM-SHOWN NOTE", 0.88, 1.66, 2.82, 0.23,
            10.5, CORAL, True)
    textbox(slide, f"NOTE {PLATFORM_NOTE_ID}", 3.55, 1.67, 2.36, 0.20,
            8.2, MUTED, True, PP_ALIGN.RIGHT)
    textbox(slide, "CURRENTLY_RATED_HELPFUL", 3.37, 1.91, 2.54, 0.18,
            8.2, CORAL, True, PP_ALIGN.RIGHT)
    textbox(slide, "83.7%", 0.90, 2.05, 1.65, 0.50,
            28, INK, True)
    textbox(slide, "overall approval", 2.40, 2.24, 1.65, 0.23,
            11.5, MUTED, True)
    metric(slide, "C0  57.5%", 0.92, 2.80, 1.52, BLUE)
    metric(slide, "C1  93.8%", 2.58, 2.80, 1.52, CORAL)
    metric(slide, "824 ratings", 4.52, 2.80, 1.22, MUTED, 10.5,
           PP_ALIGN.RIGHT)
    textbox(slide, "√(.575 × .938) = 73.4%", 0.92, 3.26, 2.90, 0.34,
            18.5, CORAL, True)
    textbox(slide, "PLATFORM SHOWS", 4.05, 3.29, 1.68, 0.28,
            13.5, CORAL, True, PP_ALIGN.RIGHT)
    line(slide, 0.90, 3.79, 5.78, 3.79, LIGHT, 0.9)
    textbox(slide, PLATFORM_TEXT, 0.92, 4.05, 4.98, 1.10,
            11.7, INK, False)
    textbox(slide, "SOURCES  YouTube · Newsweek · Business Insider",
            0.92, 5.31, 4.42, 0.20, 8.7, BLUE, True)

    # Right: the same core claim expressed more neutrally and selected by CCA.
    textbox(slide, "CCA / REPRESENTATIVE PICK", 7.02, 1.66, 3.18, 0.23,
            10.5, GREEN, True)
    textbox(slide, f"NOTE {CCA_NOTE_ID}", 10.36, 1.67, 2.06, 0.20,
            8.2, MUTED, True, PP_ALIGN.RIGHT)
    textbox(slide, "NEEDS_MORE_RATINGS", 10.30, 1.91, 2.12, 0.18,
            8.2, MUTED, True, PP_ALIGN.RIGHT)
    textbox(slide, "86.9%", 7.04, 2.05, 1.65, 0.50,
            28, INK, True)
    textbox(slide, "overall approval", 8.54, 2.24, 1.65, 0.23,
            11.5, MUTED, True)
    textbox(slide, "GABRIEL  70/100", 10.52, 2.19, 1.90, 0.25,
            12.5, GREEN, True, PP_ALIGN.RIGHT)
    metric(slide, "C0  66.5%", 7.06, 2.80, 1.52, BLUE)
    metric(slide, "C1  95.2%", 8.72, 2.80, 1.52, CORAL)
    metric(slide, "890 ratings", 11.14, 2.80, 1.22, MUTED, 10.5,
           PP_ALIGN.RIGHT)
    textbox(slide, "√(.665 × .952) = 79.6%", 7.06, 3.26, 2.94, 0.34,
            18.5, GREEN, True)
    textbox(slide, "CCA PICKS", 11.05, 3.29, 1.31, 0.28,
            13.5, GREEN, True, PP_ALIGN.RIGHT)
    line(slide, 7.04, 3.79, 12.42, 3.79, LIGHT, 0.9)
    textbox(slide, CCA_TEXT, 7.06, 4.05, 5.25, 1.10,
            11.7, INK, False)
    textbox(slide, "SOURCES  Euractiv · Reuters · Brookings · Expats.cz",
            7.06, 5.31, 4.74, 0.20, 8.7, BLUE, True)

    line(slide, 0.82, 5.91, 12.50, 5.91, LIGHT, 1.0)
    bullet(slide,
           "Cross-constituency selection favors the more neutral formulation",
           2.20, 6.22, 8.95, 15.5, INK, CORAL, True, PP_ALIGN.CENTER)
    source(slide, "Authors’ Representative selection · historical Gabriel output")


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    official_case(base_slide(presentation))
    presentation.save(path)


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V14 changed; refusing to overwrite manual edits. "
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
                    if info.filename == "ppt/slides/slide35.xml"
                    else source_zip.read(info.filename)
                )
                output_zip.writestr(info, payload)
        temporary.replace(OUTPUT)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        generated_path = Path(directory) / "official-case.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
