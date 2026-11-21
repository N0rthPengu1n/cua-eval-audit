"""在内存副本上按最终裁决复算规则 v2 与参考标签的一致度。"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHEET = ROOT / "output" / "annotation_sheet_round2.csv"
OUT = ROOT / "output" / "round2_recomputed.md"

ADJUDICATION: dict[str, tuple[str, str, str]] = {
    "6":  ("Y", "B", "X3 撤销原 A；改列 B 类候选并保留在台账（compare_pptx_files 不比对图片内容）"),
    "11": ("U", "A?", "X1 撤销原 B；暂列 U 待源文件顺序补证，不纳入有效指标"),
    "16": ("N", "", "X4 撤销 A 归因，无替代归类"),
    "21": ("N", "", "查 PDF 表单上下文后歧义消解，由 U 改判 N（标注表原值不动）"),
    "25": ("Y", "B", "X5 改列 B 类候选并保留在台账（compare_pptx_files 不比对图片内容/顺序）"),
    "28": ("N", "", "X2 撤销 A 归因，无替代归类"),
    "30": ("N", "", "查工作簿上下文后歧义消解，由 U 改判 N（标注表原值不动）"),
}

USER_VARIANT: dict[str, tuple[str, str, str]] = dict(ADJUDICATION)
USER_VARIANT["25"] = (
    "N", "B",
    "X5 在一致度计算中按 N 处理（口径 C）；台账仍保留为 B 类候选",
)

FINAL_VARIANT: dict[str, tuple[str, str, str]] = dict(USER_VARIANT)
FINAL_VARIANT["11"] = (
    "N", "",
    "X1 顺序补证：源 docx 与金标字节一致、顺序唯一 → A 不成立，由 U 结案改判 N",
)


def read_sheet(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def compute(rows: list[dict], override: dict[str, tuple[str, str, str]] | None = None):
    """在内存副本上计算混淆矩阵与一致度指标。"""
    override = override or {}
    eff = []
    for r in rows:
        no = r["no"].strip()
        v = (r["human_verdict"] or "").strip().upper()
        if no in override:
            v = override[no][0]
        eff.append({"no": no, "rule": r["rule_verdict"], "v": v})

    valid = [e for e in eff if e["v"] in ("Y", "N")]
    u = [e for e in eff if e["v"] == "U"]

    tp = sum(1 for e in valid if e["rule"] == "SUSPECT" and e["v"] == "Y")
    fp = sum(1 for e in valid if e["rule"] == "SUSPECT" and e["v"] == "N")
    fn = sum(1 for e in valid if e["rule"] == "CLEAN" and e["v"] == "Y")
    tn = sum(1 for e in valid if e["rule"] == "CLEAN" and e["v"] == "N")
    n = len(valid)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    accuracy = (tp + tn) / n if n else 0.0

    p_obs = accuracy
    p_yes_rule = (tp + fp) / n if n else 0.0
    p_yes_label = (tp + fn) / n if n else 0.0
    p_exp = (p_yes_rule * p_yes_label
             + (1 - p_yes_rule) * (1 - p_yes_label))
    kappa = (p_obs - p_exp) / (1 - p_exp) if (1 - p_exp) else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": n, "u": len(u),
        "precision": precision, "recall": recall,
        "accuracy": accuracy, "kappa": kappa,
        "u_rows": [e["no"] for e in u],
        "tp_rows": [e["no"] for e in valid if e["rule"] == "SUSPECT" and e["v"] == "Y"],
        "fp_rows": [e["no"] for e in valid if e["rule"] == "SUSPECT" and e["v"] == "N"],
        "fn_rows": [e["no"] for e in valid if e["rule"] == "CLEAN" and e["v"] == "Y"],
        "tn_rows": [e["no"] for e in valid if e["rule"] == "CLEAN" and e["v"] == "N"],
    }


def fmt(m) -> str:
    return (f"{m['tp']}/{m['fp']}/{m['fn']}/{m['tn']} | N={m['n']}, U={m['u']} | "
            f"P={m['precision']:.3f} R={m['recall']:.3f} "
            f"Acc={m['accuracy']:.3f} Kappa={m['kappa']:.3f}")


def main() -> None:
    rows = read_sheet(SHEET)
    assert len(rows) == 30, f"标注表应为 30 行，实际 {len(rows)}"

    base = compute(rows)                        # A 原始（未裁决）
    textual = compute(rows, ADJUDICATION)       # B 裁决·文字口径（X5 保留 Y）
    user_c = compute(rows, USER_VARIANT)        # C 口径 C（X5 按 N，X1 仍 U）
    final = compute(rows, FINAL_VARIANT)        # D 口径 D（C + X1 结案）← **最终采用**

    for k, v in dict(tp=2, fp=2, fn=4, tn=21, n=29, u=1).items():
        assert user_c[k] == v, f"口径 C 复现失败 {k}: 期望 {v}，得到 {user_c[k]}"
    for k, v in {"precision": 0.500, "recall": 0.333,
                 "accuracy": 0.793, "kappa": 0.281}.items():
        assert abs(user_c[k] - v) < 0.001, f"口径 C 复现失败 {k}: 期望 {v}，得到 {user_c[k]:.4f}"

    for k, v in dict(tp=2, fp=2, fn=4, tn=22, n=30, u=0).items():
        assert final[k] == v, f"口径 D 校验失败 {k}: 期望 {v}，得到 {final[k]}"
    for k, v in {"precision": 0.500, "recall": 0.333,
                 "accuracy": 0.800, "kappa": 0.286}.items():
        assert abs(final[k] - v) < 0.001, f"口径 D 校验失败 {k}: 期望 {v}，得到 {final[k]:.4f}"

    change_lines = "\n".join(
        f"| {no} | {rows[int(no)-1]['human_verdict'].strip().upper()} | "
        f"{FINAL_VARIANT[no][0]} | {FINAL_VARIANT[no][1] or '—'} | {FINAL_VARIANT[no][2]} |"
        for no in sorted(FINAL_VARIANT, key=int)
    )

    report = f"""# 第 4 步 A · 裁决后复算报告（**已定稿**）

