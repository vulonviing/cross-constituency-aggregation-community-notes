from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from build_two_problems_v4 import (
    GREEN,
    LIGHT,
    MUTED,
    H,
    W,
    base_slide,
    bullet,
    line,
    textbox,
)
from build_validation_results_v18 import validate_counts, validation_results


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v18.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v19.pptx"
SOURCE_SHA256 = "1b0136e178dfb9e9b356a4c6b5828ad9feae532b554654f61207b768f8a7bb2c"
TARGET_SLIDE = "ppt/slides/slide33.xml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validation_results_with_share(slide) -> None:
    validation_results(slide)

    # Summary ratio, visually separated so it reads as an interpretation of
    # the final node rather than a fourth funnel stage.
    line(slide, 9.42, 1.78, 9.42, 3.43, LIGHT, 1.0)
    textbox(slide, "62.7%", 9.78, 1.86, 2.25, 0.58,
            31, GREEN, True, PP_ALIGN.CENTER)
    bullet(
        slide,
        "of candidates validated by the LLM",
        9.62,
        2.68,
        2.58,
        11.2,
        MUTED,
        GREEN,
        True,
        PP_ALIGN.CENTER,
    )
    textbox(slide, "8,558 / 13,655", 9.82, 3.15, 2.15, 0.20,
            9.0, GREEN, True, PP_ALIGN.CENTER)


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    validation_results_with_share(base_slide(presentation))
    presentation.save(path)


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V18 changed; refusing to overwrite manual edits. "
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
        generated_path = Path(directory) / "validation-share.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
