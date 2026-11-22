"""Recompute round 2 agreement from the reference sheet and adjudication ledger."""
from __future__ import annotations

from audit_labels import OUTPUT, audit_verdict, load_adjudications, read_csv

SHEET = OUTPUT / "annotation_sheet_round2.csv"
OUT = OUTPUT / "round2_recomputed.md"


def compute(rows, decisions):
    bins = {key: [] for key in ("TP", "FP", "FN", "TN", "U")}
    for row in rows:
        task_id = row["task_id"]
        label = audit_verdict(row["human_verdict"].strip().upper(), decisions.get(task_id))
        rule = row["rule_verdict"]
        if rule not in {"SUSPECT", "CLEAN"} or label not in {"Y", "N", "U"}:
            raise ValueError(f"Invalid labels for {task_id}: {rule}, {label}")
        if label == "U":
            bins["U"].append(row["no"])
        elif rule == "SUSPECT":
            bins["TP" if label == "Y" else "FP"].append(row["no"])
        else:
            bins["FN" if label == "Y" else "TN"].append(row["no"])

    tp, fp, fn, tn, _ = map(len, bins.values())
    n = tp + fp + fn + tn
    accuracy = (tp + tn) / n if n else None
    expected = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / n**2 if n else None
    return bins, {
        "Precision": tp / (tp + fp) if tp + fp else None,
        "Recall": tp / (tp + fn) if tp + fn else None,
        "Accuracy": accuracy,
        "Kappa": (accuracy - expected) / (1 - expected) if n and expected != 1 else None,
    }


def format_summary(bins, metrics):
    counts = [len(bins[key]) for key in ("TP", "FP", "FN", "TN")]
    values = ["—" if value is None else f"{value:.3f}" for value in metrics.values()]
    return " | ".join(["/".join(map(str, counts)), str(sum(counts)), str(len(bins["U"])), *values])


def main():
    rows = read_csv(SHEET)
    if len({row["task_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate task_id in round 2")
    decisions = load_adjudications()
    bins, metrics = compute(rows, decisions)
    base, base_metrics = compute(rows, {})
    details = []
    for row in rows:
        decision = decisions.get(row["task_id"])
        if decision:
            details.append(
                f"| {row['no']} | `{row['task_id']}` | {row['human_verdict']} | "
                f"{audit_verdict(row['human_verdict'], decision)} | "
                f"{decision['a_status']} / {decision['b_status']} | {decision['reason']} |"
            )
    bucket_rows = [f"| {key} | {len(values)} | {', '.join(values) or '—'} |"
                   for key, values in bins.items()]
    report = [
        "# 第二轮规则与参考标签的一致度复算",
        "",
        "当前口径使用 [裁决表](adjudications.csv)，按完整 task_id 关联原始标注。"
        "已确认的 A 或 B 计 Y；没有确认项但仍有证据不足的维度计 U；"
        "针对已复核问题的否定裁决计 N。无裁决时沿用原始参考标签。",
        "",
        "| 口径 | TP/FP/FN/TN | 有效 N | U | Precision | Recall | Accuracy | Kappa |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
        f"| **当前裁决** | {format_summary(bins, metrics)} |",
        f"| 第二轮原始参考标签 | {format_summary(base, base_metrics)} |",
        "| 历史口径 D | 2/2/4/22 | 30 | 0 | 0.500 | 0.333 | 0.800 | 0.286 |",
        "",
        "X3、X5 均通过同一证据门槛。原评分器接受违反图片身份或顺序的产物，"
        "因此两题均按 B 类确认并计 Y。[评分记录](pptx_regression.json)",
        "",
        "样本包含 4 道规则命中和 26 道分层抽取的未命中任务。U 排除在二分类分母外。"
        "当前统计混用了人机协作参考标签和有证据的裁决，且规则本身未覆盖 B 类。"
        "这些指标只描述本样本的规则与参考判断一致度。",
        "",
        "| 分箱 | 条数 | 原标注表行号 |",
        "|---|---:|---|",
        *bucket_rows,
        "",
        "| 行号 | task_id | 原值 | 裁决后 | A / B 状态 | 理由 |",
        "|---|---|---|---|---|---|",
        *details,
    ]
    OUT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(f"当前裁决：{format_summary(bins, metrics)}")


if __name__ == "__main__":
    main()