> **口径声明**：所有指标是「规则 v2 与**人机协作参考标签**的一致度」，
> **不是准确率、不是真值校验、不是评分者间信度**。参考标签由人机协作产生，
> 无第二位标注者盲审、无第三人仲裁。详见 `output/LABEL_PROVENANCE.md`。
>
> 本表为**内存副本复算**：`output/annotation_sheet_round2.csv` 与所有既有报告
> **均未改动**；样本量小、分层抽样不可外推全库。
>
> **定稿裁决（2026-11-21）**：X5 采用口径 C 的处理（台账 Y / 统计 N）、
> X1 补证后结案由 U 改判 N、B2/B3 保持候选 → 最终采用**口径 D**。

---

## 1. 主结果（最终采用 · 口径 D）

| 指标 | 数值 |
|---|---|
| 混淆矩阵 TP / FP / FN / TN | **{final['tp']} / {final['fp']} / {final['fn']} / {final['tn']}** |
| 有效样本 N | **{final['n']}**（U = {final['u']}，无待仲裁样本） |
| Precision（一致率） | **{final['precision']:.3f}** |
| Recall（一致率） | **{final['recall']:.3f}** |
| Accuracy（一致率） | **{final['accuracy']:.3f}** |
| Cohen's Kappa | **{final['kappa']:.3f}** |

分箱明细（标注表行号）：

| 箱 | 行号 |
|---|---|
| TP（规则报 · 标签 Y） | {', '.join(final['tp_rows']) or '—'} |
| FP（规则报 · 标签 N） | {', '.join(final['fp_rows']) or '—'} |
| FN（规则未报 · 标签 Y） | {', '.join(final['fn_rows']) or '—'} |
| TN（规则未报 · 标签 N） | {', '.join(final['tn_rows']) or '—'} |

与第 1 轮训练集的对照（训练 / 独立样本）：

| | 第 1 轮（训练，N=30） | 第 2 轮（独立样本，N={final['n']}） | 泛化差距 |
|---|---|---|---|
| Precision | 1.000 | {final['precision']:.3f} | {final['precision']-1:+.3f} |
| Kappa | 1.000 | {final['kappa']:.3f} | {final['kappa']-1:+.3f} |

> 训练集 1.000 是「拿同一批样本自己考自己」，不能作为结论；
> 独立样本的 {final['precision']:.3f} / {final['kappa']:.3f} 才是可对外陈述的数字。

---

## 2. 裁决映射表（内存副本，可逐行审阅）

| 行号 | 原值 | 改判 | 缺陷标记 | 依据 |
|---|---|---|---|---|
{change_lines}

**未列出的 23 行保持标注表原值不变。**
`annotation_sheet_round2.csv` 中第 21、30 行仍为 `U`、第 11 行仍为 `Y`；
本表所有改判只存在于复算的内存副本中，**标注表 CSV 一字未改**。

