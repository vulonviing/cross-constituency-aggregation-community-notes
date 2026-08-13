from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from build_two_problems_v4 import BLUE, CORAL, GREEN, INK, MUTED, H, W, base_slide, bullet
from build_validation_results_v18 import validate_counts
from build_validation_share_v19 import validation_results_with_share


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v20.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v21.pptx"
SOURCE_SHA256 = "c7f7c15631e94ed99161a4e909356ff711c54c300d708a25e9ce5589c2d7ccf1"
TARGET_SLIDE = "ppt/slides/slide33.xml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validation_results_with_scoring(slide) -> None:
    validation_results_with_share(slide)

    old_rows = [
        shape
        for shape in slide.shapes
        if hasattr(shape, "text") and "rescue-worthiness < 50" in shape.text
    ]
    if len(old_rows) != 1:
        raise RuntimeError(f"Expected one old Stage 2 stop row, found {len(old_rows)}")
    old_row = old_rows[0]._element
    old_row.getparent().remove(old_row)

    bullet(slide, "0–100 holistic score", 5.12, 3.96, 2.70,
           10.6, MUTED, BLUE, True, PP_ALIGN.LEFT)
    bullet(slide, "≥50 → validated", 5.12, 4.28, 2.70,
           10.6, INK, GREEN, True, PP_ALIGN.LEFT)
    bullet(slide, "<50 → stopped", 5.12, 4.60, 2.70,
           10.6, MUTED, CORAL, True, PP_ALIGN.LEFT)


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    validation_results_with_scoring(base_slide(presentation))
    presentation.save(path)


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V20 changed; refusing to overwrite manual edits. "
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
        generated_path = Path(directory) / "validation-scoring.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
