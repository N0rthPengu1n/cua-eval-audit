"""从 OSWorld 任务中构建可复现的领域分层审计子集。"""
from __future__ import annotations

import csv
import glob
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT / "output" / "rule_v2" / "task_profile.csv"
JSON_BASE = ROOT / "data" / "osworld" / "evaluation_examples" / "examples"
SHEET1 = ROOT / "output" / "annotation_sheet.csv"
SHEET2 = ROOT / "output" / "annotation_sheet_round2.csv"
OUT_CSV = ROOT / "output" / "subset_80.csv"
OUT_MD = ROOT / "output" / "subset_design.md"

SEED = 77
TARGET = 80

DOMAIN = {
    "chrome": "网页检索",
    "gimp": "图像编辑",
    "libreoffice_calc": "表格数据",
    "libreoffice_impress": "演示文稿",
    "libreoffice_writer": "文档写作",
    "vscode": "编程开发",
    "vs_code": "编程开发",
    "multiapps": "跨应用协同",
    "multi_apps": "跨应用协同",
    "os": "系统设置",
    "vlc": "多媒体",
    "thunderbird": "邮件通讯",
    "base_setup": "环境配置",
}

EXCLUDE = {
    "c7c1e4c3": "A1 已确认：教授邮箱多值未限定 × 全表精确比对",
    "59155008": "A2 已确认：similar names 多解 × 唯一 URL",
    "3e3fc409": "A3 已确认：IMDb Top 30 时点/口径未限定 × 固定金标表",
    "b5062e3e": "A4 已确认：首位作者 affiliation 多单位 × exact_match",
    "d1acdb87": "A5 已确认：餐馆分店/电话/网站多值 × 唯一取值",
    "869de13e": "A6 已确认：桌面归类边界无定义 × 固定文件名清单",
    "42f4d1c7": "B1 已确认：要求写脚本但无脚本检查项",
    "c82632a4": "B2 候选：要求指定图片 none.png，评分器不比对图片内容",
    "bf4e9888": "B3 候选：要求 pic1–6 按序，评分器不比对图片身份/顺序",
}

