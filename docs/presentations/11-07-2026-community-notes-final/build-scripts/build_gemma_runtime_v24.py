from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
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
ROOT = HERE.parents[2]
SOURCE = HERE / "community-notes-final-presentation-v23.pptx"
OUTPUT = HERE / "community-notes-final-presentation-v24.pptx"
SOURCE_SHA256 = "45631b9a9b6185873c7057a86957629e958b25c6cc16166f5a78e7b06efe227b"

MODEL = "google/gemma-4-31B-it"
REVISION = "518276fb130dc81caf9a4f772e65e63ef2526493"
RUN_ROOTS = (
    ROOT / "data/llm_validation/runs/gemma-4-31b-it-scckn-v1",
    ROOT / "data/llm_validation/runs/gemma-4-31b-it-scckn-stage1-5-opinion-v1",
    ROOT / "data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1",
)


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


def validate_contract() -> dict[str, object]:
    manifests = [json.loads((root / "run_manifest.json").read_text()) for root in RUN_ROOTS]
    for manifest in manifests:
        assert manifest["model"] == MODEL
        assert manifest["model_revision"] == REVISION
        assert manifest["model_variant"] == "bf16-thinking"
        assert manifest["thinking"] is True
        assert manifest["temperature"] == 0.2
        assert manifest["max_completion_tokens"] == 4096
        assert manifest["default_concurrency"] == 64
        assert manifest["max_attempts_total"] == 3
        assert manifest["retrieval"] is False
        assert manifest["system_prompt"] is None
        assert manifest["structured_output_constraint"] is False
        assert manifest["vllm_version"] == "0.25.0"

    worker = (ROOT / "jobs/llm_validation_gpu.sh").read_text()
    for argument in (
        "--tensor-parallel-size 2",
        "--dtype bfloat16",
        "--max-model-len 8192",
        "--gpu-memory-utilization 0.90",
        "--max-num-seqs 64",
        "--max-num-batched-tokens 32768",
        "--enable-prefix-caching",
        "--async-scheduling",
        "--language-model-only",
        "--reasoning-parser gemma4",
    ):
        assert argument in worker

    submit = (ROOT / "jobs/submit_llm_validation.sh").read_text()
    assert "-pe smp 8" in submit
    assert "gpu=2,tesla_l40=1,h_vmem=64G" in submit
    assert "module load cuda/13.2" in worker

    summaries = [json.loads((root / "summary.json").read_text()) for root in RUN_ROOTS]
    judgments = sum(summary["notes"] for summary in summaries)
    attempts = sum(sum(summary["attempt_status"].values()) for summary in summaries)
    prompt_tokens = sum(summary["prompt_tokens"] for summary in summaries)
    completion_tokens = sum(summary["completion_tokens"] for summary in summaries)
    first_attempt_valid = (
        sum(summary["notes"] * summary["first_attempt_valid_rate"] for summary in summaries)
        / judgments
    )

    stage_spans = []
    first = None
    last = None
    for root in RUN_ROOTS:
        calls = pd.read_parquet(root / "calls.parquet", columns=["created_at"])
        timestamps = pd.to_datetime(calls["created_at"], utc=True)
        stage_spans.append(timestamps.max() - timestamps.min())
        first = timestamps.min() if first is None else min(first, timestamps.min())
        last = timestamps.max() if last is None else max(last, timestamps.max())

    active_span = sum(stage_spans, pd.Timedelta(0))
    end_to_end = last - first

    assert judgments == 25734
    assert attempts == 25804
    assert prompt_tokens + completion_tokens == 32113128
    assert round(first_attempt_valid * 100, 2) == 99.75
    assert round(active_span.total_seconds() / 60) == 748
    assert round(end_to_end.total_seconds() / 60) == 951

    return {
        "judgments": judgments,
        "attempts": attempts,
        "tokens": prompt_tokens + completion_tokens,
        "first_attempt_valid": first_attempt_valid,
        "active_span": active_span,
        "end_to_end": end_to_end,
    }


def metric(slide, value: str, label: str, x: float, color: str, width: float = 2.55) -> None:
    textbox(slide, value, x, 1.62, width, 0.48, 27, color, True)
    textbox(slide, label, x, 2.12, width, 0.25, 9.2, MUTED, True)


def specs(slide, heading: str, rows: list[str], x: float, width: float, dot: str) -> None:
    textbox(slide, heading, x, 3.13, width, 0.24, 10, dot, True)
    y = 3.50
    for row in rows:
        bullet(slide, row, x, y, width, 9.35, MUTED, dot)
        y += 0.295


