"""修订质量规则并比较 v1、v2 在第一轮参考标签上的结果。"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "osworld" / "evaluation_examples" / "examples"
OUT = ROOT / "output"
V2DIR = OUT / "rule_v2"
V2DIR.mkdir(parents=True, exist_ok=True)

VAGUE_V2 = re.compile(
    r"\b(appropriate|proper|better|improve|nice|reasonable|suitable|similar|"
    r"relevant|as you like|if possible|maybe)\b", re.I,
)
NEGATION_CTX = re.compile(
    r"\b(no|not|except|avoid|without|don't|do not|other than|rather than|"
    r"instead of)\b[^.]{0,45}$", re.I,
)
STRICT_HINT = (
    "exact_match", "compare_table", "compare_pptx_files", "compare_docx_files",
    "compare_text_file", "check_list", "check_config_status", "is_expected",
    "check_direct_json_object", "compare_pdfs",
)
FILE_MENTION = re.compile(
    r"\.(docx?|xlsx?|pptx?|pdf|csv|txt|json|png|jpe?g|mp3|mp4)"
    r"|\b(file|document|spreadsheet|presentation|folder|desktop|attachment)\b", re.I,
)
SETTING_HINT = re.compile(
    r"\b(bluetooth|battery|default|theme|wallpaper|brightness|volume|wifi|"
    r"notification|search results|extension|language|display|install|"
    r"percentage|player|python ?4)\b", re.I,
)
AMBIGUOUS_ENTITY = re.compile(
    r"\b(e-?mail addresses?|contact information|phone numbers?|mailing addresses?)\b", re.I,
)
LIMITER = re.compile(r"\b(primary|official|institutional|exactly|the one shown|specified)\b", re.I)
URL_RE = re.compile(r"https?://", re.I)

CHANGES = [
    ("OVERLONG_INSTRUCTION", "缺陷 → 风险提示 LONG_INSTRUCTION_REVIEW",
     "8/8 全误报。长 ≠ 歧义；词数无法判断多个要求是否冲突，降级为「必须人工读题」的提示。",
     "第 1/4/5/8/14/15/19/21/30 行 note"),
    ("NO_INIT_STATE", "收窄触发条件",
     "8/8 全误报。新增 infeasible 排除、纯系统设置排除，并要求题目确实提到文件/文档。",
     "第 3/6/9/17/23/24/27/28 行 note"),
    ("VAGUE_X_STRICT", "精修词表 + 排除性语境",
     "2/8 命中，是唯一有效规则。移除 etc/some/any 等数量词，保留主观多解词；"
     "模糊词落在 no / except / don't 语境时不报。",
     "第 2/11/16/20/29 行 note（反例）；第 22 行（正例）"),
    ("AMBIGUOUS_TARGET_X_EXACT", "新增规则（经第二轮收窄）",
     "题目涉及「邮箱地址 / 联系信息」这类待填字段值，打分器精确比对、又没限定取哪个 → 可疑。"
     "初版只匹配 email，误报 10 道「email 作邮件对象」的题，故收窄为 email address / contact information。"
     "它还把参考标签判 Y 的第 12 行的归因从「some 是模糊词」修正为「多值实体未限定」。",
     "第 12 行 note + 全量核对 10 道新增误报"),
    ("EVALUATOR_COVERAGE_GAP", "不自动化，列入人工复核清单",
     "题目提出保留性约束但打分器没校验（第 1 行「不改无关空白区」）。"
     "字段规则无法可靠判定，做成自动红线只会制造新误报。",
     "第 1 行 note"),
]


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", text or ""))


def func_name(ev: dict) -> str:
    f = (ev or {}).get("func")
    return "|".join(str(i) for i in f) if isinstance(f, list) else str(f or "")


def is_strict(fn: str) -> bool:
    return bool(fn) and any(h in fn for h in STRICT_HINT)


def scan_v2():
    rows = []
    for p in sorted(DATA.rglob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[跳过] {p.name}: {e}")
            continue
        ev = d.get("evaluator") or {}
        instr = (d.get("instruction") or "").strip()
        src = str(d.get("source") or "").strip()
        cfg = d.get("config")
        fn = func_name(ev)
        n_words = word_count(instr)
        env_risk = str(d.get("possibility_of_env_change") or "").strip().lower()
        is_infeasible = "infeasible" in fn

        defects, risks = [], []

        if not instr:
            defects.append("NO_INSTRUCTION")
        if instr and n_words < 5:
            defects.append("TOO_SHORT_INSTRUCTION")
        if not ev or not fn:
            defects.append("NO_EVALUATOR")
        if ev and not is_infeasible and not (ev.get("expected") or ev.get("result")):
            defects.append("NO_GOLD_ANSWER")

        if instr and n_words > 60:
            risks.append("LONG_INSTRUCTION_REVIEW")

        if (not cfg and not is_infeasible
                and FILE_MENTION.search(instr) and not SETTING_HINT.search(instr)):
            defects.append("NO_INIT_STATE")

        if is_strict(fn):
            hits = [m for m in VAGUE_V2.finditer(instr)
                    if not NEGATION_CTX.search(instr[max(0, m.start() - 45):m.start()])]
            if hits:
                defects.append("VAGUE_X_STRICT")

            if AMBIGUOUS_ENTITY.search(instr) and not LIMITER.search(instr):
                defects.append("AMBIGUOUS_TARGET_X_EXACT")

        if URL_RE.search(src):
            risks.append("EXTERNAL_DEPENDENCY")
        if is_infeasible:
            risks.append("INFEASIBLE_TASK")
        if env_risk not in ("", "low"):
            risks.append("ENV_CHANGE_RISK")
        if d.get("hint"):
            risks.append("HAS_HINT")
        if d.get("proxy") or d.get("fixed_ip"):
            risks.append("NETWORK_SPECIAL")

        rows.append({
            "task_id": d.get("id", ""),
            "app": d.get("snapshot", ""),
            "instruction": instr,
            "instruction_words": n_words,
            "config_steps": len(cfg) if isinstance(cfg, list) else 0,
            "evaluator_func": fn,
            "defect_tags": ";".join(defects),
            "risk_tags": ";".join(risks),
            "defect_count": len(defects),
            "norm_instruction": re.sub(r"\W+", " ", instr.lower()).strip(),
        })

    dup = Counter(r["norm_instruction"] for r in rows if r["norm_instruction"])
    for r in rows:
        if r["norm_instruction"] and dup[r["norm_instruction"]] > 1:
            r["defect_tags"] = ";".join(filter(None, [r["defect_tags"], "DUP_INSTRUCTION"]))
            r["defect_count"] += 1
    return rows


def read_csv(path: Path):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"无法读取 {path}")


def confusion(rows, sheet, suspect_key):
    """在 30 条人工样本上算混淆矩阵与 Kappa"""
    by_id = {r["task_id"]: r for r in rows}
    tp = fp = fn = tn = 0
    for s in sheet:
        v = (s["human_verdict"] or "").strip().upper()
        if v not in ("Y", "N"):
            continue
        try:
            flagged = int(by_id.get(s["task_id"], {}).get(suspect_key) or 0) > 0
        except (TypeError, ValueError):
            flagged = False
        if flagged and v == "Y": tp += 1
        elif flagged and v == "N": fp += 1
        elif not flagged and v == "Y": fn += 1
        else: tn += 1
    n = tp + fp + fn + tn
    if not n:
        return dict(tp=0, fp=0, fn=0, tn=0, n=0, precision=0, recall=0, po=0, kappa=0)
    po = (tp + tn) / n
    p_rule = (tp + fp) / n
    p_human = (tp + fn) / n
    pe = p_rule * p_human + (1 - p_rule) * (1 - p_human)
    k = (po - pe) / (1 - pe) if (1 - pe) else 1.0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, n=n,
                precision=tp / (tp + fp) if (tp + fp) else 0,
                recall=tp / (tp + fn) if (tp + fn) else 0,
                po=po, kappa=k)


def main():
    v1 = read_csv(OUT / "task_profile.csv")
    v2 = scan_v2()
    sheet = read_csv(OUT / "annotation_sheet.csv")
    n = len(v2)

    fields = [k for k in v2[0].keys() if k != "norm_instruction"]
    with (V2DIR / "task_profile.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(v2)
    issues2 = sorted([r for r in v2 if r["defect_count"] > 0],
                     key=lambda r: -r["defect_count"])
    with (V2DIR / "issues.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(issues2)

    v1_flag = {r["task_id"] for r in v1 if int(r["defect_count"] or 0) > 0}
    v2_flag = {r["task_id"] for r in v2 if r["defect_count"] > 0}
    removed, added = sorted(v1_flag - v2_flag), sorted(v2_flag - v1_flag)
    kept = sorted(v1_flag & v2_flag)

    c1 = Counter(t for r in v1 for t in r["defect_tags"].split(";") if t)
    c2 = Counter(t for r in v2 for t in r["defect_tags"].split(";") if t)
    r2 = Counter(t for r in v2 for t in r["risk_tags"].split(";") if t)

    m1 = confusion(v1, sheet, "defect_count")
    m2 = confusion(v2, sheet, "defect_count")

    gold = [s for s in sheet if (s["human_verdict"] or "").strip().upper() == "Y"]
    gold_rows = []
    for s in gold:
        hit = next((r for r in v2 if r["task_id"] == s["task_id"]), None)
        gold_rows.append(f"| {s['no']} | `{s['task_id'][:8]}` | "
                         f"{'✅ 仍命中' if hit and hit['defect_count'] > 0 else '❌ 漏掉'} | "
                         f"{(hit or {}).get('defect_tags', '') or '—'} | {s['note'][:56]} |")

    change_lines = "\n".join(
        f"| `{a}` | {b} | {c} | {d} |" for a, b, c, d in CHANGES
    )
    tag_lines = "\n".join(
        f"| `{k}` | {c1.get(k, 0)} | {c2.get(k, 0)} | "
        f"{c2.get(k, 0) - c1.get(k, 0):+d} |"
        for k in sorted(set(c1) | set(c2))
    )
    risk_lines = "\n".join(
        f"| `{k}` | {v} |" for k, v in r2.most_common()
    )
    removed_lines = "\n".join(
        f"| `{t[:8]}` | {next((r['instruction'][:76] for r in v1 if r['task_id'] == t), '')} |"
        for t in removed[:8]
    ) or "| （无） | |"
    added_lines = "\n".join(
        f"| `{t[:8]}` | {next((r['instruction'][:76] for r in v2 if r['task_id'] == t), '')} |"
        for t in added[:8]
    ) or "| （无） | |"

    report = f"""# 第 3 步产出：质量规则 v1 → v2 修订与回测报告

