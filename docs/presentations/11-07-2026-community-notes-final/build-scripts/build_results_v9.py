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
    WHITE,
    W,
    H,
    base_slide,
    bullet,
    circle,
    line,
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v8.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v9.pptx"
SOURCE_SHA256 = "12d197ce22f71a9727daa524f81fccd41f117a2ae19dd2f71ea2172515cba94e"
GOLD = "D79A24"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wip(slide) -> None:
    textbox(slide, "WORK IN PROGRESS", 10.42, 0.47, 1.45, 0.19,
            8.8, CORAL, True, PP_ALIGN.RIGHT)
    line(slide, 10.66, 0.72, 11.86, 0.72, CORAL, 1.0)


def result_node(slide, x: float, y: float, number: str, label: str, color: str,
                width: float = 2.20) -> None:
    textbox(slide, number, x, y, width, 0.52, 29, color, True, PP_ALIGN.CENTER)
    bullet(slide, label, x, y + 0.68, width, 12.5, MUTED, color, True,
           PP_ALIGN.CENTER)


def slide_representative(slide) -> None:
    title(slide, "RESULTS · REPRESENTATIVE", "What the platform shows—and hides", "12")

    result_node(slide, 0.82, 2.52, "44,722", "Representative picks", INK, 2.35)
    line(slide, 3.22, 3.02, 4.05, 3.02, LIGHT, 1.5)
    textbox(slide, "→", 3.46, 2.83, 0.35, 0.30, 19, MUTED, True, PP_ALIGN.CENTER)

    # Platform outcome split.
    line(slide, 4.14, 3.02, 4.74, 2.40, BLUE, 1.2)
    line(slide, 4.14, 3.02, 4.74, 4.18, CORAL, 1.2)
    result_node(slide, 4.78, 1.78, "6,832", "shown · 15%", BLUE, 2.10)
    result_node(slide, 4.78, 3.72, "37,890", "not shown · 85%", CORAL, 2.10)

    # CCA searches within the hidden pool.
    line(slide, 6.96, 4.30, 8.12, 4.30, LIGHT, 1.5)
    textbox(slide, "→", 7.35, 4.11, 0.35, 0.30, 19, MUTED, True, PP_ALIGN.CENTER)
    result_node(slide, 8.18, 3.72, "13,655", "CCA rescue candidates", GREEN, 2.65)

    textbox(slide, "INSIDE THE HIDDEN POOL", 8.36, 5.05, 2.30, 0.20,
            9, GREEN, True, PP_ALIGN.CENTER)
    line(slide, 0.82, 5.73, 12.50, 5.73, LIGHT, 1.0)
    bullet(slide, "CCA searches inside the hidden Representative pool",
           3.10, 6.06, 7.05, 16.5, INK, GREEN, True, PP_ALIGN.CENTER)
    source(slide, "Authors’ 200k Representative pipeline")


def stage_label(slide, text: str, x: float, y: float, color: str) -> None:
    circle(slide, x, y + 0.01, 0.22, color)
    textbox(slide, text, x + 0.34, y, 1.55, 0.22, 10, color, True)


def slide_validation(slide) -> None:
    title(slide, "VALIDATION", "Gabriel Validation", "12")
    wip(slide)
    line(slide, 6.66, 1.75, 6.66, 5.66, LIGHT, 1.0)

    # Stage 1.
    stage_label(slide, "STAGE 1", 0.90, 1.78, BLUE)
    textbox(slide, "Nature + sourcing", 0.90, 2.18, 3.60, 0.32,
            19, INK, True)
    textbox(slide, "PASS", 0.92, 2.82, 0.60, 0.20, 8.5, GREEN, True)
    bullet(slide, "sourced factual information", 1.55, 2.77, 3.70,
           13, INK, GREEN, True)

    textbox(slide, "STOP", 0.92, 3.30, 0.60, 0.20, 8.5, CORAL, True)
    for index, text in enumerate([
        "unsourced context / claim",
        "opinion / speculation",
        "hostile / derogatory",
        "irrelevant / spam",
    ]):
        bullet(slide, text, 1.55, 3.22 + index * 0.42, 3.72,
               11.5, MUTED, CORAL)

    textbox(slide, "VISIBLE EXTERNAL SOURCE POINTER REQUIRED",
            0.92, 5.08, 4.95, 0.24, 10.5, BLUE, True)

    # Stage 2.
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
    bullet(slide, "Missing sourcing is a validation failure—not proof that the claim is false",
           1.50, 6.20, 10.35, 14.5, INK, CORAL, True, PP_ALIGN.CENTER)
    source(slide, "Historical Gabriel method · model-based validation")


def funnel_step(slide, x: float, number: str, label: str, color: str) -> None:
    circle(slide, x + 0.72, 3.04, 0.20, color)
    textbox(slide, number, x, 2.12, 1.65, 0.50, 28, color, True, PP_ALIGN.CENTER)
    bullet(slide, label, x - 0.18, 3.55, 2.05, 12, MUTED, color, True,
           PP_ALIGN.CENTER)