def runtime_slide(slide, metrics: dict[str, object]) -> None:
    title(slide, "VALIDATION · INFERENCE", "A 30.7B model, pinned end to end", "13")

    metric(slide, "30.7B", "DENSE PARAMETERS · GEMMA 4 31B IT", 0.74, GREEN, 2.55)
    metric(slide, "2× L40S", "46,068 MiB EACH · TENSOR PARALLEL 2", 3.72, BLUE, 2.70)
    metric(slide, "64", "CONCURRENT REQUESTS · MAX SEQUENCES", 6.96, CORAL, 2.45)
    metric(slide, "15h 51m", "FIRST OUTPUT → FINAL OUTPUT", 9.91, GREEN, 2.68)

    for x in (3.39, 6.63, 9.61):
        line(slide, x, 1.62, x, 2.40, LIGHT, 0.9)
    line(slide, 0.72, 2.70, 12.62, 2.70, LIGHT, 0.9)

    specs(
        slide,
        "MODEL + DECODING",
        [
            MODEL,
            f"revision {REVISION}",
            "BF16 · no quantization",
            "thinking on · gemma4 reasoning parser",
            "temperature 0.2",
            "seed = SHA-256(stage, note, attempt)",
            "8,192 context · 4,096 completion",
        ],
        0.74,
        3.55,
        GREEN,
    )
    specs(
        slide,
        "SCCKN + SERVING",
        [
            "AMD EPYC host · 8 CPU slots",
            "64 GB h_vmem / slot · ~52 GB observed peak",
            "CUDA 13.2 · GPU utilization target 90%",
            "vLLM 0.25.0 · async scheduling",
            "PyTorch 2.11.0+cu130",
            "Transformers 5.13.1",
            "32,768 batched tokens · prefix cache on",
            "language-model-only · local OpenAI-compatible endpoint",
        ],
        4.55,
        3.55,
        BLUE,
    )
    specs(
        slide,
        "INFERENCE CONTRACT + AUDIT",
        [
            "one note → one independent user prompt",
            "no system prompt · no guided generation",
            "strict JSON validation after generation",
            "no tweet context · no URL fetching",
            "no retrieval · embeddings · vector store",
            "no Gabriel scaffold or label in context",
            "≤3 attempts · durable per-attempt records",
            "25,734 judgments · 25,804 total attempts",
            "32.1M tokens · 99.75% first-attempt valid",
        ],
        8.37,
        4.05,
        CORAL,
    )

    line(slide, 0.72, 6.36, 12.62, 6.36, LIGHT, 0.9)
    textbox(slide, "ACTIVE PHASES", 0.74, 6.53, 1.23, 0.19, 8.4, MUTED, True)
    textbox(slide, "7h 18m", 1.84, 6.49, 0.73, 0.23, 11.4, BLUE, True)
    textbox(slide, "STAGE 1", 2.55, 6.53, 0.69, 0.18, 8.4, MUTED, True)
    textbox(slide, "+", 3.35, 6.49, 0.25, 0.23, 11.4, MUTED, True, PP_ALIGN.CENTER)
    textbox(slide, "36m", 3.72, 6.49, 0.58, 0.23, 11.4, CORAL, True)
    textbox(slide, "STAGE 1.5", 4.28, 6.53, 0.78, 0.18, 8.4, MUTED, True)
    textbox(slide, "+", 5.18, 6.49, 0.25, 0.23, 11.4, MUTED, True, PP_ALIGN.CENTER)
    textbox(slide, "4h 35m", 5.57, 6.49, 0.73, 0.23, 11.4, GREEN, True)
    textbox(slide, "STAGE 2", 6.28, 6.53, 0.68, 0.18, 8.4, MUTED, True)
    textbox(slide, "=", 7.12, 6.49, 0.25, 0.23, 11.4, MUTED, True, PP_ALIGN.CENTER)
    textbox(slide, "12h 28m", 7.48, 6.47, 0.93, 0.26, 13.0, GREEN, True)
    textbox(slide, "OBSERVED ACTIVE TIME", 8.46, 6.53, 1.55, 0.18, 8.4, MUTED, True)
    textbox(slide, "LOCAL vLLM · NO HOSTED API", 10.12, 6.53, 2.25, 0.18, 8.2, INK, True, PP_ALIGN.RIGHT)

    source(
        slide,
        "Canonical run manifests · SCCKN scheduler records · call timestamps · Google Gemma 4 model card",
    )


def build_generated(path: Path, metrics: dict[str, object]) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(W)
    presentation.slide_height = Inches(H)
    runtime_slide(base_slide(presentation), metrics)
    presentation.save(path)


def assemble(generated_path: Path) -> None:
    actual_hash = sha256(SOURCE)
    if actual_hash != SOURCE_SHA256:
        raise SystemExit(
            "V23 changed; refusing to overwrite manual edits. "
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
            b'<p:sldId id="287" r:id="rId39"/><p:sldId id="288" r:id="rId40"/>',
            b'<p:sldId id="287" r:id="rId39"/><p:sldId id="291" r:id="rId43"/>'
            b'<p:sldId id="288" r:id="rId40"/>',
            "post-method insertion point",
        )

        presentation_rels = source_zip.read("ppt/_rels/presentation.xml.rels")
        relationship = (
            b'<Relationship Id="rId43" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide36.xml"/>'
        )
        replacements["ppt/_rels/presentation.xml.rels"] = replace_once(
            presentation_rels,
            b"</Relationships>",
            relationship + b"</Relationships>",
            "presentation relationship",
        )

        content_types = source_zip.read("[Content_Types].xml")
        override = (
            b'<Override PartName="/ppt/slides/slide36.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        replacements["[Content_Types].xml"] = replace_once(
            content_types,
            b"</Types>",
            override + b"</Types>",
            "content type",
        )

        additions = {
            "ppt/slides/slide36.xml": new_slide,
            "ppt/slides/_rels/slide36.xml.rels": new_rels,
        }

        temporary = OUTPUT.with_suffix(".tmp.pptx")
        temporary.unlink(missing_ok=True)
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                output_zip.writestr(
                    info, replacements.get(info.filename, source_zip.read(info.filename))
                )
            for name, payload in additions.items():
                output_zip.writestr(name, payload)
        temporary.replace(OUTPUT)


def main() -> None:
    metrics = validate_contract()
    with tempfile.TemporaryDirectory() as directory:
        generated_path = Path(directory) / "gemma-runtime.pptx"
        build_generated(generated_path, metrics)
        assemble(generated_path)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
