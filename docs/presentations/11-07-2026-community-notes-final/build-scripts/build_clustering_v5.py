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
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v4.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v5.pptx"
SOURCE_SHA256 = "b89963f6c3cf61935cd9ec627c45b1d1130cfcb2fc5b33d14e222d9f38bd571b"

NEW_SLIDE_XML = "ppt/slides/slide14.xml"
NEW_SLIDE_RELS = "ppt/slides/_rels/slide14.xml.rels"
NEW_REL_ID = "rId21"
NEW_SLIDE_ID = "269"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def user_dot(slide, x: float, y: float, color: str = MUTED, diameter: float = 0.12):
    return circle(slide, x, y, diameter, color)


def matrix_mark(slide, mark: str, x: float, y: float, color: str):
    textbox(slide, mark, x, y, 0.24, 0.24, 12.5, color, True, PP_ALIGN.CENTER)


def build_matrix(slide) -> None:
    origin_x, origin_y = 0.94, 2.35
    cell_w, cell_h = 0.39, 0.43
    rows, cols = 6, 7

    # Minimal matrix scaffolding: blanks are intentionally left blank because
    # an absent rating is missing data, not agreement or disagreement.
    for col in range(cols + 1):
        x = origin_x + 0.40 + col * cell_w
        line(slide, x, origin_y, x, origin_y + rows * cell_h, LIGHT, 0.55)
    for row in range(rows + 1):
        y = origin_y + row * cell_h
        line(slide, origin_x + 0.40, y, origin_x + 0.40 + cols * cell_w, y, LIGHT, 0.55)

    patterns = [
        ["✓", "✓", "", "×", "", "✓", "×"],
        ["✓", "", "✓", "×", "", "✓", "×"],
        ["", "✓", "✓", "×", "×", "", "×"],
        ["×", "×", "", "✓", "", "×", "✓"],
        ["×", "", "×", "✓", "✓", "", "✓"],
        ["", "×", "×", "✓", "✓", "×", ""],
    ]
    for row, pattern in enumerate(patterns):
        y = origin_y + row * cell_h
        user_dot(slide, origin_x + 0.08, y + 0.15, MUTED, 0.12)
        for col, mark in enumerate(pattern):
            if not mark:
                continue
            color = GREEN if mark == "✓" else CORAL
            matrix_mark(
                slide,
                mark,
                origin_x + 0.47 + col * cell_w,
                y + 0.075,
                color,
            )

    textbox(slide, "USERS", 0.91, 5.08, 0.70, 0.18, 8.5, MUTED, True)
    textbox(slide, "NOTES", 2.19, 5.08, 0.70, 0.18, 8.5, MUTED, True)


def build_similarity_graph(slide) -> None:
    points = [
        (5.05, 2.62), (5.62, 2.35), (6.15, 2.70),
        (5.25, 3.28), (5.88, 3.18), (6.43, 3.48),
        (6.88, 3.75),
        (7.28, 3.16), (7.76, 2.68), (8.24, 2.93),
        (7.52, 3.80), (8.10, 3.62), (8.46, 4.10),
    ]
    edges = [
        (0, 1), (0, 3), (1, 2), (1, 4), (2, 4), (2, 5),
        (3, 4), (4, 5), (5, 6), (6, 7),
        (7, 8), (7, 9), (7, 10), (8, 9), (9, 11),
        (10, 11), (10, 12), (11, 12),
    ]
    for left, right in edges:
        x1, y1 = points[left]
        x2, y2 = points[right]
        bridge = (left, right) == (6, 7)
        line(slide, x1 + 0.07, y1 + 0.07, x2 + 0.07, y2 + 0.07,
             LIGHT if bridge else MUTED, 0.7 if bridge else 1.0)
    for x, y in points:
        user_dot(slide, x, y, MUTED, 0.14)


def build_constituencies(slide) -> None:
    blue_points = [
        (9.72, 2.55), (10.14, 2.34), (10.55, 2.62),
        (9.90, 3.06), (10.34, 3.12), (10.73, 3.00),
        (10.10, 3.54), (10.56, 3.55),
    ]
    coral_points = [
        (11.25, 3.45), (11.65, 3.24), (12.05, 3.52),
        (11.45, 3.94), (11.86, 4.02), (12.24, 3.92),
        (11.63, 4.42), (12.05, 4.43),
    ]
    for x, y in blue_points:
        user_dot(slide, x, y, BLUE, 0.15)
    for x, y in coral_points:
        user_dot(slide, x, y, CORAL, 0.15)
    textbox(slide, "CONSTITUENCY A", 9.48, 4.78, 1.65, 0.20,
            9, BLUE, True, PP_ALIGN.CENTER)
    textbox(slide, "CONSTITUENCY B", 11.00, 4.78, 1.65, 0.20,
            9, CORAL, True, PP_ALIGN.CENTER)


