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
    line,
    source,
    textbox,
    title,
)


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v13.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v14.pptx"
SOURCE_SHA256 = "82a79f8d142e2522f8a913149070a61ee58354e027f1982fa125224d4990e5e7"

MAJORITY_NOTE_ID = "1971737848320758040"
CCA_NOTE_ID = "1971775923088244749"

MAJORITY_TEXT = (
    "NNN — While the individual pardons are 80 in total, this does not include "
    "Categorical pardons. Factoring in Categorical pardons issued by the Biden "
    "administration, the total number of pardons are the number reported in OP’s image."
)
CCA_TEXT = (
    "The table mislabels clemency actions as “pardons.” Biden issued ~80 pardons and "
    "4,165 commutations (total: 4,245), not 8,064 pardons. Bush: 189 pardons/11 "
    "commutations. Obama: 212/1,715. Trump: 143/94."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metric(slide, text: str, x: float, y: float, width: float, color: str,
           size: float = 13.0, align=PP_ALIGN.LEFT) -> None:
    textbox(slide, text, x, y, width, 0.28, size, color, True, align)


def cherry_pick(slide) -> None:
    title(slide, "CHERRY-PICKED CASE · BIDEN CLEMENCY",
          "The winner changes with the rule", "13")
    line(slide, 6.67, 1.70, 6.67, 5.74, LIGHT, 1.0)

    # Left: the globally popular note selected by simple majority.
    textbox(slide, "SIMPLE MAJORITY PICK", 0.88, 1.66, 2.75, 0.23,
            10.5, CORAL, True)
    textbox(slide, f"NOTE {MAJORITY_NOTE_ID}", 3.55, 1.67, 2.36, 0.20,
            8.2, MUTED, True, PP_ALIGN.RIGHT)
    textbox(slide, "77.6%", 0.90, 2.05, 1.65, 0.50,
            28, INK, True)
    textbox(slide, "overall approval", 2.40, 2.24, 1.65, 0.23,
            11.5, MUTED, True)
    metric(slide, "C0  93.8%", 0.92, 2.80, 1.52, BLUE)
    metric(slide, "C1  4.0%", 2.58, 2.80, 1.45, CORAL)
    metric(slide, "277 ratings", 4.52, 2.80, 1.22, MUTED, 10.5, PP_ALIGN.RIGHT)
    textbox(slide, "√(.938 × .040) = 19.4%", 0.92, 3.26, 2.78, 0.34,
            18.5, CORAL, True)
    textbox(slide, "BRIDGE FAIL", 4.18, 3.29, 1.55, 0.28,
            13.5, CORAL, True, PP_ALIGN.RIGHT)
    line(slide, 0.90, 3.79, 5.78, 3.79, LIGHT, 0.9)
    textbox(slide, MAJORITY_TEXT, 0.92, 4.05, 4.98, 1.10,
            11.7, INK, False)
    textbox(slide, "SOURCES  Biden White House · DOJ", 0.92, 5.31, 3.80, 0.20,
            8.7, BLUE, True)

    # Right: lower global approval, but enough cross-constituency support to pass.
    textbox(slide, "CCA / REPRESENTATIVE PICK", 7.02, 1.66, 3.18, 0.23,
            10.5, GREEN, True)
    textbox(slide, f"NOTE {CCA_NOTE_ID}", 10.36, 1.67, 2.06, 0.20,
            8.2, MUTED, True, PP_ALIGN.RIGHT)
    textbox(slide, "57.9%", 7.04, 2.05, 1.65, 0.50,
            28, INK, True)
    textbox(slide, "overall approval", 8.54, 2.24, 1.65, 0.23,
            11.5, MUTED, True)
    textbox(slide, "GABRIEL  82/100", 10.52, 2.19, 1.90, 0.25,
            12.5, GREEN, True, PP_ALIGN.RIGHT)
    metric(slide, "C0  27.7%", 7.06, 2.80, 1.52, BLUE)
    metric(slide, "C1  98.5%", 8.72, 2.80, 1.52, CORAL)
    metric(slide, "461 ratings", 11.14, 2.80, 1.22, MUTED, 10.5, PP_ALIGN.RIGHT)
    textbox(slide, "√(.277 × .985) = 52.2%", 7.06, 3.26, 2.92, 0.34,
            18.5, GREEN, True)
    textbox(slide, "BRIDGE PASS", 10.76, 3.29, 1.60, 0.28,
            13.5, GREEN, True, PP_ALIGN.RIGHT)
    line(slide, 7.04, 3.79, 12.42, 3.79, LIGHT, 0.9)
    textbox(slide, CCA_TEXT, 7.06, 4.05, 5.25, 1.10,
            11.7, INK, False)
    textbox(slide, "SOURCES  DOJ · Pew Research", 7.06, 5.31, 3.50, 0.20,
            8.7, BLUE, True)

    line(slide, 0.82, 5.91, 12.50, 5.91, LIGHT, 1.0)
    bullet(slide,
           "Higher overall approval can hide near-zero support in one constituency",
           2.12, 6.22, 9.15, 15.5, INK, CORAL, True, PP_ALIGN.CENTER)
    source(slide, "Authors’ Representative selection · historical Gabriel output")


def build_generated(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    cherry_pick(base_slide(presentation))
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
            "V13 changed; refusing to overwrite manual edits. "
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
            b'<p:sldId id="289" r:id="rId41"/>',
            b'<p:sldId id="290" r:id="rId42"/><p:sldId id="289" r:id="rId41"/>',
            "rubric slide insertion point",
        )

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationship = (
            b'<Relationship Id="rId42" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide35.xml"/>'
        )
        replacements["ppt/_rels/presentation.xml.rels"] = replace_once(
            presentation_rels,
            b"</Relationships>",
            relationship + b"</Relationships>",
            "presentation relationship",
        )

        content_types = source_zip.read("[Content_Types].xml")
        override = (
            b'<Override PartName="/ppt/slides/slide35.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        replacements["[Content_Types].xml"] = replace_once(
            content_types,
            b"</Types>",
            override + b"</Types>",
            "content type",
        )

        additions = {
            "ppt/slides/slide35.xml": new_slide,
            "ppt/slides/_rels/slide35.xml.rels": new_rels,
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
        generated_path = Path(directory) / "cherry-picked-case.pptx"
        build_generated(generated_path)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
