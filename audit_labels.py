"""Load original reference labels and task-ID keyed audit decisions."""
from __future__ import annotations

import csv
import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "output"
STATUSES = {"confirmed", "rejected", "insufficient", "unassessed"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_adjudications():
    decisions = {}
    for row in read_csv(OUTPUT / "adjudications.csv"):
        task_id = row["task_id"]
        statuses = {row["a_status"], row["b_status"]}
        if not task_id or task_id in decisions or not statuses <= STATUSES:
            raise ValueError(f"Invalid or duplicate adjudication: {task_id}")
        evidence = OUTPUT / row["evidence"].split("#", 1)[0]
        if not evidence.is_file():
            raise ValueError(f"Missing evidence for {task_id}: {evidence}")
        if row["evidence_kind"] == "artifact_replay":
            replay = json.loads(evidence.read_text(encoding="utf-8"))["tasks"][task_id]["cases"]
            if row["b_status"] == "confirmed":
                wrong = replay["wrong_image_or_order"]
                if (wrong["upstream_score"], wrong["repaired_score"]) != (1, 0):
                    raise ValueError(f"Evidence does not establish a false acceptance: {task_id}")
            if row["a_status"] == "confirmed":
                for case, scores in {"chronological": (1, 1), "reverse": (0, 1),
                                     "incorrect_total": (0, 0)}.items():
                    result = replay[case]
                    if (result["upstream_score"], result["repaired_score"]) != scores:
                        raise ValueError(f"Evidence does not establish a false rejection: {task_id} {case}")
        decisions[task_id] = row
    return decisions


def audit_verdict(reference, decision):
    if decision is None:
        return reference
    statuses = {decision["a_status"], decision["b_status"]}
    if "confirmed" in statuses:
        return "Y"
    if "insufficient" in statuses:
        return "U"
    if "rejected" in statuses:
        return "N"
    return reference


def exclusion_reason(flagged, reference, decision):
    verdict = audit_verdict(reference, decision)
    if verdict in {"Y", "U"}:
        label = "有缺陷记录" if verdict == "Y" else "证据不足"
        return f"{label}：{decision['reason']}" if decision else f"参考标签为 {verdict}，待源码复核"
    if flagged and verdict != "N":
        return "v2 规则命中，尚无复核结论"
    return ""
