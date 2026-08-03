from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v15.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v16.pptx"
SOURCE_SHA256 = "ee2d833b14b7adbc6640230f8a7d3c006529a7f5cd2d3fa454fbaa91bc865e00"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return payload.replace(old, new, 1)


def reorder_case_first(presentation_xml: bytes) -> bytes:
    case_marker = b'<p:sldId id="290" r:id="rId42"/>'
    representative_marker = b'<p:sldId id="286" r:id="rId38"/>'
    presentation_xml = replace_once(
        presentation_xml, case_marker, b"", "case-study slide"
    )
    return replace_once(
        presentation_xml,
        representative_marker,
        case_marker + representative_marker,
        "Representative-results insertion point",
    )


def update_model_strip(slide_xml: bytes) -> bytes:
    replacements = [
        (b"<a:t>MiMo v2.5 Pro rerun</a:t>",
         b"<a:t>RERUNS IN PROGRESS</a:t>", "rerun heading"),
        (b"<a:t>higher reasoning capacity</a:t>",
         b"<a:t>MiMo v2.5 Pro</a:t>", "MiMo label"),
        (b"<a:t>accuracy expected to improve</a:t>",
         "<a:t>Gemma 4 · Qwen 3.5</a:t>".encode("utf-8"), "Gemma/Qwen label"),
        ("<a:t>• Historical Gabriel outputs · MiMo rerun underway</a:t>".encode("utf-8"),
         "<a:t>• Historical Gabriel outputs · three reruns underway</a:t>".encode("utf-8"),
         "source line"),
    ]
    for old, new, label in replacements:
        slide_xml = replace_once(slide_xml, old, new, label)
    return slide_xml


def build() -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V15 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        replacements = {
            "ppt/presentation.xml": reorder_case_first(
                source_zip.read("ppt/presentation.xml")
            ),
            "ppt/slides/slide33.xml": update_model_strip(
                source_zip.read("ppt/slides/slide33.xml")
            ),
        }

        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                output_zip.writestr(
                    info, replacements.get(info.filename, source_zip.read(info.filename))
                )
        temporary.replace(OUTPUT)


def main() -> None:
    build()
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
