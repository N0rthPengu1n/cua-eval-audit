"""计算规则 v2 在第二轮独立样本上的一致度。"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
REPORT = OUT / "round2_report.md"

CAUSE = [
    ("约束—验收覆盖缺口", re.compile(r"验收|打分器|校验|覆盖|evaluator|未检查|没检查|未验证|约束")),
    ("指令歧义 / 多解", re.compile(r"歧义|模糊|多种|多解|未限定|没说明|不确定")),
    ("初始状态 / 复现", re.compile(r"初始|预置|config|文件不存在|状态")),
    ("环境漂移 / 外部依赖", re.compile(r"漂移|外部|网页|链接|URL|版本")),
]


def read_csv(path: Path):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"无法读取 {path}")


def confusion(rows, flagged):
    tp = fp = fn = tn = 0
    undecided = []
    valid = []
    for r in rows:
        v = (r.get("human_verdict") or "").strip().upper()
        if v == "U":
            undecided.append(r)
            continue
        if v not in ("Y", "N"):
            continue
        valid.append(r)
        suspect = r["task_id"] in flagged
        if suspect and v == "Y": tp += 1
        elif suspect and v == "N": fp += 1
        elif not suspect and v == "Y": fn += 1
        else: tn += 1
    n = tp + fp + fn + tn
    if not n:
        return dict(tp=0, fp=0, fn=0, tn=0, n=0, precision=0, recall=0,
                    po=0, pe=0, kappa=0, undecided=undecided, valid=valid)
    po = (tp + tn) / n
    p_rule = (tp + fp) / n
    p_human = (tp + fn) / n
    pe = p_rule * p_human + (1 - p_rule) * (1 - p_human)
    k = (po - pe) / (1 - pe) if (1 - pe) else 1.0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, n=n,
                precision=tp / (tp + fp) if (tp + fp) else 0,
                recall=tp / (tp + fn) if (tp + fn) else 0,
                po=po, pe=pe, kappa=k, undecided=undecided, valid=valid)


def cause_of(note: str) -> str:
    for name, pat in CAUSE:
        if pat.search(note or ""):
            return name
    return "其他 / 未归因"


def main():
    demo = "--demo" in sys.argv
    r1 = read_csv(OUT / "annotation_sheet.csv")
    r2 = read_csv(OUT / "annotation_sheet_round2.csv")
    v2 = read_csv(OUT / "rule_v2" / "task_profile.csv")
    flagged = {r["task_id"] for r in v2 if int(r["defect_count"] or 0) > 0}

    if demo:
        for r in r2:
            r["human_verdict"] = "Y" if r["task_id"] in flagged else "N"
        res = confusion(r2, flagged)
        print("[自检模式] 用 v2 规则自身当人工标签，指标应全部为 1.0")
        print(f"  N={res['n']}  TP={res['tp']}  FP={res['fp']}  FN={res['fn']}  TN={res['tn']}")
        print(f"  Precision={res['precision']:.3f}  Recall={res['recall']:.3f}  Kappa={res['kappa']:.3f}")
        print("自检通过：脚本可正常运行。填完标注表后去掉 --demo 再跑一次即可。")
        return

    unfilled = [r["no"] for r in r2 if (r.get("human_verdict") or "").strip().upper() not in ("Y", "N", "U")]
    if unfilled:
        print("以下行还没填 human_verdict（只能填 Y / N / U）：")
        print("  " + ", ".join(map(str, unfilled[:40])))
        print("补齐后重新运行。")
        return

    m1 = confusion(r1, flagged)
    m2 = confusion(r2, flagged)

    must_lines = []
    for r in r2:
        if r["task_id"] in flagged:
            v = (r["human_verdict"] or "").strip().upper()
            must_lines.append(
                f"| {r['no']} | `{r['task_id'][:8]}` | {v} | `{r['rule_tags'] or '—'}` | "
                f"{(r['note'] or '')[:64]} |"
            )

    fp_rows = [r for r in m2["valid"] if r["task_id"] in flagged and r["human_verdict"].strip().upper() == "N"]
    fn_rows = [r for r in m2["valid"] if r["task_id"] not in flagged and r["human_verdict"].strip().upper() == "Y"]
    fp_lines = [f"| {r['no']} | {r['stratum']} | `{r['rule_tags']}` | {(r['note'] or '')[:64]} |"
                for r in fp_rows[:8]] or ["| （无） | | | |"]
    fn_lines = [f"| {r['no']} | {r['stratum']} | {cause_of(r['note'])} | {(r['note'] or '')[:64]} |"
                for r in fn_rows[:8]] or ["| （无） | | | |"]
    cause_cnt = Counter(cause_of(r["note"]) for r in fn_rows)
    cause_lines = "\n".join(f"| {k} | {v} |" for k, v in cause_cnt.most_common()) or "| （无漏判） | 0 |"

    by_stratum = defaultdict(lambda: [0, 0, 0])
    for r in m2["valid"]:
        s = r["stratum"]
        by_stratum[s][0] += 1
        if r["task_id"] in flagged: by_stratum[s][1] += 1
        if r["human_verdict"].strip().upper() == "Y": by_stratum[s][2] += 1
    stratum_lines = "\n".join(
        f"| {s} | {v[0]} | {v[1]} | {v[2]} |"
        for s, v in sorted(by_stratum.items(), key=lambda x: -x[1][0])
    ) or "| （无） | | | |"

    u_lines = [
        f"| {r['no']} | {r['stratum']} | {(r['note'] or '')[:70]} |"
        for r in m2["undecided"][:8]
    ] or ["| （无） | | |"]

    if m2["n"] == 0:
        verdict = "没有有效标注，无法评估。"
    elif fn_rows:
        verdict = (
            f"独立样本里出现 **{len(fn_rows)} 条漏判**，说明第 3 步的担忧被证实："
            "v2 变保守之后，Precision 好看了，但确实把一部分真问题留在了「没被报出来」的题里。"
            "这不是失败，而是本项目最有价值的发现之一 —— 它说明**字段规则有天花板，"
            "规范 3.5 的人工复核清单不能省**。下一步应把漏判归因写进 v1.1 规范，"
            "并评估哪些维度值得做成新规则。"
        )
    elif fp_rows:
        verdict = (
            f"独立样本里出现 **{len(fp_rows)} 条误报**，说明 v2 在新领域仍有语义陷阱，"
            "需要继续收窄规则；但没发现漏判，召回表现暂时稳定。"
            "注意必查项只有 4 条，样本量小，不能据此宣称规则已可靠。"
        )
    else:
        verdict = (
            "独立样本里既未出现误报，也未出现漏判，v2 在这一轮表现稳定。"
            "**但请克制**：必查项仅 4 条、分层随机 26 条，样本量不足以证明规则可靠；"
            "更准确的结论是「未发现反例」，而不是「规则已验证有效」。"
        )

    delta_p = m2["precision"] - m1["precision"]
    delta_k = m2["kappa"] - m1["kappa"]

    report = f"""# 第 4 步 A 产出：规则 v2 独立样本复测报告