> ⚠️ **口径更正（2026-11-21）**：数值保留不改动，「人工复核结论 / 真值 / 单标注者」
> 等表述已作废。参考标签为**人机协作产生**，非独立人工标注；所有指标为一致率。
> 详见 `output/LABEL_PROVENANCE.md`。

依据：`output/annotation_sheet.csv` 的 **30 条参考标签**（28 N / 2 Y / 0 U）
与 `output/agreement_report.md`（Precision {m1['precision']:.3f}、Kappa {m1['kappa']:.3f}）。
规则 v1 的完整产物保留在 `output/` 未改动，v2 产物在 `output/rule_v2/`。

## 一句话结论

规则 v1 报出 **{len(v1_flag)} 道**可疑题，人工抽样复核后 Precision 仅 **{m1['precision']:.3f}**、
Kappa **{m1['kappa']:.3f}** —— 三条字段规则里两条 0% 命中。
按人工结论修订后，v2 报出 **{len(v2_flag)} 道**（摘掉 {len(removed)} 道、新增 {len(added)} 道），
在 30 条样本上 Precision 升至 **{m2['precision']:.3f}**、Kappa 升至 **{m2['kappa']:.3f}**。

> ⚠️ 1.000 来自用于修订规则的同一批样本，只能作为训练集回测结果，不能代表泛化表现。
> 规则 v1 报出的 24 条抽样任务中，22 条被参考标签判为误报，说明字段规则必须经语义复核校准。