def slide_historical(slide) -> None:
    title(slide, "RESULTS · VALIDATION", "From candidates to validated rescues", "12")
    wip(slide)

    line(slide, 1.56, 3.14, 11.82, 3.14, LIGHT, 1.8)
    funnel_step(slide, 0.82, "13,655", "CCA candidates", INK)
    textbox(slide, "→", 3.58, 2.92, 0.36, 0.30, 18, MUTED, True, PP_ALIGN.CENTER)
    funnel_step(slide, 4.08, "8,051", "Stage 1 pass", BLUE)
    textbox(slide, "→", 6.82, 2.92, 0.36, 0.30, 18, MUTED, True, PP_ALIGN.CENTER)
    funnel_step(slide, 7.34, "3,896", "Stage 2 pass · ≥50", GREEN)

    # Stop paths.
    line(slide, 5.00, 3.24, 5.00, 4.42, CORAL, 1.0)
    textbox(slide, "5,604 STOP", 4.06, 4.48, 1.90, 0.26,
            13.5, CORAL, True, PP_ALIGN.CENTER)
    textbox(slide, "• 474 unsourced context / claim", 3.82, 4.90, 2.40, 0.22,
            10.2, MUTED, False, PP_ALIGN.CENTER)

    line(slide, 8.24, 3.24, 8.24, 4.42, CORAL, 1.0)
    textbox(slide, "4,155 BELOW 50", 7.22, 4.48, 2.05, 0.26,
            13.5, CORAL, True, PP_ALIGN.CENTER)

    # WIP model strip.
    line(slide, 0.82, 5.42, 12.50, 5.42, LIGHT, 1.0)
    textbox(slide, "GPT-4o-mini baseline", 0.94, 5.70, 2.30, 0.24,
            11.5, MUTED, True)
    textbox(slide, "→", 3.23, 5.68, 0.36, 0.26, 16, MUTED, True, PP_ALIGN.CENTER)
    textbox(slide, "MiMo v2.5 Pro rerun", 3.70, 5.70, 2.45, 0.24,
            11.5, BLUE, True)
    bullet(slide, "higher reasoning capacity", 6.55, 5.68, 2.55,
           11.5, MUTED, BLUE)
    bullet(slide, "accuracy expected to improve", 9.30, 5.68, 2.82,
           11.5, MUTED, GREEN)
    textbox(slide, "FINAL COUNTS WILL CHANGE", 4.50, 6.30, 4.35, 0.25,
            12, CORAL, True, PP_ALIGN.CENTER)
    source(slide, "Historical Gabriel outputs · MiMo rerun underway")


def build_three_slides(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    for builder in (slide_representative, slide_validation, slide_historical):
        slide = base_slide(presentation)
        builder(slide)
    presentation.save(path)


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def assemble_v9(generated_pptx: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "Source V8 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(generated_pptx, "r") as generated:
        slide_xml = {
            index: generated.read(f"ppt/slides/slide{index}.xml")
            for index in range(1, 4)
        }

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        base_rels = source_zip.read("ppt/slides/_rels/slide29.xml.rels")
        replacements: dict[str, bytes] = {
            "ppt/slides/slide29.xml": slide_xml[1],
        }

        presentation_xml = source_zip.read("ppt/presentation.xml")
        presentation_xml = replace_once(
            presentation_xml,
            b'<p:sldId id="284" r:id="rId36"/>',
            (
                b'<p:sldId id="284" r:id="rId36"/>'
                b'<p:sldId id="285" r:id="rId37"/>'
                b'<p:sldId id="286" r:id="rId38"/>'
            ),
            "results slide order",
        )
        replacements["ppt/presentation.xml"] = presentation_xml

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationships = (
            b'<Relationship Id="rId37" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide30.xml"/>'
            b'<Relationship Id="rId38" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide31.xml"/>'
        )
        presentation_rels = replace_once(
            presentation_rels,
            b"</Relationships>",
            relationships + b"</Relationships>",
            "presentation relationships",
        )
        replacements["ppt/_rels/presentation.xml.rels"] = presentation_rels

        content_types = source_zip.read("[Content_Types].xml")
        overrides = (
            b'<Override PartName="/ppt/slides/slide30.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            b'<Override PartName="/ppt/slides/slide31.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        content_types = replace_once(
            content_types,
            b"</Types>",
            overrides + b"</Types>",
            "content types",
        )
        replacements["[Content_Types].xml"] = content_types

        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                output_zip.writestr(
                    info,
                    replacements.get(info.filename, source_zip.read(info.filename)),
                )
            output_zip.writestr("ppt/slides/slide30.xml", slide_xml[2])
            output_zip.writestr("ppt/slides/slide31.xml", slide_xml[3])
            output_zip.writestr("ppt/slides/_rels/slide30.xml.rels", base_rels)
            output_zip.writestr("ppt/slides/_rels/slide31.xml.rels", base_rels)
        temporary.replace(OUTPUT)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        generated = Path(tmpdir) / "results-slides.pptx"
        build_three_slides(generated)
        assemble_v9(generated)
    print(f"Source V8 preserved: {sha256(SOURCE)}")
    print(f"Saved V9: {OUTPUT}")
    print(f"V9 SHA256: {sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