样本：`output/annotation_sheet_round2.csv`，30 条，**与第 1 轮 30 条零重叠**（seed 44）。
抽样方法与分层配额见 `output/round2_sampling_note.md`。
判定口径依《CUA 评测任务标注规范 v1.1》。
> ⚠️ 口径更正（2026-11-21）：参考标签由人机协作产生，**非独立人工标注**；
> 所有指标是「规则与参考标签的一致率」，不是准确率。见 `output/LABEL_PROVENANCE.md`。
> ⚠️ **定稿更正（2026-11-21）**：本报告是**裁决前历史记录**，数值保留不篡改，
> 但不再作为结论。最终以口径 D 为准：**一致率 0.500 / Kappa 0.286（N=30、U=0）**，
> 见 `output/round2_recomputed.md` 与 `output/failure_taxonomy.md` v1.0。

## 一句话结论

{verdict}

## 1. 为什么这一轮才算数

第 3 步报告里 v2 的 Precision / Kappa 是 **1.000**，但那 30 条正是用来改规则的样本，
属于「拿训练集自测」，报告第 6 节已明确警告不可作为效果证明。

本轮 30 条排除了第 1 轮的全部 task_id，其中 4 条是 v2 命中但从未人工复核过的必查项，
26 条按 11 个应用领域分层随机抽出（用于查漏判）。**这才是独立测试集**，
两轮指标的差值就是泛化差距。

## 2. 混淆矩阵与核心指标