## 1. 规则变更清单（每一条都能追到人工标注证据）

| 规则 | 变更 | 理由 | 证据 |
|---|---|---|---|
{change_lines}

## 2. 全量 {n} 道题：标签数量变化

| 缺陷标签 | v1 | v2 | 变化 |
|---|---|---|---|
{tag_lines}

风险类（v2，只提示不判缺陷）：

| 风险标签 | 题数 |
|---|---|
{risk_lines}

> `LONG_INSTRUCTION_REVIEW` 从缺陷降为风险，是本次最重要的决策：
> 词数只能说明「需要人工读一遍」，不能说明「这道题有歧义」。
> 把无法自动判定的维度硬写成红线，只会产出大量无效工单。

## 3. 题目级别的增减

| 项目 | 数量 |
|---|---|
| v1 报、v2 仍报（保留） | {len(kept)} |
| v1 报、v2 摘掉（消除误报） | {len(removed)} |
| v1 没报、v2 新报 | {len(added)} |

被摘掉的题（示例）：

| task_id | 题目（截断） |
|---|---|
{removed_lines}

新增的题（示例）：

| task_id | 题目（截断） |
|---|---|
{added_lines}

> 「新增 {len(added)} 道」不等于「新增规则没用」：`AMBIGUOUS_TARGET_X_EXACT` 命中的题
> 原本就在 v1 名单里（被别的标签报过），它的作用是**把归因改对** ——
> 例如第 12 行（参考标签判 Y），v1 说它「有模糊词 some」，v2 说它「邮箱是多值实体却没限定取哪个」，
> 后者才是能直接拿去修题目的诊断。

## 4. 两道参考标签判 Y 的样本，v2 有没有守住

| 序号 | task_id | v2 结果 | 命中标签 | 人工复核理由 |
|---|---|---|---|---|
{chr(10).join(gold_rows) or '| （无） | | | | |'}

守住这两道是修订的底线：如果为了降低误报把规则改到连真问题都不报，
Precision 会好看、Recall 会塌掉，等于用「少报」粉饰指标。

