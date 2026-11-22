"""Run the bundled OSWorld metric against controlled PPTX artifacts."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import zipfile
from importlib.metadata import version

from PIL import Image
from PIL.PngImagePlugin import PngInfo
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from verify_b_counterexample import ROOT, SF, _build, diff_parts

UPSTREAM = ROOT / "data/osworld"
SOURCE = UPSTREAM / "desktop_env/evaluators/metrics/slides.py"
TASKS = UPSTREAM / "evaluation_examples/examples/libreoffice_impress"
CASES = {
    3: ("c82632a4-56b6-4db4-9dd1-3820ee3388e4", (2,)),
    5: ("bf4e9888-f10f-47af-8dba-76413038b73c", (1, 2, 3, 4, 5, 6)),
}
OUT = ROOT / "output/pptx_regression.json"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def pixels(content):
    with Image.open(io.BytesIO(content)) as image:
        rgba = image.convert("RGBA")
        return rgba.size, rgba.tobytes()


def reencode_png(content):
    with Image.open(io.BytesIO(content)) as image:
        out = io.BytesIO()
        metadata = PngInfo()
        metadata.add_text("audit", "lossless re-encoding control")
        image.save(out, format="PNG", pnginfo=metadata, compress_level=0)
    return out.getvalue()


def slide_images(content, slide_numbers):
    presentation = Presentation(io.BytesIO(content))
    return [
        [pixels(shape.image.blob) for shape in presentation.slides[number - 1].shapes
         if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
        for number in slide_numbers
    ]


def main():
    spec = importlib.util.spec_from_file_location("osworld_slides", SOURCE)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    results = {}

    for case, (task_id, slide_numbers) in CASES.items():
        task_path = TASKS / f"{task_id}.json"
        evaluator = json.loads(task_path.read_text(encoding="utf-8"))["evaluator"]
        if evaluator["func"] != "compare_pptx_files":
            raise ValueError(f"Unexpected evaluator for {task_id}: {evaluator['func']}")
        options = evaluator["options"]
        gold_path = SF / f"x{case}_gold.pptx"
        counterexample_path = SF / f"x{case}_counterexample.pptx"
        gold = gold_path.read_bytes()
        counterexample = counterexample_path.read_bytes()
        changed_media, added_or_removed = diff_parts(gold, counterexample)
        if added_or_removed or not changed_media or any(
            not part.startswith("ppt/media/") or not part.endswith(".png") for part in changed_media
        ):
            raise AssertionError(f"Counterexample changed unexpected parts for {task_id}")
        with zipfile.ZipFile(gold_path) as archive:
            recoded = {part: reencode_png(archive.read(part)) for part in changed_media}
        reencoded = _build(gold_path, recoded)
        if diff_parts(gold, reencoded) != (changed_media, []):
            raise AssertionError(f"Unexpected archive changes for {task_id}")

        reference = slide_images(gold, slide_numbers)
        if any(len(images) != 1 for images in reference):
            raise AssertionError(f"Expected one reference picture per checked slide for {task_id}")
        scores = {}
        for name, artifact, images_match in (
            ("correct", gold, True),
            ("wrong_image_or_order", counterexample, False),
            ("lossless_reencoding", reencoded, True),
        ):
            original = upstream.compare_pptx_files(io.BytesIO(artifact), io.BytesIO(gold),
                                                    **{**options, "enable_debug": False})
            image_match = slide_images(artifact, slide_numbers) == reference
            repaired = int(original == 1 and image_match)
            if original != 1 or image_match != images_match or repaired != int(images_match):
                raise AssertionError(f"{task_id} {name}: upstream={original}, pixel_match={image_match}, repaired={repaired}")
            scores[name] = {
                "artifact_sha256": digest(artifact),
                "upstream_score": original,
                "slide_images_match": image_match,
                "repaired_score": repaired,
            }
        results[task_id] = {
            "task": task_path.relative_to(ROOT).as_posix(),
            "task_sha256": digest(task_path.read_bytes()),
            "reference": gold_path.relative_to(ROOT).as_posix(),
            "counterexample": counterexample_path.relative_to(ROOT).as_posix(),
            "expected_asset": evaluator["expected"]["path"],
            "options": options,
            "image_slides": slide_numbers,
            "changed_media": changed_media,
            "cases": scores,
        }

    report = {
        "scope": "offline comparison of PPTX artifacts",
        "metric": SOURCE.relative_to(ROOT).as_posix(),
        "metric_sha256": digest(SOURCE.read_bytes()),
        "dependencies": {name: version(name) for name in ("python-pptx", "Pillow", "lxml")},
        "tasks": results,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for task_id, result in results.items():
        print(task_id, {name: (row["upstream_score"], row["repaired_score"])
                        for name, row in result["cases"].items()})


if __name__ == "__main__":
    main()
