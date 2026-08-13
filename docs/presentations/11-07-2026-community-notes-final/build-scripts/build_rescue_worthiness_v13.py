from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

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
    W,
    H,
    base_slide,
    bullet,
    circle,
    line,
    outline_round_rect,
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v12.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v13.pptx"
SOURCE_SHA256 = "78e8211f04f042faf6d87b6f289785c37d1e7ee535f7d94cc862344872540d92"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def criterion(slide, y: float, text: str) -> None:
    circle(slide, 4.08, y + 0.02, 0.17, GREEN)
    textbox(slide, text, 4.42, y, 3.62, 0.28, 13.2, INK, True)


def score_band(slide, y: float, score: str, label: str, color: str) -> None:
    textbox(slide, score, 9.30, y, 0.78, 0.24, 10.5, color, True,
            PP_ALIGN.RIGHT)
    textbox(slide, label, 10.25, y, 1.72, 0.24, 10.5, MUTED, True)


def rescue_worthiness(slide) -> None:
    title(slide, "VALIDATION · STAGE 2", "What makes a note worth rescuing?", "13")

    # The model receives only the visible note text and its visible source pointer.
    textbox(slide, "MODEL SEES", 0.84, 1.68, 1.60, 0.22, 10, MUTED, True)
    outline_round_rect(slide, 0.92, 2.05, 2.18, 2.42, INK, 1.15)
    line(slide, 1.20, 2.55, 2.80, 2.55, INK, 1.2)
    line(slide, 1.20, 2.94, 2.58, 2.94, INK, 1.2)
    line(slide, 1.20, 3.33, 2.72, 3.33, INK, 1.2)
    line(slide, 1.20, 3.86, 2.44, 3.86, BLUE, 1.8)
    textbox(slide, "SOURCE POINTER", 1.20, 4.02, 1.28, 0.18,
            8.2, BLUE, True)
    bullet(slide, "note text", 1.03, 4.78, 1.52, 12.5, MUTED, INK, True)
    bullet(slide, "visible source pointer", 1.03, 5.19, 2.02,
           12.5, MUTED, BLUE, True)
    textbox(slide, "→", 3.34, 3.19, 0.38, 0.34, 20, MUTED, True,
            PP_ALIGN.CENTER)

    # Five prompt-exact dimensions form one holistic judgment.
    textbox(slide, "HOLISTIC JUDGMENT", 4.02, 1.68, 2.30, 0.22,
            10, MUTED, True)
    line(slide, 4.165, 2.25, 4.165, 4.99, LIGHT, 1.2)
    criteria = [
        "specific + traceable source pointer",
        "clear claim ↔ source connection",
        "self-contained explanation",
        "factual + neutral wording",
        "concise + constructive presentation",
    ]
    for index, text in enumerate(criteria):
        criterion(slide, 2.17 + index * 0.67, text)

    textbox(slide, "→", 8.16, 3.19, 0.38, 0.34, 20, MUTED, True,
            PP_ALIGN.CENTER)

    # Prompt-defined bands plus the historical display threshold at 50.
    textbox(slide, "0–100 SCORE", 8.74, 1.68, 1.70, 0.22, 10, MUTED, True)
    line(slide, 9.02, 2.13, 9.02, 3.70, GREEN, 3.0)
    line(slide, 9.02, 3.70, 9.02, 5.24, LIGHT, 3.0)
    circle(slide, 8.91, 3.59, 0.22, CORAL)

    score_band(slide, 2.08, "90–100", "outstanding", GREEN)
    score_band(slide, 2.66, "70–89", "strong", GREEN)
    score_band(slide, 3.23, "40–69", "mixed", MUTED)
    score_band(slide, 4.34, "10–39", "weak", CORAL)
    score_band(slide, 4.92, "0–9", "minimal", CORAL)

    line(slide, 8.88, 3.70, 12.20, 3.70, CORAL, 1.2)
    textbox(slide, "50", 8.53, 3.57, 0.28, 0.24, 10.5, CORAL, True,
            PP_ALIGN.RIGHT)
    textbox(slide, "≥50  VALIDATED", 10.02, 3.82, 1.88, 0.25,
            13.5, GREEN, True, PP_ALIGN.CENTER)

    line(slide, 0.82, 5.76, 12.50, 5.76, LIGHT, 1.0)
    bullet(slide,
           "No URL opening · No original post · Visible note quality only",
           2.42, 6.10, 8.55, 15.5, INK, CORAL, True, PP_ALIGN.CENTER)
    source(slide, "Gabriel Stage-2 prompt · historical threshold ≥50")


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    rescue_worthiness(base_slide(presentation))
    presentation.save(path)


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "The manually edited V12 changed; refusing to overwrite it. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(generated_path, "r") as generated_zip:
        new_slide = generated_zip.read("ppt/slides/slide1.xml")
        new_rels = generated_zip.read("ppt/slides/_rels/slide1.xml.rels")

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        replacements: dict[str, bytes] = {}

        presentation_xml = source_zip.read("ppt/presentation.xml")
        replacements["ppt/presentation.xml"] = replace_once(
            presentation_xml,
            b'<p:sldId id="288" r:id="rId40"/>',
            b'<p:sldId id="288" r:id="rId40"/><p:sldId id="289" r:id="rId41"/>',
            "final slide marker",
        )

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationship = (
            b'<Relationship Id="rId41" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide34.xml"/>'
        )
        replacements["ppt/_rels/presentation.xml.rels"] = replace_once(
            presentation_rels,
            b"</Relationships>",
            relationship + b"</Relationships>",
            "presentation relationship",
        )

        content_types = source_zip.read("[Content_Types].xml")
        override = (
            b'<Override PartName="/ppt/slides/slide34.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        replacements["[Content_Types].xml"] = replace_once(
            content_types,
            b"</Types>",
            override + b"</Types>",
            "content type",
        )

        additions = {
            "ppt/slides/slide34.xml": new_slide,
            "ppt/slides/_rels/slide34.xml.rels": new_rels,
        }

        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                output_zip.writestr(
                    info, replacements.get(info.filename, source_zip.read(info.filename))
                )
            for name, payload in additions.items():
                output_zip.writestr(name, payload)
        temporary.replace(OUTPUT)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        generated_path = Path(directory) / "rescue-worthiness.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