---

## 3. 四种口径对照与裁决记录

| 口径 | TP/FP/FN/TN | N / U | Precision | Recall | Accuracy | Kappa |
|---|---|---|---|---|---|---|
| A 原始（未裁决） | {fmt(base)} |
| B 裁决·文字口径（X5 保留 Y） | {fmt(textual)} |
| C 口径 C（X5 按 N，X1 仍 U） | {fmt(user_c)} |
| **D 口径 D = C + X1 结案（最终采用）** | **{fmt(final)}** |

### 已确认的口径区分（原「需你确认」事项已结案）

主结果只有在 **第 25 行（X5）按 `N` 处理**时才成立；而 X5 同时按定稿裁决
**保留在缺陷台账中为 B 类候选（Y）**。定稿处理如下：

- **台账口径**：X5 = B 类候选（保留 Y），记录「图片身份/顺序约束未被验收」这一缺陷；
- **统计口径**：X5 = N，理由是「B 类候选尚未端到端确认（不安装 `python-pptx`）」，
  在一致度计算中不把未确认候选计入 Y；
- 两者**有意区分并已在台账、规范、本报告中显式声明**，不是遗漏或计算错误。
- 第 6 行（X3）同为 B 类候选、在 FN 中按 Y 计入，与 X5 的处理不同：
  这是「参考标签原判 Y + 撤销 A 后换列 B」与「参考标签原判 Y 但整条改判 N」的差别，
  保留原始裁决轨迹，不做追溯性统一。

> 若未来把 B2/B3 端到端升格为「已确认」，应同时重算本表，并说明口径变化。

---

## 4. X1 顺序补证结果（已结案）

X1 的源文件顺序补证见 `output/evaluator_evidence.md` 第 3.1 节：

1. `thunderbird.profile.tar.gz` → `Notes` mbox → 邮件 **Lecture Document** → 附件 `lecture-notes.docx`；
2. docx 内 `word/media/image1.png / image2.png / image3.png`，在 `word/document.xml`
   中按 `rId4 → rId5 → rId6` 依次被引用 → **正文出现顺序唯一**；
3. 金标 `1_gold.png / 2_gold.png / 3_gold.png` 与上述三张图**字节完全相同**
   （sha256 前 16 位 `4f584d4b99a2ae04 / d5bfc6194ab0ff2f / 4e3e2dd11a39dcb6`，
   大小 30882 / 40335 / 27669 字节）。

**结案结论**：源文档自然给出唯一顺序，且 evaluator 的固定映射与之对应；
「指令未规定编号顺序 → 多个合理做法只认一个」的 **A 类推断不成立**。
X1 由 `U` **改判 `N`**，A 待补证据撤销，计入 TN。
标注表 CSV 原值仍为 `Y`（人机协作参考标签），结案裁决覆盖之，
这正体现「不把参考标签当真值」的方法原则。

---

## 5. 定稿状态

| 事项 | 裁决 |
|---|---|
| X5 统计口径 | 采用 C（台账 Y / 统计 N），差异已显式声明 |
| X1 | 补证后结案，U → N，采用口径 D |
| B2 / B3 | **保持候选**，不安装 `python-pptx`、不做端到端升格，证据边界如实保留 |
| 标注表与既有报告 | 全部原值不动 |

脚本内置两组断言：口径 C 与最终口径 D 的统计值均已校验。
"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8", newline="\n")

    print("=" * 66)
    print("第 4 步 A · 裁决后复算（已定稿 · 内存副本，未改动标注表与既有报告）")
    print("=" * 66)
    print(f"最终口径 D: TP/FP/FN/TN = {final['tp']}/{final['fp']}/{final['fn']}/{final['tn']}")
    print(f"            N={final['n']}  U={final['u']}")
    print(f"            Precision {final['precision']:.3f} | Recall {final['recall']:.3f} "
          f"| Accuracy {final['accuracy']:.3f} | Kappa {final['kappa']:.3f}")
    print("-" * 66)
    print("口径对照（审计轨迹）：")
    for name, m in [("A 原始", base), ("B 文字口径", textual),
                    ("C X5按N", user_c), ("D 最终", final)]:
        print(f"  {name:<12} {fmt(m)}")
    print("-" * 66)
    print("断言 1 通过：口径 C = 2/2/4/21、0.500/0.333/0.793/0.281")
    print("断言 2 通过：口径 D = 2/2/4/22、0.500/0.333/0.800/0.286")
    print(f"已生成：{OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
