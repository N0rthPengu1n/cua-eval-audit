"""生成 OSWorld 任务画像、风险标签和待复核任务清单。"""
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
OUT.mkdir(parents=True, exist_ok=True)

VAGUE = re.compile(
    r"\b(some|several|a few|appropriate|proper|better|improve|nice|reasonable|"
    r"usually|typical|etc|and so on|as you like|relevant|suitable|similar|"
    r"a couple|any|maybe|if possible)\b",
    re.I,
)
STRICT_HINT = (
    "exact_match", "compare_table", "compare_pptx_files", "compare_docx_files",
    "compare_text_file", "check_list", "check_config_status", "is_expected",
    "check_direct_json_object", "compare_pdfs",
)
URL_RE = re.compile(r"https?://", re.I)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", text or ""))


def func_name(ev: dict) -> str:
    f = (ev or {}).get("func")
    if isinstance(f, list):
        return "|".join(str(i) for i in f)
    return str(f or "")


def load_tasks():
    for p in sorted(DATA.rglob("*.json")):
        try:
            yield p, json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[跳过] {p.name}: {e}")


rows = []
for path, d in load_tasks():
    ev = d.get("evaluator") or {}
    instr = (d.get("instruction") or "").strip()
    src = str(d.get("source") or "").strip()
    cfg = d.get("config")
    fn = func_name(ev)
    n_words = word_count(instr)
    env_risk = str(d.get("possibility_of_env_change") or "").strip().lower()

    defects, risks = [], []
    is_infeasible = "infeasible" in fn

    if not instr:
        defects.append("NO_INSTRUCTION")
    if instr and n_words < 5:
        defects.append("TOO_SHORT_INSTRUCTION")
    if instr and n_words > 60:
        defects.append("OVERLONG_INSTRUCTION")
    if not cfg:
        defects.append("NO_INIT_STATE")
    if not ev or not fn:
        defects.append("NO_EVALUATOR")
    if ev and not is_infeasible and not (ev.get("expected") or ev.get("result")):
        defects.append("NO_GOLD_ANSWER")
    if fn and any(h in fn for h in STRICT_HINT) and VAGUE.search(instr):
        defects.append("VAGUE_X_STRICT")

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
        "related_apps": ",".join(d.get("related_apps") or []),
        "instruction": instr,
        "instruction_words": n_words,
        "source": src,
        "source_is_url": int(bool(URL_RE.search(src))),
        "config_steps": len(cfg) if isinstance(cfg, list) else 0,
        "evaluator_func": fn,
        "env_risk": env_risk or "unknown",
        "has_hint": int(bool(d.get("hint"))),
        "defect_tags": ";".join(defects),
        "risk_tags": ";".join(risks),
        "defect_count": len(defects),
        "risk_count": len(risks),
        "norm_instruction": re.sub(r"\W+", " ", instr.lower()).strip(),
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
    })

dup = Counter(r["norm_instruction"] for r in rows if r["norm_instruction"])
for r in rows:
    if r["norm_instruction"] and dup[r["norm_instruction"]] > 1:
        r["defect_tags"] = ";".join(filter(None, [r["defect_tags"], "DUP_INSTRUCTION"]))
        r["defect_count"] += 1

if not rows:
    raise SystemExit("没有读到任务 JSON，请确认 data/osworld/evaluation_examples/examples/ 是否存在。")

fields = [k for k in rows[0].keys() if k != "norm_instruction"]