RUBRIC = {
    "compare_table": "表结构与单元格值比对；先查 config 初始工作簿，再核对 expected 金标表的 sheet/range/rule 类型",
    "compare_pptx_files": "逐选项检查清单；必须查 options 里 examine_* 的开关与 slides.py 源码语义，不得按字面推断",
    "exact_match": "唯一值精确比对；确认 expected 是否只接受一个答案",
    "is_expected_active_tab": "唯一 URL / 标签页比对；确认是否有其它合理目标",
    "compare_image_list": "图片列表与金标逐一对应；确认 query_list 的命名与顺序约束",
    "compare_animated_images": "时间轴 SSIM；确认时长容差，与帧率/帧数无关",
    "infeasible": "特殊题型：预期「无法完成」，本来就没有标准答案，不按缺陷处理",
}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = read_csv(PROFILE)
    assert len(rows) == 368, f"抽样框应为 368 道，实际 {len(rows)}"

    excluded, pool = [], []
    for r in rows:
        tid = r["task_id"]
        hit = next((reason for pre, reason in EXCLUDE.items() if tid.startswith(pre)), None)
        if hit:
            excluded.append((tid, hit))
        elif int(r["defect_count"] or 0) > 0:
            excluded.append((tid, "v2 规则命中但尚未完成人工复核，暂不纳入"))
        else:
            pool.append(r)

    by_domain: dict[str, list[dict]] = defaultdict(list)
    for r in pool:
        dom = DOMAIN.get(r["app"], "其它")
        by_domain[dom].append(r)

    assert len(by_domain) == 11, f"应为 11 个领域，实际 {len(by_domain)}: {list(by_domain)}"

    n_pool = len(pool)
    raw = {d: TARGET * len(v) / n_pool for d, v in by_domain.items()}
    quota = {d: max(1, int(raw[d])) for d in by_domain}
    rem = TARGET - sum(quota.values())
    order = sorted(
        (d for d in by_domain if int(raw[d]) >= 1),
        key=lambda d: raw[d] - int(raw[d]), reverse=True,
    )
    while rem > 0 and order:
        progressed = False
        for d in order:
            if rem <= 0:
                break
            if quota[d] < len(by_domain[d]):
                quota[d] += 1
                rem -= 1
                progressed = True
        if not progressed:
            break
    for d in sorted(by_domain):
        while rem > 0 and quota[d] < len(by_domain[d]):
            quota[d] += 1
            rem -= 1

    rng = random.Random(SEED)
    reviewed = {}
    for sh, tag in ((SHEET1, "round1"), (SHEET2, "round2")):
        for x in read_csv(sh):
            reviewed[x["task_id"]] = (tag, x["human_verdict"].strip().upper())

    json_path = {}
    for f in glob.glob(str(JSON_BASE / "**" / "*.json"), recursive=True):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            json_path[d.get("id", "")] = str(Path(f).relative_to(ROOT)).replace("\\", "/")
        except Exception:
            continue

    picked: list[dict] = []
    for dom in sorted(by_domain):
        items = list(by_domain[dom])
        rng.shuffle(items)
        picked.extend(items[: quota[dom]])

    rng.shuffle(picked)
    for i, r in enumerate(picked, 1):
        r["_no"] = i
        r["_domain"] = DOMAIN.get(r["app"], "其它")

    fields = [
        "no", "task_id", "domain_zh", "app", "instruction", "instruction_words",
        "config_steps", "evaluator_func", "risk_tags", "reviewed_round",
        "reference_verdict", "quality_flag", "rubric_hint", "source_json",
    ]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in picked:
            tid = r["task_id"]
            rr, verdict = reviewed.get(tid, ("", ""))
            fn = r["evaluator_func"] or ""
            hint = RUBRIC.get(fn, "查 evaluator.func 与 options / expected.rules，按评分器源码确认实际检查项")
            if r["risk_tags"]:
                hint += "；注意风险标记：" + r["risk_tags"]
            src = json_path.get(tid, "")
            r["_dir_mismatch"] = bool(src and src.split("/")[-2] != r["app"])
            w.writerow({
                "no": r["_no"], "task_id": tid, "domain_zh": r["_domain"], "app": r["app"],
                "instruction": r["instruction"], "instruction_words": r["instruction_words"],
                "config_steps": r["config_steps"], "evaluator_func": fn,
                "risk_tags": r["risk_tags"], "reviewed_round": rr,
                "reference_verdict": verdict,
                "quality_flag": "reviewed_ok" if rr else "not_reviewed",
                "rubric_hint": hint,
                "source_json": src,
            })

    dist = Counter(r["_domain"] for r in picked)
    q_lines = "\n".join(
        f"| {d} | {len(by_domain[d])} | {len(by_domain[d])/n_pool*100:.1f}% | {quota[d]} | {dist[d]} |"
        for d in sorted(by_domain)
    )
    ex_lines = "\n".join(f"| `{t[:8]}…` | {why} |" for t, why in excluded)
    risk_cnt = Counter(t for r in picked for t in (r["risk_tags"] or "").split(";") if t)
    risk_lines = "\n".join(f"| {k} | {v} |" for k, v in risk_cnt.most_common()) or "| （无） | 0 |"
    rev_cnt = sum(1 for r in picked if r["task_id"] in reviewed)

    md = f"""# 领域分层审计子集设计说明（第 4 步 B · 已定稿）

> **定位声明**：本子集**不是新建评测集**。80 道题目 100% 来自
> `xlang-ai/OSWorld` 的 `evaluation_examples/`（Apache-2.0，368 道公开评测任务）。
> 本项目做的是**领域分层抽样 + 质量审计标记继承 + 评测接入口径设计**。
> 对外表述统一为「基于 OSWorld 公开任务组建领域分层审计子集」，不得写作「构建评测集」。
> 标注来源与统计口径见 `output/LABEL_PROVENANCE.md`。

---

## 1. 设计目标

子集按 11 个领域分层，保留每个任务的评分器、风险标记与复核状态。显式纳入与排除标准使样本可复现，并支持按领域和评分器分别分析结果。

---

## 2. 抽样框与纳入 / 排除标准

| 项 | 内容 |
|---|---|
| 抽样框 | `output/rule_v2/task_profile.csv`，全量 **{len(rows)}** 道 |
| 排除数 | **{len(excluded)}** 道（逐条见下表） |
| 可用池 | **{n_pool}** 道 |
| 目标样本量 | **{TARGET}** 道 |
| 随机种子 | `{SEED}`（`random.Random`，可复现） |
| 分层变量 | `app` → 11 个中文领域（归并 `vs_code→编程开发`、`multi_apps→跨应用协同`） |
| 配额方法 | 按框内比例分配，最大余数法调整，每层 ≥ 1 |

**排除规则**（两类，均为显式 ID，不靠模糊匹配）：

1. 台账 v1.0 中**已确认或候选的缺陷题**（A1–A6、B1、B2、B3）；
2. 规则 v2 命中但**尚未完成复核**的题。

排除清单：

| task_id | 排除理由 |
|---|---|
{ex_lines}

> 撤销归因后改判 `N` 的题（X1 `46407397`、X2 `2fe4b718`、X4 `15aece23`）
> 与两条 `U` 消解题（21 `185f29bd`、30 `f9584479`）**不排除**，
> 因为它们按定稿裁决已不属缺陷；其中被复核过的会在 `reviewed_round` 标记。

---

## 3. 领域配额表

| 中文领域 | 框内题数 | 框内占比 | 配额 | 实际抽中 |
|---|---|---|---|---|
{q_lines}
| **合计** | **{n_pool}** | **100.0%** | **{sum(quota.values())}** | **{len(picked)}** |

> `vlc`（多媒体）框内仅 4 道，按「每层 ≥ 1」保底；其余领域按最大余数法分配。
> 因此**比例与全库不完全一致** —— 这是分层保底抽样的必然结果，
> 不能据此推断全库各领域的缺陷率或难度分布。

---

## 4. 字段字典（`output/subset_80.csv`）

| 字段 | 含义 |
|---|---|
| `no` | 子集内序号（1–{len(picked)}） |
| `task_id` | OSWorld 原始任务 ID，用于回查 |
| `domain_zh` | 11 个中文领域标签 |
| `app` | 原始 app 字段 |
| `instruction` | 原始英文题目（**未改动**） |
| `instruction_words` / `config_steps` | 第 1 步画像的衍生指标 |
| `evaluator_func` | 打分器函数名（可能是组合） |
| `risk_tags` | 第 1 步扫描出的风险标记（不是缺陷） |
| `reviewed_round` | 该题是否在 round1 / round2 复核样本中出现 |
| `reference_verdict` | 两轮**人机协作参考标签**原值（Y/N/U），**非真值** |
| `quality_flag` | `reviewed_ok`（已复核）/ `not_reviewed`（未复核） |
| `rubric_hint` | 按 `evaluator_func` 生成的验收口径读取提示 |
| `source_json` | 原始任务 JSON 的**实际**相对路径，供回查 `evaluator.expected` / `config`。注意 OSWorld 把部分跨应用任务放在 `multi_apps/`、`vscode` 对应 `vs_code/`，故路径目录可能与 `app` 字段不同；子集内 {sum(1 for r in picked if r.get('_dir_mismatch'))} 道存在该情况，属原始数据组织方式，不是抽样错误 |

子集内**已复核 {rev_cnt} 道**，其余 {len(picked)-rev_cnt} 道为未复核样本。

---

## 5. 子集内的风险标记分布

| 风险标记 | 题数 |
|---|---|
{risk_lines}

> 风险标记是「建议人工读一遍」的提示，**不是缺陷判定**（见《标注规范 v1.1》3.6）。
> `EXTERNAL_DEPENDENCY` 占比高是因为多数题的 `source` 指向外部网页；
> 它与官方 `possibility_of_env_change` 标注不匹配，是第 1 步报告里的一个发现。

---

## 6. 评测接入口径（评测方法设计）

字段映射建议（接入 EvalScope / AgentNetBench 之类的横评框架时）：

| 子集字段 | 框架字段 | 说明 |
|---|---|---|
| `instruction` | `prompt` / `instruction` | 原样传入，不翻译、不改写 |
| `source_json` → `config` | `init_state` | 初始文件/环境按 OSWorld 原配置加载 |
| `source_json` → `evaluator.expected` | `gold_answer` | 金标答案与打分器规则 |
| `evaluator_func` + `rubric_hint` | `metric` | 按 func 选择打分器；**不要统一成一个指标** |
| `domain_zh` | `subset` / `group` | 分组出报告，观察领域间差异 |
| `risk_tags` / `quality_flag` | `metadata` | 分层分析时作为协变量，不参与打分 |

**三条必须遵守的口径**：

1. 不同 `evaluator_func` 的分数**不可直接横向相加**（123 种打分器、口径各异），
   分组统计时应按领域 × func 分别出指标；
2. 跑 baseline 后若分数异常，先按台账 v1.0 的 A/B 判据排查「打分器误判」，
   不要直接归因于模型能力；
3. 失败样本回流时记录「grounding 错 / 规划错 / **验收误判**」三类，
   只有验收误判才允许修订 evaluator，且需保留跨版本可比性（OSWorld-Verified 的原则）。

---

## 7. 限制（对外表述必须带上）

1. **不是新建评测集**，题目全部来自 OSWorld，Apache-2.0，须注明出处。
2. **未跑任何 baseline**：本步骤只完成子集组建与设计，没有模型横评结果，不能写「驱动模型效果提升 X%」。
3. **分层保底抽样不可外推**：80 道不是等概率抽样，不能据此估计全库缺陷率或领域难度。
4. **参考标签非独立人工标注**：`reference_verdict` 是人机协作产生的参考标签，非真值；详见 `LABEL_PROVENANCE.md`。
5. **`not_reviewed` 不等于没问题**：未被复核的题只是没有出现在两轮样本中，
   按《标注规范 v1.1》第 7 节，自动规则「没报出来」不等于「没问题」。
6. **未做中文改写**：题目保持 OSWorld 原英文；中文只用于领域分层标签。
   若后续要做中文 CUA 子集，需另立翻译与回译校验流程。

---

## 8. 复现

```bash
python step4b_subset.py
```

输出：`output/subset_80.csv`（{len(picked)} 行）、`output/subset_design.md`（本文件）。
仅用 Python 标准库；不改动 `data/osworld/` 中任何原始题目。
"""
    OUT_MD.write_text(md, encoding="utf-8", newline="\n")

    print("=" * 66)
    print(f"第 4 步 B：领域分层审计子集（seed={SEED}, 目标 {TARGET} 道）")
    print("=" * 66)
    print(f"抽样框 {len(rows)} → 排除 {len(excluded)} → 可用池 {n_pool} → 抽中 {len(picked)}")
    print(f"其中已复核 {rev_cnt} 道 / 未复核 {len(picked)-rev_cnt} 道")
    print("-" * 66)
    for d in sorted(by_domain):
        print(f"  {d:<10} 框内 {len(by_domain[d]):>3}  配额 {quota[d]:>2}  抽中 {dist[d]:>2}")
    print("-" * 66)
    print(f"已生成：{OUT_CSV.relative_to(ROOT)}")
    print(f"已生成：{OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
