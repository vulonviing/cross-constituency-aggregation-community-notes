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
SOURCE = HERE / "community-notes-final-presentation-v5.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v6.pptx"
SOURCE_SHA256 = "e340bd82bb55b6820bdd31442e446013a02ea4f2eb3f512bb3d2a27f0a6a708c"

NEW_SLIDE_XML = "ppt/slides/slide15.xml"
NEW_SLIDE_RELS = "ppt/slides/_rels/slide15.xml.rels"
NEW_REL_ID = "rId22"
NEW_SLIDE_ID = "270"
GOLD = "D79A24"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_mark(slide, x: float, y: float, diameter: float = 0.24) -> None:
    circle(slide, x, y, diameter, GREEN)
    line(slide, x + 0.05, y + 0.13, x + 0.10, y + 0.18, WHITE, 1.25)
    line(slide, x + 0.10, y + 0.18, x + 0.20, y + 0.06, WHITE, 1.25)


def labeled_group(slide, label: str, x: float, y: float, color: str) -> None:
    circle(slide, x, y, 0.27, color)
    textbox(slide, label, x, y + 0.055, 0.27, 0.16, 8.5, WHITE, True, PP_ALIGN.CENTER)


def dot_majority(slide, x: float, y: float, color: str) -> None:
    for index in range(7):
        row, col = divmod(index, 4)
        fill = color if index < 4 else LIGHT
        circle(slide, x + col * 0.34, y + row * 0.34, 0.14, fill)


def switzerland_example(slide) -> None:
    textbox(slide, "SWITZERLAND", 0.90, 1.82, 2.20, 0.24, 11, INK, True)
    textbox(slide, "PEOPLE", 0.96, 2.42, 0.85, 0.20, 8.5, MUTED, True)
    dot_majority(slide, 1.02, 2.80, BLUE)
    textbox(slide, "+", 2.58, 2.89, 0.30, 0.28, 18, MUTED, True, PP_ALIGN.CENTER)

    textbox(slide, "CANTONS", 0.96, 3.63, 0.85, 0.20, 8.5, MUTED, True)
    dot_majority(slide, 1.02, 4.01, CORAL)

    line(slide, 2.91, 3.01, 3.48, 3.34, BLUE, 1.2)
    line(slide, 2.91, 4.18, 3.48, 3.55, CORAL, 1.2)
    check_mark(slide, 3.55, 3.31, 0.32)
    bullet(slide, "Double majority", 0.96, 5.02, 2.25, 13.5, INK, GREEN, True)


def compact_example(
    slide,
    country: str,
    groups: list[tuple[str, str]],
    mechanism: str,
    y: float,
    outcome: str = "✓",
) -> None:
    textbox(slide, country, 5.10, y, 1.75, 0.22, 10.5, INK, True)
    start_x = 7.04
    for index, (label, color) in enumerate(groups):
        x = start_x + index * 0.54
        labeled_group(slide, label, x, y - 0.03, color)
        if index < len(groups) - 1:
            textbox(slide, "+", x + 0.31, y + 0.01, 0.20, 0.18,
                    11, MUTED, True, PP_ALIGN.CENTER)

    arrow_x = start_x + len(groups) * 0.54 + 0.02
    textbox(slide, "→", arrow_x, y - 0.02, 0.34, 0.23,
            16, MUTED, True, PP_ALIGN.CENTER)
    if outcome == "✓":
        check_mark(slide, arrow_x + 0.42, y - 0.03, 0.27)
    else:
        circle(slide, arrow_x + 0.42, y - 0.03, 0.27, GREEN)
        textbox(slide, outcome, arrow_x + 0.42, y + 0.045, 0.27, 0.14,
                7.3, WHITE, True, PP_ALIGN.CENTER)

    bullet(slide, mechanism, 10.20, y - 0.01, 2.10, 12.5, INK, GREEN, True)


