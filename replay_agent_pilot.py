"""Prepare agent inputs and score saved file artifacts for five reviewed tasks."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import tempfile
from zipfile import BadZipFile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "output/pilot_review_assets.json"
PILOT = ROOT / "output/pilot_review.csv"
TASK_NUMBERS = ("3", "6", "8", "9", "10")
P10_STRETCH_TOLERANCE = 0.01


def load_cases():
    assets = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with PILOT.open(encoding="utf-8-sig", newline="") as stream:
        rows = {str(int(row["pilot_id"])): row for row in csv.DictReader(stream)}
    cases = {}
    for number in TASK_NUMBERS:
        row = rows[number]
        task = json.loads((ROOT / row["task_json"]).read_text(encoding="utf-8"))
        if task["id"] != row["task_id"]:
            raise ValueError(f"Task mismatch for pilot {number}")
        cases[f"p{number}"] = (task, assets[task["id"]]["assets"])
    return cases


def asset(entries, kind, directory):
    record, = [entry for entry in entries if entry["kind"] == kind]
    path = directory / record["file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError(f"Asset checksum mismatch: {path.name}")
    return path


def prepare(cases, assets, destination):
    for case, (task, entries) in cases.items():
        source = asset(entries, "initial", assets)
        initial_name = source.name.removeprefix(f"{case}_initial_")
        directory = destination / case
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, directory / initial_name)
        (directory / "task.txt").write_text(
            f"{task['instruction'].strip()}\n\nInitial file: {initial_name}\n"
            f"Save your result as result{source.suffix} and return it with any available action log.\n",
            encoding="utf-8",
        )


def load_metrics():
    from verify_xlsx_regression import load_upstream_metric

    source = ROOT / "data/osworld/desktop_env/evaluators/metrics/slides.py"
    spec = importlib.util.spec_from_file_location("pilot_slides", source)
    slides = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(slides)
    return {"compare_table": load_upstream_metric(),
            "compare_pptx_files": slides.compare_pptx_files,
            "check_image_stretch_and_center": slides.check_image_stretch_and_center}


def original_score(artifact, evaluator, entries, assets, metrics):
    funcs = evaluator["func"]
    if isinstance(funcs, str):
        funcs = [funcs]
    options = evaluator.get("options", {})
    if isinstance(options, dict):
        options = [options] * len(funcs)
    scores = []
    for index, (func, option) in enumerate(zip(funcs, options, strict=True)):
        gold = asset(entries, f"gold{index}_0", assets)
        kwargs = dict(option or {})
        if func == "compare_pptx_files":
            kwargs["enable_debug"] = False
        score = float(metrics[func](str(artifact), str(gold), **kwargs))
        scores.append(score)
        if evaluator.get("conj") == "or" and score == 1:
            break
        if evaluator.get("conj", "and") == "and" and score == 0:
            return 0.0, scores
    aggregate = max(scores) if evaluator.get("conj") == "or" else sum(scores) / len(scores)
    return aggregate, scores


def geometry_score(artifact, reference, upstream):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    if not upstream:
        return 0, None
    source = next(shape for shape in Presentation(reference).slides[0].shapes
                  if shape.shape_type == MSO_SHAPE_TYPE.PICTURE)
    matches = [shape for shape in Presentation(artifact).slides[0].shapes
               if shape.shape_type == MSO_SHAPE_TYPE.PICTURE and shape.image.blob == source.image.blob]
    if not matches:
        return 0, None
    picture = matches[-1]
    image_width, image_height = picture.image.size
    visible_width = image_width * (1 - picture.crop_left - picture.crop_right)
    visible_height = image_height * (1 - picture.crop_top - picture.crop_bottom)
    if min(visible_width, visible_height, picture.width, picture.height) <= 0:
        return 0, None
    frame_ratio = picture.width / picture.height
    visible_image_ratio = visible_width / visible_height
    relative_stretch = frame_ratio / visible_image_ratio - 1
    return int(abs(relative_stretch) <= P10_STRETCH_TOLERANCE), {
        "frame_ratio": frame_ratio,
        "visible_image_ratio": visible_image_ratio,
        "relative_stretch": relative_stretch,
        "tolerance": P10_STRETCH_TOLERANCE,
    }


def score(cases, assets, artifacts, destination, run_kind, run_id, agent):
    from pptx.exc import PackageNotFoundError

    metrics = load_metrics()
    scores = []
    for case, (task, entries) in cases.items():
        source = asset(entries, "initial", assets)
        artifact = artifacts / case / f"result{source.suffix}"
        log = artifact.with_name("action_log.jsonl")
        row = {"case": case, "task_id": task["id"], "artifact": artifact.relative_to(artifacts).as_posix(),
               "status": "missing_artifact", "original_score": None, "repaired_score": None}
        if log.is_file():
            row["action_log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
        if artifact.is_file():
            row["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            try:
                upstream, branches = original_score(artifact, task["evaluator"], entries, assets, metrics)
                row.update(status="scored", original_score=upstream, original_branches=branches)
                if case == "p10":
                    reference = asset(entries, "gold0_0", assets)
                    repaired, geometry = geometry_score(artifact, reference, upstream)
                    row.update(repaired_score=repaired, image_geometry=geometry)
            except (BadZipFile, KeyError, OSError, PackageNotFoundError, ValueError) as error:
                row.update(status="scoring_error", error=str(error))
        scores.append(row)

    report = {"scope": "offline saved artifacts", "run_kind": run_kind, "run_id": run_id,
              "agent": agent, "tasks": scores}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=Path(tempfile.gettempdir()) / "cua_pilot_assets")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("destination", type=Path)
    score_parser = commands.add_parser("score")
    score_parser.add_argument("artifacts", type=Path)
    score_parser.add_argument("destination", type=Path)
    score_parser.add_argument("--run-kind", choices=("agent", "fixture"), required=True)
    score_parser.add_argument("--run-id", required=True)
    score_parser.add_argument("--agent")
    args = parser.parse_args()
    cases = load_cases()
    if args.command == "prepare":
        prepare(cases, args.assets, args.destination)
    else:
        if args.run_kind == "agent" and not args.agent:
            parser.error("--agent is required for an agent run")
        score(cases, args.assets, args.artifacts, args.destination, args.run_kind, args.run_id, args.agent)


if __name__ == "__main__":
    main()
