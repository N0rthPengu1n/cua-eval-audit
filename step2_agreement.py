"""计算规则 v1 与第一轮参考标签的一致度。"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
SHEET = ROOT / "output" / "annotation_sheet.csv"
REPORT = ROOT / "output" / "agreement_report.md"

PRIORITY = ("NO_INIT_STATE", "VAGUE_X_STRICT", "OVERLONG_INSTRUCTION", "DUP_INSTRUCTION")
RULE_NAME = {
    "NO_INIT_STATE": "缺少初始状态",
    "VAGUE_X_STRICT": "模糊指令撞精确打分器",
    "OVERLONG_INSTRUCTION": "题目过长/多重约束",
    "OTHER": "其他",
}


def read_rows(path: Path):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f)), enc
        except UnicodeDecodeError:
            continue
    raise SystemExit("无法识别标注表编码，请用 Excel 另存为「CSV UTF-8（逗号分隔）」。")


def primary_tag(tags: str) -> str:
    ts = [t for t in (tags or "").split(";") if t]
    for t in PRIORITY:
        if t in ts:
            return t
    return "OTHER"


def kappa_level(k: float) -> str:
    if k < 0.20:
        return "极低（规则基本不可信，需要重写）"
    if k < 0.40:
        return "一般（规则需要大幅修订）"
    if k < 0.60:
        return "中等（规则可用，但需逐类校准）"
    if k < 0.80:
        return "较高（规则可用，做小修即可）"
    return "几乎完全一致（注意检查是否照抄规则）"


def compute(rows):
    valid, undecided, unfilled = [], [], []
    for r in rows:
        v = (r.get("human_verdict") or "").strip().upper()
        r["_v"] = v
        if v == "":
            unfilled.append(r["no"])
        elif v == "U":
            undecided.append(r)
        elif v in ("Y", "N"):
            valid.append(r)
        else:
            unfilled.append(f"{r['no']}(填了 {v})")

    tp = sum(1 for r in valid if r["rule_verdict"] == "SUSPECT" and r["_v"] == "Y")
    fp = sum(1 for r in valid if r["rule_verdict"] == "SUSPECT" and r["_v"] == "N")
    fn = sum(1 for r in valid if r["rule_verdict"] == "CLEAN" and r["_v"] == "Y")
    tn = sum(1 for r in valid if r["rule_verdict"] == "CLEAN" and r["_v"] == "N")
    n = tp + fp + fn + tn
    if n == 0:
        raise SystemExit("没有有效标注，请先在 human_verdict 列填 Y / N。")

    po = (tp + tn) / n
    p_rule = (tp + fp) / n
    p_human = (tp + fn) / n
    pe = p_rule * p_human + (1 - p_rule) * (1 - p_human)
    k = (po - pe) / (1 - pe) if (1 - pe) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    by_rule = defaultdict(lambda: [0, 0])
    for r in valid:
        if r["rule_verdict"] != "SUSPECT":
            continue
        t = primary_tag(r.get("rule_tags"))
        by_rule[t][1] += 1
        if r["_v"] == "Y":
            by_rule[t][0] += 1

    fp_examples = [r for r in valid if r["rule_verdict"] == "SUSPECT" and r["_v"] == "N"]
    fn_examples = [r for r in valid if r["rule_verdict"] == "CLEAN" and r["_v"] == "Y"]

    return {
        "rows": valid, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": n,
        "po": po, "pe": pe, "k": k, "precision": precision, "recall": recall,
        "by_rule": by_rule, "fp_examples": fp_examples, "fn_examples": fn_examples,
        "undecided": undecided, "unfilled": unfilled,
    }


def main():
    demo = "--demo" in sys.argv
    rows, enc = read_rows(SHEET)
    print(f"读取标注表：{len(rows)} 行，编码 {enc}")

    if demo:
        for r in rows:
            r["human_verdict"] = "Y" if r["rule_verdict"] == "SUSPECT" else "N"
        res = compute(rows)
        print("[自检模式] 用规则自身当人工标签，指标应全部为 1.0")
        print(f"  N={res['n']}  Precision={res['precision']:.3f}  "
              f"Recall={res['recall']:.3f}  Kappa={res['k']:.3f}")
        print("自检通过：脚本可正常运行。填完标注表后去掉 --demo 再跑一次即可。")
        return

    res = compute(rows)
    if res["unfilled"]:
        print("以下行还没填 human_verdict（只能填 Y / N / U）：")
        print("  " + ", ".join(map(str, res["unfilled"][:40])))
        print("补齐后重新运行。")
        return

    rule_lines = []
    for t, (hit, total) in sorted(res["by_rule"].items(), key=lambda x: (x[1][0] / x[1][1] if x[1][1] else 0)):
        rate = hit / total if total else 0
        rule_lines.append(f"| `{t}` | {RULE_NAME.get(t, t)} | {hit}/{total} | {rate * 100:.1f}% |")

    fp_lines = [
        f"| {r['no']} | `{primary_tag(r.get('rule_tags'))}` | {r['instruction'][:90].replace('|', '/')} | {r.get('note', '')[:60]} |"
        for r in res["fp_examples"][:8]
    ]
    fn_lines = [
        f"| {r['no']} | {r['instruction'][:100].replace('|', '/')} | {r.get('human_issue_type', '')} | {r.get('note', '')[:60]} |"
        for r in res["fn_examples"][:8]
    ]
    u_lines = [
        f"| {r['no']} | {r['instruction'][:100].replace('|', '/')} | {r.get('note', '')[:60]} |"
        for r in res["undecided"][:8]
    ]

    worst = min(res["by_rule"].items(), key=lambda x: (x[1][0] / x[1][1] if x[1][1] else 1))[0] if res["by_rule"] else "（无）"

    report = f"""# 第 2 步产出：规则 v1 与参考标签的一致度报告