def build_clustering_slide(slide) -> None:
    title(slide, "OUR SHIFT · RECOVERY", "From ratings to constituencies", "06")

    bullet(slide, "Rate notes", 0.92, 1.76, 2.4, 14.5, INK, BLUE, True)
    bullet(slide, "Find matching patterns", 4.88, 1.76, 3.0, 14.5, INK, BLUE, True)
    bullet(slide, "Recover constituencies", 9.45, 1.76, 3.0, 14.5, INK, BLUE, True)

    build_matrix(slide)
    textbox(slide, "→", 4.05, 3.27, 0.42, 0.38, 24, MUTED, True, PP_ALIGN.CENTER)
    build_similarity_graph(slide)
    textbox(slide, "→", 8.83, 3.27, 0.42, 0.38, 24, MUTED, True, PP_ALIGN.CENTER)
    build_constituencies(slide)

    line(slide, 0.82, 5.74, 12.50, 5.74, LIGHT, 1.0)
    bullet(
        slide,
        "Similar co-rating patterns → same behavioral constituency",
        2.70,
        6.05,
        7.90,
        17,
        INK,
        GREEN,
        True,
        PP_ALIGN.CENTER,
    )
    source(slide, "Authors’ 100k-note / 200k-rater pipeline")


def build_single_slide(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    slide = base_slide(presentation)
    build_clustering_slide(slide)
    presentation.save(path)


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def assemble_v5(new_slide_pptx: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "Source V4 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(new_slide_pptx, "r") as generated:
        slide_xml = generated.read("ppt/slides/slide1.xml")

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        slide_rels = source_zip.read("ppt/slides/_rels/slide9.xml.rels")
        replacements: dict[str, bytes] = {}

        presentation_xml = source_zip.read("ppt/presentation.xml")
        presentation_xml = replace_once(
            presentation_xml,
            b'<p:sldId id="264" r:id="rId16"/>',
            b'<p:sldId id="269" r:id="rId21"/><p:sldId id="264" r:id="rId16"/>',
            "slide-order",
        )
        replacements["ppt/presentation.xml"] = presentation_xml

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationship = (
            b'<Relationship Id="rId21" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide14.xml"/>'
        )
        presentation_rels = replace_once(
            presentation_rels,
            b"</Relationships>",
            relationship + b"</Relationships>",
            "presentation relationship",
        )
        replacements["ppt/_rels/presentation.xml.rels"] = presentation_rels

        content_types = source_zip.read("[Content_Types].xml")
        override = (
            b'<Override PartName="/ppt/slides/slide14.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        content_types = replace_once(
            content_types,
            b"</Types>",
            override + b"</Types>",
            "content type",
        )
        replacements["[Content_Types].xml"] = content_types

        renumber = {
            9: (b"<a:t>06</a:t>", b"<a:t>07</a:t>"),
            10: (b"<a:t>07</a:t>", b"<a:t>08</a:t>"),
            11: (b"<a:t>08</a:t>", b"<a:t>09</a:t>"),
            12: (b"<a:t>09</a:t>", b"<a:t>10</a:t>"),
            13: (b"<a:t>10</a:t>", b"<a:t>11</a:t>"),
        }
        for number, (old, new) in renumber.items():
            name = f"ppt/slides/slide{number}.xml"
            replacements[name] = replace_once(
                source_zip.read(name), old, new, f"visible number on slide {number}"
            )

        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                output_zip.writestr(
                    info,
                    replacements.get(info.filename, source_zip.read(info.filename)),
                )
            output_zip.writestr(NEW_SLIDE_XML, slide_xml)
            output_zip.writestr(NEW_SLIDE_RELS, slide_rels)
        temporary.replace(OUTPUT)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        generated = Path(tmpdir) / "clustering-slide.pptx"
        build_single_slide(generated)
        assemble_v5(generated)
    print(f"Source V4 preserved: {sha256(SOURCE)}")
    print(f"Saved V5: {OUTPUT}")
    print(f"V5 SHA256: {sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