def build_politics_slide(slide) -> None:
    title(slide, "COLLECTIVE DECISIONS", "This problem predates platforms", "06")
    line(slide, 4.55, 1.78, 4.55, 5.38, LIGHT, 1.0)

    switzerland_example(slide)
    compact_example(
        slide,
        "BELGIUM",
        [("NL", BLUE), ("FR", CORAL)],
        "Parallel majorities",
        2.24,
    )
    line(slide, 5.10, 2.93, 12.36, 2.93, LIGHT, 0.7)
    compact_example(
        slide,
        "BOSNIA",
        [("B", BLUE), ("C", GOLD), ("S", CORAL)],
        "Vital-interest veto",
        3.47,
        "VETO",
    )
    line(slide, 5.10, 4.16, 12.36, 4.16, LIGHT, 0.7)
    compact_example(
        slide,
        "N. IRELAND",
        [("U", BLUE), ("N", CORAL)],
        "Parallel consent",
        4.70,
    )

    line(slide, 0.82, 5.72, 12.50, 5.72, LIGHT, 1.0)
    bullet(slide, "No group decides alone", 0.92, 6.05, 3.45,
           16.5, INK, GREEN, True)
    bullet(slide, "But online, who are the groups? →", 7.32, 6.05, 4.70,
           16.5, INK, BLUE, True, PP_ALIGN.RIGHT)
    source(
        slide,
        "Linder & Mueller (2021); Lijphart (1977); Bieber (2006); McGarry & O’Leary (2009)",
    )


def build_single_slide(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    slide = base_slide(presentation)
    build_politics_slide(slide)
    presentation.save(path)


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def assemble_v6(new_slide_pptx: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "Source V5 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(new_slide_pptx, "r") as generated:
        slide_xml = generated.read("ppt/slides/slide1.xml")

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        slide_rels = source_zip.read("ppt/slides/_rels/slide14.xml.rels")
        replacements: dict[str, bytes] = {}

        presentation_xml = source_zip.read("ppt/presentation.xml")
        presentation_xml = replace_once(
            presentation_xml,
            b'<p:sldId id="269" r:id="rId21"/>',
            b'<p:sldId id="270" r:id="rId22"/><p:sldId id="269" r:id="rId21"/>',
            "slide-order",
        )
        replacements["ppt/presentation.xml"] = presentation_xml

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationship = (
            b'<Relationship Id="rId22" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide15.xml"/>'
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
            b'<Override PartName="/ppt/slides/slide15.xml" '
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
            14: (b"<a:t>06</a:t>", b"<a:t>07</a:t>"),
            9: (b"<a:t>07</a:t>", b"<a:t>08</a:t>"),
            10: (b"<a:t>08</a:t>", b"<a:t>09</a:t>"),
            11: (b"<a:t>09</a:t>", b"<a:t>10</a:t>"),
            12: (b"<a:t>10</a:t>", b"<a:t>11</a:t>"),
            13: (b"<a:t>11</a:t>", b"<a:t>12</a:t>"),
        }
        for number, (old, new) in renumber.items():
            name = f"ppt/slides/slide{number}.xml"
            replacements[name] = replace_once(
                source_zip.read(name), old, new, f"visible number on slide {number}"
            )

        consult_name = "ppt/slides/slide9.xml"
        consult_xml = replacements[consult_name]
        consult_xml = replace_once(
            consult_xml,
            "<a:t>• Switzerland · Belgium · Bosnia · Northern Ireland</a:t>".encode(),
            "<a:t>• Recover groups → consult each one → aggregate explicitly</a:t>".encode(),
            "consult-slide closing",
        )
        consult_xml = replace_once(
            consult_xml,
            b"<a:t>\xe2\x80\xa2 Linder &amp; Mueller (2021); Lijphart (1977); Bieber (2006); McGarry &amp; O\xe2\x80\x99Leary (2009)</a:t>",
            "<a:t>• Authors’ cross-constituency aggregation</a:t>".encode(),
            "consult-slide source",
        )
        replacements[consult_name] = consult_xml

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
        generated = Path(tmpdir) / "politics-slide.pptx"
        build_single_slide(generated)
        assemble_v6(generated)
    print(f"Source V5 preserved: {sha256(SOURCE)}")
    print(f"Saved V6: {OUTPUT}")
    print(f"V6 SHA256: {sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
