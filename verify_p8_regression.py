"""Reproduce the p8 false rejection and its missing-underline control."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen

from pptx import Presentation

from replay_agent_pilot import ROOT, asset, load_cases

DEMO = ROOT / "data/sample_files/p8_title_style"
METRIC = ROOT / "data/osworld/desktop_env/evaluators/metrics/slides.py"
RUN = ROOT / "output/agent_run_01.json"


def fetch_references(entries, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if not entry["kind"].startswith("gold"):
            continue
        path = directory / entry["file"]
        if path.exists():
            continue
        with tempfile.TemporaryDirectory(dir=directory) as scratch:
            candidate = Path(scratch) / path.name
            with urlopen(entry["url"], timeout=45) as response, candidate.open("wb") as output:
                shutil.copyfileobj(response, output)
            asset(entries, entry["kind"], candidate.parent)
            candidate.replace(path)


def title_shape(deck):
    return next(shape for shape in deck.slides[0].shapes if shape.name == "TextBox 18")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=Path(tempfile.gettempdir()) / "cua_pilot_assets")
    parser.add_argument("--fetch", action="store_true", help="Download the two public reference files")
    args = parser.parse_args()

    task, entries = load_cases()["p8"]
    evaluator = task["evaluator"]
    if evaluator["func"] != ["compare_pptx_files"] * 2 or evaluator["conj"] != "or":
        raise ValueError("Unexpected p8 evaluator")
    if args.fetch:
        fetch_references(entries, args.assets)
    references = [asset(entries, f"gold{i}_0", args.assets) for i in range(2)]

    spec = importlib.util.spec_from_file_location("osworld_slides", METRIC)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)

    positive = DEMO / "agent_result.pptx"
    negative = DEMO / "missing_underline.pptx"
    record = next(row for row in json.loads(RUN.read_text(encoding="utf-8"))["tasks"] if row["case"] == "p8")
    if hashlib.sha256(positive.read_bytes()).hexdigest() != record["artifact_sha256"]:
        raise ValueError("The positive fixture differs from the scored Agent output")

    for label, artifact, expected in (
        ("agent_result", positive, ([0, 0], [1, 1])),
        ("missing_underline", negative, ([0, 0], [0, 0])),
    ):
        branch_scores = [
            [upstream.compare_pptx_files(str(artifact), str(ref), examine_shape=geometry,
                                         enable_debug=False) for ref in references]
            for geometry in (True, False)
        ]
        if tuple(branch_scores) != expected:
            raise AssertionError(f"{label}: {branch_scores}")
        print(f"{label}: original={branch_scores[0]}, geometry diagnostic={branch_scores[1]}")

    deck = Presentation(positive)
    title_shape(deck).height = title_shape(Presentation(references[0])).height
    diagnostic = io.BytesIO()
    deck.save(diagnostic)
    diagnostic.seek(0)
    height_only = upstream.compare_pptx_files(diagnostic, str(references[0]), enable_debug=False)
    if height_only != 1:
        raise AssertionError(f"Changing only title height should give 1, got {height_only}")
    print(f"agent_result with gold0 title height only: gold0={height_only}")


if __name__ == "__main__":
    main()