| 指标 | v2 @ 第 1 轮（训练集） | v2 @ 第 2 轮（独立测试集） | 差值 |
|---|---|---|---|
| 有效标注 N | {m1['n']} | {m2['n']} | — |
| TP / FP / FN / TN | {m1['tp']}/{m1['fp']}/{m1['fn']}/{m1['tn']} | {m2['tp']}/{m2['fp']}/{m2['fn']}/{m2['tn']} | — |
| Precision | {m1['precision']:.3f} | {m2['precision']:.3f} | {delta_p:+.3f} |
| Recall | {m1['recall']:.3f} | {m2['recall']:.3f} | {m2['recall'] - m1['recall']:+.3f} |
| Accuracy | {m1['po']:.3f} | {m2['po']:.3f} | {m2['po'] - m1['po']:+.3f} |
| Cohen's Kappa | {m1['kappa']:.3f} | {m2['kappa']:.3f} | {delta_k:+.3f} |

> 两轮都用**同一套 v2 规则**和同一套口径计算，唯一差别是样本是否参与过规则设计，
> 因此差值可以解释为泛化差距，而不是口径变化。

## 3. 必查 4 道的复核结论

| 序号 | task_id | 参考标签 | v2 标签 | 理由 |
|---|---|---|---|---|
{chr(10).join(must_lines) or '| （无） | | | | |'}

这 4 道是第 3 步报告第 8 节点名要查的「v2 命中但未经人工判断」的题。
它们数量少、优先级最高，直接决定 v2 的 Precision 是真是假。

## 4. 误报样例（v2 报了，参考标签判 N）

| 序号 | 领域 | 标签 | 理由 |
|---|---|---|---|
{chr(10).join(fp_lines)}

## 5. 漏判样例（v2 没报，参考标签判 Y）

> ⚠️ **复核更正（2026-11-21）**：本节第 6、11、16、25、28 行的归因经 evaluator
> 配置与评分器源码核对后**已被撤销或降级**，不能作为已确认缺陷。
> 详见 `output/failure_taxonomy.md` v0.2 与 `output/evaluator_evidence.md`。


| 序号 | 领域 | 归因 | 理由 |
|---|---|---|---|
{chr(10).join(fn_lines)}

漏判归因分布（按 `note` 关键词粗分，仅作方向性提示）：

| 归因 | 条数 |
|---|---|
{cause_lines}

> 特别留意「约束—验收覆盖缺口」：这正是《标注规范 v1.1》3.5 故意不做自动化、
> 只列入人工清单的维度。如果它在本轮漏判里占多数，就实证了那条决策是对的 ——
> **不是所有质量维度都适合写成字段规则**。

## 6. 按领域分层的表现

| 中文领域 | 样本数 | v2 报可疑 | 参考标签判 Y |
|---|---|---|---|
{stratum_lines}

分层是为了让小领域不被 chrome / calc 两个大头淹没。由于各层抽样概率不同，
本表**不能**外推为全库缺陷率。

## 7. 说不清 / 待仲裁（U）

| 序号 | 领域 | 备注 |
|---|---|---|
{chr(10).join(u_lines)}

`U` 是标准边界模糊的信号，应写进《标注规范 v1.1》的「边界情况」。

## 8. 结论限制

本报告保留裁决前的原始结果；最终统计以 `output/round2_recomputed.md` 的口径 D 为准。
参考标签并非独立人工标注，且样本量小、分层抽样不可外推为全库缺陷率。
"""

    REPORT.write_text(report, encoding="utf-8")

    print("=" * 62)
    print("第 4 步 A 完成：规则 v2 独立测试集复测")
    print("=" * 62)
    print(f"训练集(第1轮) N={m1['n']}  Precision {m1['precision']:.3f}  Kappa {m1['kappa']:.3f}")
    print(f"测试集(第2轮) N={m2['n']}  Precision {m2['precision']:.3f}  Kappa {m2['kappa']:.3f}")
    print(f"泛化差距       Precision {delta_p:+.3f}  Kappa {delta_k:+.3f}")
    print(f"  混淆矩阵 TP/FP/FN/TN = {m2['tp']}/{m2['fp']}/{m2['fn']}/{m2['tn']}"
          f"，待仲裁 U = {len(m2['undecided'])}")
    print("-" * 62)
    print(f"已生成：{REPORT.relative_to(ROOT)}")
    print("=" * 62)


if __name__ == "__main__":
    main()
