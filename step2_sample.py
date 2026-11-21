"""生成第一轮分层参考标签表。"""
from __future__ import annotations

import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT / "output" / "task_profile.csv"
OUT = ROOT / "output" / "annotation_sheet.csv"

SEED = 42
QUOTA = {"NO_INIT_STATE": 8, "VAGUE_X_STRICT": 8, "OVERLONG_INSTRUCTION": 8}
SUSPECT_N = 24
CONTROL_N = 6
PRIORITY = ("NO_INIT_STATE", "VAGUE_X_STRICT", "OVERLONG_INSTRUCTION", "DUP_INSTRUCTION")

FIELDS = [
    "no", "task_id", "app", "instruction", "instruction_words",
    "evaluator_func", "config_steps", "env_risk",
    "rule_tags", "rule_verdict",
    "human_verdict", "human_issue_type", "note",
]


def primary_tag(row: dict) -> str:
    tags = [t for t in row["defect_tags"].split(";") if t]
    for t in PRIORITY:
        if t in tags:
            return t
    return "OTHER"


def main():
    rows = list(csv.DictReader(PROFILE.open(encoding="utf-8-sig", newline="")))
    suspect = [r for r in rows if int(r["defect_count"]) > 0]
    clean = [r for r in rows if int(r["defect_count"]) == 0]

    groups = defaultdict(list)
    for r in suspect:
        groups[primary_tag(r)].append(r)

    rng = random.Random(SEED)
    picked = []
    for tag, quota in QUOTA.items():
        pool = groups.get(tag, [])
        picked += rng.sample(pool, min(quota, len(pool)))

    chosen_ids = {r["task_id"] for r in picked}
    rest = [r for r in suspect if r["task_id"] not in chosen_ids]
    need = SUSPECT_N - len(picked)
    if need > 0:
        picked += rng.sample(rest, min(need, len(rest)))

    clean_risky = [r for r in clean if r["risk_tags"]]
    clean_pure = [r for r in clean if not r["risk_tags"]]
    control = rng.sample(clean_risky, min(3, len(clean_risky)))
    control += rng.sample(clean_pure, min(CONTROL_N - len(control), len(clean_pure)))
    control_ids = {r["task_id"] for r in control}
    if len(control) < CONTROL_N:
        extra = [r for r in clean if r["task_id"] not in control_ids]
        control += rng.sample(extra, min(CONTROL_N - len(control), len(extra)))

    items = [("SUSPECT", r) for r in picked] + [("CLEAN", r) for r in control]
    rng.shuffle(items)

    out_rows = []
    for i, (verdict, r) in enumerate(items, 1):
        out_rows.append({
            "no": i,
            "task_id": r["task_id"],
            "app": r["app"],
            "instruction": r["instruction"],
            "instruction_words": r["instruction_words"],
            "evaluator_func": r["evaluator_func"],
            "config_steps": r["config_steps"],
            "env_risk": r["env_risk"],
            "rule_tags": r["defect_tags"],
            "rule_verdict": verdict,
            "human_verdict": "",
            "human_issue_type": "",
            "note": "",
        })

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)

    tag_stat = defaultdict(int)
    for r in picked:
        tag_stat[primary_tag(r)] += 1
    print("=" * 62)
    print("第 2 步标注表已生成")
    print("=" * 62)
    print(f"总条数 {len(items)}：可疑组 {len(picked)} + 对照组 {len(control)}（顺序已打乱）")
    print("可疑组构成：", dict(tag_stat))
    print(f"对照组构成：带风险 {sum(1 for r in control if r['risk_tags'])} / 完全干净 {sum(1 for r in control if not r['risk_tags'])}")
    print(f"随机种子 {SEED}，可复现")
    print("-" * 62)
    print(f"请打开：{OUT.relative_to(ROOT)}")
    print("填写 human_verdict 列（Y / N / U），保存后运行：python step2_agreement.py")
    print("=" * 62)


if __name__ == "__main__":
    main()