> ⚠️ **口径更正（2026-11-21）**：数值保留不改动，「人工判断 / 独立标注 / 真值」等表述
> 已作废。参考标签为**人机协作产生**，非独立人工标注；Kappa 是「规则与参考标签的一致率」。
> 详见 `output/LABEL_PROVENANCE.md`。

样本：`output/annotation_sheet.csv`，{res['n']} 条参考标签（另有 {len(res['undecided'])} 条标为 U 待仲裁）。
方法：把**规则 v1 视作判定方 A**、**参考标签视作判定方 B**，计算两者的一致程度。

> 本项目不存在第二位独立标注者；Kappa 衡量的是自动规则与参考标签的一致程度，
> 不是评分者间信度，也不是规则准确率。

标注口径：`Y/N` 回答的是「按 `rule_tags` 指出的那条标准，这道题是否真的有问题」，
不是「这道题是否存在任何毛病」。若人工复核发现的是另一类问题（如打分器覆盖不全），
仍按原标准判定，把新发现写进 `note`，留到第 3 步修订规则时处理 ——
否则会把理由错配误算成规则命中，人为抬高 Kappa。

## 1. 混淆矩阵

|  | 人工判为坏题 (Y) | 人工判为没问题 (N) |
|---|---|---|
| **规则报可疑 (SUSPECT)** | TP = {res['tp']} | FP = {res['fp']}（误报） |
| **规则判正常 (CLEAN)** | FN = {res['fn']}（漏判） | TN = {res['tn']} |

## 2. 核心指标

| 指标 | 数值 | 人话解释 |
|---|---|---|
| Precision（精确率） | {res['precision']:.3f} | 规则报出来的可疑题里，真的有问题占多少 → **衡量误报** |
| Recall（召回率） | {res['recall']:.3f} | 真正的坏题里，规则抓到了多少 → **衡量漏判**（靠对照组估计） |
| Accuracy（一致率） | {res['po']:.3f} | 规则和人判断一致的比例 |
| 期望随机一致率 pe | {res['pe']:.3f} | 两者碰巧猜对的概率 |
| **Cohen's Kappa** | **{res['k']:.3f}** | 扣除碰巧一致后的一致性 → {kappa_level(res['k'])} |

Kappa = (po − pe) / (1 − pe)。Landis & Koch 常用分档：<0.2 极低、0.21–0.40 一般、
0.41–0.60 中等、0.61–0.80 较高、>0.80 几乎完全一致。

## 3. 逐条规则的命中率（第 3 步该修谁）

| 规则 | 含义 | 命中/样本 | 命中率 |
|---|---|---|---|
{chr(10).join(rule_lines) or '| （无可疑样本） | | | |'}

**优先修订：`{worst}`**（命中率最低，说明这条规则最容易被领域语义误导）。

## 4. 误报样例（规则报了，人工判没问题）

| 序号 | 规则 | 题目（截断） | 复核理由 |
|---|---|---|---|
{chr(10).join(fp_lines) or '| （无） | | | |'}

## 5. 漏判样例（规则没报，参考标签判 Y）

| 序号 | 题目（截断） | 问题类型 | 复核理由 |
|---|---|---|---|
{chr(10).join(fn_lines) or '| （无） | | | |'}

## 6. 说不清 / 待仲裁（U）

| 序号 | 题目（截断） | 备注 |
|---|---|---|
{chr(10).join(u_lines) or '| （无） | | |'}

这些「说不清」最有价值：它们说明**标准本身有边界模糊**，第 3 步写《标注规范 v1》时要专门定义。

## 7. 一个必须写进结论的限制

本样本是**分层抽样**（三类缺陷各约 8 条）并人为加入了 6 条对照组，
不是从 368 道题里等概率随机抽的。因此 Precision / Recall **只用于校准规则，
不能外推成「全题库有 X% 的坏题」**。第 1 步那个 14.1% 才是全量扫描的命中率。

"""
    REPORT.write_text(report, encoding="utf-8")

    print("=" * 62)
    print(f"第 2 步完成：有效标注 {res['n']} 条，待仲裁 {len(res['undecided'])} 条")
    print(f"  Precision {res['precision']:.3f} | Recall {res['recall']:.3f} | "
          f"Accuracy {res['po']:.3f} | Kappa {res['k']:.3f}")
    print(f"  Kappa 解读：{kappa_level(res['k'])}")
    print(f"  待修订规则：{worst}")
    print("-" * 62)
    print(f"已生成：{REPORT.relative_to(ROOT)}")
    print("=" * 62)


if __name__ == "__main__":
    main()