with (OUT / "task_profile.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

issues = sorted([r for r in rows if r["defect_count"] > 0],
                key=lambda r: (-r["defect_count"], -r["risk_count"], r["app"]))
with (OUT / "issues.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(issues)

n = len(rows)
app_cnt = Counter(r["app"] for r in rows)
func_cnt = Counter(t for r in rows for t in r["evaluator_func"].split("|") if t)
func_calls = sum(func_cnt.values())
multi_func_n = sum(1 for r in rows if "|" in r["evaluator_func"])
env_cnt = Counter(r["env_risk"] for r in rows)
defect_cnt = Counter(t for r in rows for t in r["defect_tags"].split(";") if t)
risk_cnt = Counter(t for r in rows for t in r["risk_tags"].split(";") if t)
wc = [r["instruction_words"] for r in rows]
cfg_steps = [r["config_steps"] for r in rows]
url_n = sum(r["source_is_url"] for r in rows)
flagged = len(issues)


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0


def bar(cnt, top=12, denom=None):
    denom = denom or n
    mx = max(cnt.values()) or 1
    return "\n".join(
        f"| {k or '(空)':<26} | {v:>4} | {v / denom * 100:>5.1f}% | {'█' * max(1, round(v / mx * 18))} |"
        for k, v in cnt.most_common(top)
    )


DEFECT_DESC = {
    "NO_INSTRUCTION": "题目为空",
    "TOO_SHORT_INSTRUCTION": "题目少于 5 个词，信息可能不全",
    "OVERLONG_INSTRUCTION": "题目超过 60 个词，多重约束易生歧义",
    "NO_INIT_STATE": "缺少初始环境配置，任务无法复现",
    "NO_EVALUATOR": "缺少打分器",
    "NO_GOLD_ANSWER": "缺少标准答案（infeasible 题型除外）",
    "VAGUE_X_STRICT": "题目用模糊措辞，打分器却是精确匹配（OSWorld-Verified 修复的核心问题）",
    "DUP_INSTRUCTION": "题目重复，虚高评测集覆盖度",
}
RISK_DESC = {
    "EXTERNAL_DEPENDENCY": "题目来源为外部网页，改版或反爬会让分数漂移",
    "ENV_CHANGE_RISK": "官方标注的环境变化风险不为 low",
    "HAS_HINT": "需要额外提示才能做，题目不够自足",
    "NETWORK_SPECIAL": "需要代理或固定 IP 等特殊网络配置",
    "INFEASIBLE_TASK": "「不可能完成」特殊题型，无标准答案，按返回 FAIL 计分",
}

report = f"""# 第 1 步产出：CUA 评测集数据体检报告

数据源：`xlang-ai/OSWorld` → `evaluation_examples/examples/`，共 **{n}** 道评测任务（Apache-2.0）。
生成方式：`python step1_profile.py`（零第三方依赖，可重复运行）。

## 一句话结论

在 {n} 道题里，按预设规则扫出 **{flagged} 道（{flagged / n * 100:.1f}%）存在至少一项缺陷**，
**{sum(1 for r in rows if r['risk_tags'])} 道（{sum(1 for r in rows if r['risk_tags']) / n * 100:.1f}%）带有环境/复现风险**。
这些就是下一步要人工复核的候选坏题。

## 1. 数据总览

| 指标 | 数值 |
|---|---|
| 任务总数 | {n} |
| 覆盖应用数 | {len(app_cnt)} |
| 打分器类型数 | {len(func_cnt)} 种（共被调用 {func_calls} 次） |
| 使用多个打分器的任务 | {multi_func_n} |
| 题目词数（中位数 / 最短 / 最长） | {median(wc)} / {min(wc)} / {max(wc)} |
| 初始配置步数（中位数） | {median(cfg_steps)} |
| source 为外部 URL 的任务 | {url_n}（{url_n / n * 100:.1f}%） |
| 至少一项缺陷 | {flagged}（{flagged / n * 100:.1f}%） |

## 2. 应用分布（这就是「领域分层」的雏形）

| 应用 | 题数 | 占比 | |
|---|---|---|---|
{bar(app_cnt, 15)}

## 3. 打分器类型 Top 12（这就是「评测方法」的分布）

共 {len(func_cnt)} 种打分器、被调用 {func_calls} 次；{multi_func_n} 道题叠加使用多个打分器。下表占比以调用次数为分母。

| 打分器 | 调用次数 | 占比 | |
|---|---|---|---|
{bar(func_cnt, 12, func_calls)}

## 4. 环境漂移风险（官方标注）

| 等级 | 题数 | 占比 | |
|---|---|---|---|
{bar(env_cnt, 8)}

## 5. 质量红线扫描结果

### 缺陷类（明确要修）

| 标签 | 题数 | 占比 | 含义 |
|---|---|---|---|
{chr(10).join(f"| `{k}` | {v} | {v / n * 100:.1f}% | {DEFECT_DESC.get(k, '')} |" for k, v in defect_cnt.most_common()) or '| （无） | | | |'}

### 风险类（影响复现与分数稳定性）

| 标签 | 题数 | 占比 | 含义 |
|---|---|---|---|
{chr(10).join(f"| `{k}` | {v} | {v / n * 100:.1f}% | {RISK_DESC.get(k, '')} |" for k, v in risk_cnt.most_common()) or '| （无） | | | |'}

> 注意：这些是规则筛出的待复核样本，不等于已确认的问题。

## 6. 审计观察

1. 题库高度依赖外部网页（{url_n / n * 100:.1f}% 的 source 是 URL），而官方标注 `env_change != low` 的只有
   {env_cnt.get('medium', 0) + env_cnt.get('high', 0)} 道 —— **外部依赖比例与环境风险标注明显不匹配**，
   说明环境漂移是一个被低估的质量维度。
2. `VAGUE_X_STRICT`（模糊指令撞上精确打分器）命中 {defect_cnt.get('VAGUE_X_STRICT', 0)} 道，
   对应 OSWorld-Verified 修复的「指令歧义 / 验证逻辑」两类问题：题目可以有多种合理解，打分器只认一种。
3. 打分器多达 {len(func_cnt)} 种、{func_calls} 次调用，其中 `compare_table` 被调用 {func_cnt.get('compare_table', 0)} 次 ——
   **不同题型用不同打分口径**，横向比较分数前必须先统一指标定义，这是「评测方法设计」的第一道关。

## 7. 规则局限

第一版规则曾把 26 道 `infeasible` 题误报为「缺少标准答案」。这类题**故意**没有标准答案，
评测逻辑是「agent 主动返回 FAIL 即得分」——如果不了解题型语义，纯靠字段是否为空去判断，就会得出错误结论。
修正后已把该题型单独标为 `INFEASIBLE_TASK`，不计入缺陷。

同理，第一版把 `config` 中任意 http 链接都算作外部依赖，命中率高达 96%，失去区分度，
因此收窄为只看 `source` 字段。

> 质量规则必须结合领域语义校准，不能只依据字段是否为空。

## 文件说明

- `output/task_profile.csv`：全量 {n} 行指标表，可直接用 Excel / pandas 继续分析
- `output/issues.csv`：{flagged} 行可疑任务，按缺陷数降序
- `output/summary.md`：本文件
"""

(OUT / "summary.md").write_text(report, encoding="utf-8")

print("=" * 62)
print(f"第 1 步完成：共扫描 {n} 道评测任务")
print("=" * 62)
print(f"覆盖应用 {len(app_cnt)} 个 / 打分器 {len(func_cnt)} 种")
print(f"题目词数中位数 {median(wc)}，外部 URL 依赖 {url_n} 道（{url_n / n * 100:.1f}%）")
print(f"扫出可疑任务 {flagged} 道（{flagged / n * 100:.1f}%）")
print("-" * 62)
print("缺陷 Top 5：")
for k, v in defect_cnt.most_common(5):
    print(f"  {k:<26} {v:>4} 道  ({v / n * 100:.1f}%)")
print("-" * 62)
print("已生成：")
print("  output/task_profile.csv")
print("  output/issues.csv")
print("  output/summary.md")
print("=" * 62)