## 5. 30 条样本上的回测

| 指标 | 规则 v1 | 规则 v2 | 说明 |
|---|---|---|---|
| TP / FP / FN / TN | {m1['tp']}/{m1['fp']}/{m1['fn']}/{m1['tn']} | {m2['tp']}/{m2['fp']}/{m2['fn']}/{m2['tn']} | 以 30 条人工标注为参照 |
| Precision | {m1['precision']:.3f} | {m2['precision']:.3f} | 报出来的里面真有问题的比例 |
| Recall | {m1['recall']:.3f} | {m2['recall']:.3f} | 真问题里被抓到的比例 |
| Accuracy | {m1['po']:.3f} | {m2['po']:.3f} | 与人工判断一致的比例 |
| Cohen's Kappa | {m1['kappa']:.3f} | {m2['kappa']:.3f} | 扣除碰巧一致 |

### 数字变漂亮 ≠ 规则变好（更重要的一段）

v2 只报 {len(v2_flag)} 道、比 v1 少 {len(v1_flag) - len(v2_flag)} 道，看起来「干净」了，
但代价是**规则变保守了，只覆盖能用字段判定的维度**：

- 你在第 1 行 note 里发现的「题目写了不要改无关空白区，打分器却完全不校验」，
  属于**约束—验收覆盖缺口**，v2 没有任何规则能抓到它（见变更清单第 5 行，故意不自动化）。
- 除两道已复核的样本外，v2 命中的其余 {max(0, len(v2_flag) - 2)} 道**尚未经过复核**，
  既可能是真问题，也可能是新一批误报。
- 没有任何自动规则能证明「没被报出来的题都是好的」。少报会让 Precision 好看，
  同时把 Recall 的分母（参考标签）里的错误藏在看不见的地方。

所以第 4 步的独立抽样复测不是锦上添花，而是这个项目能否自圆其说的必要条件。

## 6. 方法学限制

1. **这 30 条是训练集，不是测试集。** 规则 v2 正是照着这 30 条结论改的，
   再拿同一批样本算 Precision / Kappa 属于「自己考自己」，只能作方向性验证。
   要证明泛化，必须**另抽一批独立样本**（建议第 4 步分层再抽 30 条）做二次复核。
2. **标注口径不对称。** 人工 `Y/N` 回答的是「v1 的 `rule_tags` 那条标准是否成立」，
   而 v2 新增了 `AMBIGUOUS_TARGET_X_EXACT` 这一维度，两者不是同一把尺子。
   因此第 5 节的数字是**趋势**而非严格的可比指标。
3. **分层抽样不可外推。** 30 条里人为放入 24 条可疑题和 6 条对照组，
   不能据此估计「全题库有 X% 坏题」；只有全量扫描的命中率才有全库意义。
4. **参考标签非独立人工标注。** 标签由人机协作产生，与规则同源；无第二位标注者
   盲审、无第三人仲裁。Kappa 只度量「规则与参考标签的一致度」，不是评分者间信度。

## 7. 配套产出

- `annotation_guideline_v1.1.md`：《CUA 评测任务标注规范》，定义可复用的复核标准
  （定义 / 正例 / 反例 / 边界情况 / 人工复核清单）。
- `output/rule_v2/task_profile.csv`、`output/rule_v2/issues.csv`：v2 全量扫描结果。

## 8. 下一步

第 4 步：按领域分层组建中文评测子集（60–100 题），并从中**独立抽样**做第二轮复核，
验证规则 v2 在新样本上是否仍然有效 —— 这就补上了本节第 1 条的泛化证据。
第二轮请把 `output/rule_v2/issues.csv` 里尚未人工判断的 {max(0, len(v2_flag) - 2)} 道
作为必查项：它们数量少、优先级最高，正好用来检验「少报是否掩盖了漏判」。
"""

    (OUT / "rule_revision_report.md").write_text(report, encoding="utf-8")

    print("=" * 62)
    print("第 3 步完成：规则 v1 → v2 修订与回测")
    print("=" * 62)
    print(f"全量 {n} 道题：v1 命中 {len(v1_flag)} 道 → v2 命中 {len(v2_flag)} 道")
    print(f"  摘掉 {len(removed)} 道 / 新增 {len(added)} 道 / 保留 {len(kept)} 道")
    print("-" * 62)
    print(f"30 条样本回测： Precision {m1['precision']:.3f} → {m2['precision']:.3f}"
          f" | Kappa {m1['kappa']:.3f} → {m2['kappa']:.3f}")
    print("-" * 62)
    print("已生成：")
    print("  output/rule_revision_report.md")
    print("  output/rule_v2/task_profile.csv")
    print("  output/rule_v2/issues.csv")
    print("=" * 62)


if __name__ == "__main__":
    main()
