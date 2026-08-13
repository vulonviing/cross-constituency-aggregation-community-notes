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
SOURCE = HERE / "community-notes-final-presentation-v7.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v8.pptx"
SOURCE_SHA256 = "f43c22fb0454667a4751c26e94677410a4e9dcf53ad982e5c05d2a318586d5ea"
GOLD = "D79A24"

NEW_SLIDES = {
    "ppt/slides/slide28.xml": "ppt/slides/slide2.xml",
    "ppt/slides/slide29.xml": "ppt/slides/slide3.xml",
    "ppt/slides/slide30.xml": "ppt/slides/slide4.xml",
}
NEW_RELS = {
    "ppt/slides/_rels/slide28.xml.rels",
    "ppt/slides/_rels/slide29.xml.rels",
    "ppt/slides/_rels/slide30.xml.rels",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_mark(slide, x: float, y: float, diameter: float = 0.24) -> None:
    circle(slide, x, y, diameter, GREEN)
    line(slide, x + 0.05, y + 0.13, x + 0.10, y + 0.18, WHITE, 1.2)
    line(slide, x + 0.10, y + 0.18, x + 0.20, y + 0.06, WHITE, 1.2)


def cross_mark(slide, x: float, y: float, diameter: float = 0.24) -> None:
    circle(slide, x, y, diameter, CORAL)
    line(slide, x + 0.06, y + 0.06, x + 0.18, y + 0.18, WHITE, 1.2)
    line(slide, x + 0.18, y + 0.06, x + 0.06, y + 0.18, WHITE, 1.2)


def principle_rows(slide, reveal_count: int) -> None:
    xline = 1.42
    line(slide, xline, 1.82, xline, 5.78, LIGHT, 1.4)
    rows = [
        (1.92, "P1", "≥3 ratings", "from every group", BLUE),
        (3.00, "P2", "Geometric mean", "a soft veto", CORAL),
        (4.05, "P3", "Same rule", "no size weighting", GOLD),
        (5.12, "P4", "200k raters", "Method-B recovery", GREEN),
    ]
    for index, (y, label, head, sub, color) in enumerate(rows):
        if index >= reveal_count:
            continue
        circle(slide, xline - 0.09, y + 0.06, 0.18, color)
        textbox(slide, label, 1.86, y + 0.06, 0.65, 0.20, 11, color, True)
        textbox(slide, head, 2.53, y, 2.95, 0.28, 17, INK, True)
        bullet(slide, sub, 5.55, y + 0.03, 2.55, 13.5, MUTED, color)


def right_heading(slide, text: str) -> None:
    textbox(slide, text, 8.58, 1.76, 3.85, 0.22, 9.5, MUTED, True)


def example_presence(slide) -> None:
    right_heading(slide, "CHECK 1 · PRESENCE")
    textbox(slide, "SAME NOTE", 8.58, 2.18, 1.30, 0.20, 8.5, MUTED, True)

    textbox(slide, "CONSTITUENCY A", 8.58, 2.70, 1.70, 0.20, 9, BLUE, True)
    textbox(slide, "90 ratings", 10.35, 2.62, 1.20, 0.28, 17, INK, True)
    check_mark(slide, 11.92, 2.64, 0.26)

    line(slide, 8.58, 3.18, 12.36, 3.18, LIGHT, 0.8)

    textbox(slide, "CONSTITUENCY B", 8.58, 3.55, 1.70, 0.20, 9, CORAL, True)
    textbox(slide, "2 ratings", 10.35, 3.47, 1.20, 0.28, 17, INK, True)
    cross_mark(slide, 11.92, 3.49, 0.26)

    textbox(slide, "NO SCORE YET", 8.58, 4.30, 3.82, 0.46,
            26, CORAL, True, PP_ALIGN.CENTER)
    bullet(slide, "≥3 from every group", 9.12, 5.02, 2.75,
           14, MUTED, CORAL, True, PP_ALIGN.CENTER)


def example_non_compensation(slide) -> None:
    right_heading(slide, "CHECK 2 · NON-COMPENSATION")
    textbox(slide, "A · 81 / 90 = 90%", 8.58, 2.15, 1.75, 0.24,
            11.5, BLUE, True)
    textbox(slide, "B · 1 / 10 = 10%", 10.62, 2.15, 1.75, 0.24,
            11.5, CORAL, True, PP_ALIGN.RIGHT)

    textbox(slide, "POOLED VOTES", 8.58, 2.70, 1.55, 0.20, 8.5, MUTED, True)
    textbox(slide, "(81 + 1) / (90 + 10) = 82%", 8.58, 3.02, 3.75, 0.34,
            16.5, INK, True)
    textbox(slide, "PASS", 11.42, 3.42, 0.90, 0.27,
            14, GREEN, True, PP_ALIGN.RIGHT)

    line(slide, 8.58, 3.82, 12.36, 3.82, LIGHT, 0.8)

    textbox(slide, "CCA", 8.58, 4.15, 0.90, 0.20, 8.5, GREEN, True)
    textbox(slide, "√(.90 × .10) = 30%", 8.58, 4.45, 3.75, 0.36,
            19, INK, True)
    textbox(slide, "DOES NOT PASS", 10.40, 4.93, 1.92, 0.27,
            13.5, CORAL, True, PP_ALIGN.RIGHT)
    bullet(slide, "Enthusiasm cannot erase rejection", 8.58, 5.32, 3.65,
           12.5, MUTED, CORAL)


def dot_row(slide, x: float, y: float, count: int, color: str) -> None:
    for index in range(count):
        circle(slide, x + index * 0.20, y, 0.105, color)


def example_symmetry(slide) -> None:
    right_heading(slide, "CHECK 3 · SYMMETRY")

    textbox(slide, "90 RATERS", 8.58, 2.22, 1.10, 0.20, 8.5, BLUE, True)
    dot_row(slide, 8.58, 2.60, 9, BLUE)
    textbox(slide, "10 RATERS", 10.84, 2.22, 1.10, 0.20, 8.5, CORAL, True)
    dot_row(slide, 10.84, 2.60, 1, CORAL)

    textbox(slide, "90 raters  ≠  9× weight", 8.58, 3.15, 3.78, 0.34,
            18, INK, True, PP_ALIGN.CENTER)
    line(slide, 8.58, 3.72, 12.36, 3.72, LIGHT, 0.8)

    textbox(slide, "√(sA × sB)  =  √(sB × sA)", 8.58, 4.08, 3.78, 0.34,
            16.5, GOLD, True, PP_ALIGN.CENTER)
    textbox(slide, "√(.90 × .10) = √(.10 × .90) = 30%", 8.58, 4.62,
            3.78, 0.34, 14.5, INK, True, PP_ALIGN.CENTER)
    bullet(slide, "Group size does not change the rule", 8.72, 5.28, 3.52,
           12.5, MUTED, GOLD, True, PP_ALIGN.CENTER)


def example_recovery(slide) -> None:
    right_heading(slide, "CHECK 4 · BEHAVIORAL RECOVERY")

    # Active raters.
    for row in range(4):
        for col in range(5):
            circle(slide, 8.62 + col * 0.23, 2.32 + row * 0.28, 0.09, MUTED)
    textbox(slide, "200k RATERS", 8.58, 3.58, 1.25, 0.20, 8.5, MUTED, True)

    textbox(slide, "→", 9.88, 2.73, 0.36, 0.30, 19, MUTED, True, PP_ALIGN.CENTER)

    # Co-rating graph.
    graph_points = [(10.34, 2.35), (10.75, 2.24), (11.03, 2.62),
                    (10.48, 2.92), (10.88, 3.10), (11.25, 2.94)]
    for a, b in [(0, 1), (0, 3), (1, 2), (1, 3), (2, 4), (3, 4), (4, 5)]:
        x1, y1 = graph_points[a]; x2, y2 = graph_points[b]
        line(slide, x1 + 0.05, y1 + 0.05, x2 + 0.05, y2 + 0.05, LIGHT, 0.8)
    for x, y in graph_points:
        circle(slide, x, y, 0.11, MUTED)
    textbox(slide, "CO-RATING", 10.33, 3.58, 1.10, 0.20, 8.5, MUTED, True)

    textbox(slide, "→", 11.43, 2.73, 0.36, 0.30, 19, MUTED, True, PP_ALIGN.CENTER)

    # Recovered constituencies.
    for x, y in [(11.93, 2.35), (12.15, 2.58), (11.88, 2.84)]:
        circle(slide, x, y, 0.13, BLUE)
    for x, y in [(12.30, 3.03), (12.06, 3.23), (12.35, 3.42)]:
        circle(slide, x, y, 0.13, CORAL)
    textbox(slide, "A / B", 11.88, 3.72, 0.60, 0.20, 9, GREEN, True, PP_ALIGN.CENTER)

    textbox(slide, "METHOD B", 8.58, 4.35, 3.78, 0.28,
            15.5, GREEN, True, PP_ALIGN.CENTER)
    bullet(slide, "No party · country · ideology labels", 8.62, 4.95, 3.70,
           13, MUTED, GREEN, True, PP_ALIGN.CENTER)


def build_principle_slide(slide, reveal_count: int) -> None:
    title(slide, "IMPLEMENTATION", "Principles become operations", "11")
    principle_rows(slide, reveal_count)
    [example_presence, example_non_compensation, example_symmetry, example_recovery][
        reveal_count - 1
    ](slide)
    if reveal_count < 4:
        source(slide, "Toy illustration—not the Community Notes scoring formula; authors’ CCA design")
    else:
        source(slide, "Authors’ 200k Representative pipeline")


def build_four_slides(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    for reveal_count in range(1, 5):
        slide = base_slide(presentation)
        build_principle_slide(slide, reveal_count)
    presentation.save(path)


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def assemble_v8(generated_pptx: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "Source V7 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(generated_pptx, "r") as generated:
        generated_xml = {
            index: generated.read(f"ppt/slides/slide{index}.xml")
            for index in range(1, 5)
        }

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        base_rels = source_zip.read("ppt/slides/_rels/slide25.xml.rels")
        replacements: dict[str, bytes] = {
            "ppt/slides/slide25.xml": generated_xml[1],
        }

        presentation_xml = source_zip.read("ppt/presentation.xml")
        presentation_xml = replace_once(
            presentation_xml,
            b'<p:sldId id="280" r:id="rId32"/>',
            (
                b'<p:sldId id="280" r:id="rId32"/>'
                b'<p:sldId id="283" r:id="rId35"/>'
                b'<p:sldId id="284" r:id="rId36"/>'
                b'<p:sldId id="285" r:id="rId37"/>'
            ),
            "principle reveal order",
        )
        replacements["ppt/presentation.xml"] = presentation_xml

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationships = b"".join(
            (
                f'<Relationship Id="rId{rel_id}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                f'Target="slides/slide{slide_id}.xml"/>'
            ).encode()
            for rel_id, slide_id in [(35, 28), (36, 29), (37, 30)]
        )
        presentation_rels = replace_once(
            presentation_rels,
            b"</Relationships>",
            relationships + b"</Relationships>",
            "presentation relationships",
        )
        replacements["ppt/_rels/presentation.xml.rels"] = presentation_rels

        content_types = source_zip.read("[Content_Types].xml")
        overrides = b"".join(
            (
                f'<Override PartName="/ppt/slides/slide{slide_id}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            ).encode()
            for slide_id in (28, 29, 30)
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
            for target, generated_name in NEW_SLIDES.items():
                generated_index = int(generated_name.removeprefix("ppt/slides/slide").removesuffix(".xml"))
                output_zip.writestr(target, generated_xml[generated_index])
            for rel_name in NEW_RELS:
                output_zip.writestr(rel_name, base_rels)
        temporary.replace(OUTPUT)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        generated = Path(tmpdir) / "principle-reveals.pptx"
        build_four_slides(generated)
        assemble_v8(generated)
    print(f"Source V7 preserved: {sha256(SOURCE)}")
    print(f"Saved V8: {OUTPUT}")
    print(f"V8 SHA256: {sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
