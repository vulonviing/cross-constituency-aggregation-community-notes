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
    helpful_mark,
    line,
    note,
    source,
    textbox,
    title,
    user,
)


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v6.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v7.pptx"
SOURCE_SHA256 = "301431a95de8579f30ade3e23ccf8c30b4f14dcd491fde7af1220593eece2721"

NEW_SLIDE_XML = "ppt/slides/slide23.xml"
NEW_SLIDE_RELS = "ppt/slides/_rels/slide23.xml.rels"
NEW_REL_ID = "rId30"
NEW_SLIDE_ID = "278"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def heading(slide, text: str, x: float, y: float, width: float) -> None:
    textbox(slide, text, x, y, width, 0.22, 9.5, MUTED, True)


def build_good_instinct(slide) -> None:
    heading(slide, "GOOD INSTINCT", 0.84, 1.72, 1.80)
    user(slide, 1.05, 2.45, 0.90, BLUE)
    user(slide, 3.20, 2.45, 0.90, CORAL)
    note(slide, 2.03, 2.20, 1.05, 1.42, INK)
    helpful_mark(slide, 1.72, 2.75)
    helpful_mark(slide, 3.00, 2.75)
    line(slide, 1.47, 2.86, 1.68, 2.86, BLUE, 1.3)
    line(slide, 1.96, 2.86, 2.02, 2.86, BLUE, 1.3)
    line(slide, 3.08, 2.86, 3.17, 2.86, CORAL, 1.3)
    textbox(slide, "ENEMIES SHAKE HANDS", 1.03, 4.02, 3.10, 0.25,
            11.5, GREEN, True, PP_ALIGN.CENTER)
    bullet(slide, "Cross-group agreement is valuable", 0.94, 4.72, 3.25,
           13.5, INK, GREEN, True)


def rating_mix(slide, x: float, y: float, blue_count: int, coral_count: int) -> None:
    total = blue_count + coral_count
    for index in range(total):
        color = BLUE if index < blue_count else CORAL
        circle(slide, x + index * 0.21, y, 0.105, color)


def build_balance_math(slide) -> None:
    heading(slide, "SELECTION BALANCE", 4.66, 1.72, 2.10)

    textbox(slide, "BALANCED", 4.72, 2.18, 1.10, 0.20, 8.5, MUTED, True)
    rating_mix(slide, 4.72, 2.56, 5, 5)
    textbox(slide, "πA = .50   πB = .50", 4.72, 2.92, 2.25, 0.24,
            11.5, INK, True)
    textbox(slide, "2(.50)(.50) = 50%", 4.72, 3.27, 2.75, 0.30,
            16, GREEN, True)

    textbox(slide, "OBSERVED", 4.72, 3.90, 1.10, 0.20, 8.5, MUTED, True)
    rating_mix(slide, 4.72, 4.28, 9, 1)
    textbox(slide, "πA = .90   πB = .10", 4.72, 4.64, 2.25, 0.24,
            11.5, INK, True)
    textbox(slide, "2(.90)(.10) = 18%", 4.72, 4.99, 2.75, 0.30,
            16, CORAL, True)

    textbox(slide, "50%  →  18%", 7.25, 3.44, 1.30, 0.42,
            22, INK, True, PP_ALIGN.CENTER)


def build_distortions(slide) -> None:
    heading(slide, "THEN IT GETS MESSIER", 8.96, 1.72, 2.60)

    textbox(slide, "PARTISAN", 9.00, 2.23, 1.15, 0.20, 9, CORAL, True)
    textbox(slide, "fᵤ · fₙ", 9.00, 2.62, 1.20, 0.36, 21, CORAL, True)
    textbox(slide, "changes the credit", 10.25, 2.70, 2.05, 0.24,
            12.5, INK, True)
    bullet(slide, "The same click is interpreted differently", 9.00, 3.12,
           3.15, 12.5, MUTED, CORAL)

    line(slide, 9.00, 3.64, 12.32, 3.64, LIGHT, 0.8)

    textbox(slide, "ACTIVITY", 9.00, 3.98, 1.15, 0.20, 9, BLUE, True)
    textbox(slide, "πg", 9.00, 4.34, 0.55, 0.36, 21, BLUE, True)
    textbox(slide, "follows ratings—not people", 9.55, 4.42, 2.72, 0.24,
            12.5, INK, True)
    bullet(slide, "Active users represent each side", 9.00, 4.86,
           3.10, 12.5, MUTED, BLUE)


def build_transition_slide(slide) -> None:
    title(
        slide,
        "BRIDGING, REFRAMED",
        "The handshake is right. The electorate is not.",
        "06",
    )
    line(slide, 4.38, 1.70, 4.38, 5.48, LIGHT, 1.0)
    line(slide, 8.76, 1.70, 8.76, 5.48, LIGHT, 1.0)

    build_good_instinct(slide)
    build_balance_math(slide)
    build_distortions(slide)

    line(slide, 0.82, 5.72, 12.50, 5.72, LIGHT, 1.0)
    bullet(slide, "Keep consent. Make representation explicit.", 3.22, 6.04,
           6.95, 17, INK, GREEN, True, PP_ALIGN.CENTER)
    source(
        slide,
        "Toy illustration—not the Community Notes scoring formula; Buterin (2023); Wojcik et al. (2022); Nudo et al. (2026)",
    )


def build_single_slide(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    slide = base_slide(presentation)
    build_transition_slide(slide)
    presentation.save(path)


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def assemble_v7(new_slide_pptx: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "Source V6 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(new_slide_pptx, "r") as generated:
        slide_xml = generated.read("ppt/slides/slide1.xml")

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        slide_rels = source_zip.read("ppt/slides/_rels/slide16.xml.rels")
        replacements: dict[str, bytes] = {}

        presentation_xml = source_zip.read("ppt/presentation.xml")
        presentation_xml = replace_once(
            presentation_xml,
            b'<p:sldId id="271" r:id="rId23"/>',
            b'<p:sldId id="278" r:id="rId30"/><p:sldId id="271" r:id="rId23"/>',
            "slide-order",
        )
        replacements["ppt/presentation.xml"] = presentation_xml

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationship = (
            b'<Relationship Id="rId30" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide23.xml"/>'
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
            b'<Override PartName="/ppt/slides/slide23.xml" '
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
            16: (b"<a:t>06</a:t>", b"<a:t>07</a:t>"),
            17: (b"<a:t>07</a:t>", b"<a:t>08</a:t>"),
            18: (b"<a:t>08</a:t>", b"<a:t>09</a:t>"),
            19: (b"<a:t>09</a:t>", b"<a:t>10</a:t>"),
            20: (b"<a:t>10</a:t>", b"<a:t>11</a:t>"),
            21: (b"<a:t>11</a:t>", b"<a:t>12</a:t>"),
            22: (b"<a:t>12</a:t>", b"<a:t>13</a:t>"),
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
        generated = Path(tmpdir) / "transition-slide.pptx"
        build_single_slide(generated)
        assemble_v7(generated)
    print(f"Source V6 preserved: {sha256(SOURCE)}")
    print(f"Saved V7: {OUTPUT}")
    print(f"V7 SHA256: {sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
