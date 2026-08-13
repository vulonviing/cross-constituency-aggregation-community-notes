from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from build_gemma_method_v20 import validate_case_score


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "community-notes-final-presentation-v22.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v23.pptx"
SOURCE_SHA256 = "16cbe5cbb8103d497ee188d473ba69696257940df2515011a3004207d0d20b38"
TARGET_SLIDE = "ppt/slides/slide35.xml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_case_label(payload: bytes) -> bytes:
    old = "<a:t>CHERRY-PICKED CASE · RUSSIA / UKRAINE</a:t>".encode("utf-8")
    new = "<a:t>CASE · RUSSIA / UKRAINE</a:t>".encode("utf-8")
    count = payload.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one cherry-picked case label, found {count}")
    return payload.replace(old, new, 1)


def build() -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V22 changed; refusing to overwrite manual edits. "
            f"Expected {SOURCE_SHA256}, got {actual_hash}."
        )

    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        replacement = update_case_label(source_zip.read(TARGET_SLIDE))
        temporary = OUTPUT.with_suffix(".tmp.pptx")
        if temporary.exists():
            temporary.unlink()
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                payload = replacement if info.filename == TARGET_SLIDE else source_zip.read(info.filename)
                output_zip.writestr(info, payload)
        temporary.replace(OUTPUT)


def main() -> None:
    validate_case_score()
    build()
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
