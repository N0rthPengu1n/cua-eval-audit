"""生成与第一轮零重叠的第二轮分层复核样本。"""
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
OUT = ROOT / "output"
SEED = 44
QUOTA_MUST = 4
QUOTA_RANDOM = 26

APP_ALIAS = {"vs_code": "vscode", "multiapps": "multi_apps"}
DOMAIN = {
    "chrome": "网页 / 信息检索",
    "gimp": "图像编辑",
    "libreoffice_calc": "表格 / 数据处理",
    "libreoffice_impress": "演示文稿",
    "libreoffice_writer": "文档写作",
    "vscode": "编程开发",
    "multi_apps": "跨应用协同",
    "os": "系统设置",
    "vlc": "多媒体",
    "thunderbird": "邮件 / 通讯",
    "base_setup": "环境配置",
}


def read_csv(path: Path):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"无法读取 {path}")


def norm_app(a: str) -> str:
    return APP_ALIAS.get(a, a)


def allocate(strata: dict, k: int) -> dict:
    """分层比例分配：每层至少 1 条，其余按池子大小用最大余数法分配，
    并保证不超过该层可用题数。"""
    names = list(strata)
    quota = {s: 1 for s in names}
    left = k - len(names)
    if left <= 0:
        return {s: min(1, len(strata[s])) for s in names}
    total = sum(len(v) for v in strata.values())
    raw = {s: left * len(strata[s]) / total for s in names}
    for s in names:
        quota[s] += int(raw[s])
    rest = k - sum(quota.values())
    for s in sorted(names, key=lambda x: raw[x] - int(raw[x]), reverse=True):
        if rest <= 0:
            break
        quota[s] += 1
        rest -= 1
    for s in names:
        while quota[s] > len(strata[s]):
            quota[s] -= 1
            donor = max((x for x in names if quota[x] < len(strata[x])),
                        key=lambda x: len(strata[x]), default=None)
            if donor is None:
                break
            quota[donor] += 1
    return quota


def main():
    r1 = read_csv(OUT / "annotation_sheet.csv")
    v2 = read_csv(OUT / "rule_v2" / "task_profile.csv")
    v1 = read_csv(OUT / "task_profile.csv")
    env_by_id = {r["task_id"]: r.get("env_risk", "") for r in v1}
    used = {r["task_id"] for r in r1}

    flagged = [r for r in v2 if int(r["defect_count"] or 0) > 0]
    must = [r for r in flagged if r["task_id"] not in used]
    if len(must) != QUOTA_MUST:
        print(f"[提示] 必查项实际 {len(must)} 条（预期 {QUOTA_MUST}），按实际值继续。")

    pool = [r for r in v2
            if int(r["defect_count"] or 0) == 0 and r["task_id"] not in used]
    strata = defaultdict(list)
    for r in pool:
        strata[norm_app(r["app"])].append(r)

    rng = random.Random(SEED)
    for s in strata:
        rng.shuffle(strata[s])
    quota = allocate(strata, QUOTA_RANDOM)
    random_rows = []
    for s, q in quota.items():
        random_rows.extend(strata[s][:q])

    rows = must + random_rows
    rng.shuffle(rows)

    fields = ["no", "task_id", "app", "stratum", "instruction", "instruction_words",
              "evaluator_func", "config_steps", "env_risk", "rule_tags",
              "rule_verdict", "human_verdict", "human_issue_type", "note"]
    records = []
    for i, r in enumerate(rows, 1):
        app = norm_app(r["app"])
        cnt = int(r["defect_count"] or 0)
        records.append({
            "no": i,
            "task_id": r["task_id"],
            "app": app,
            "stratum": DOMAIN.get(app, "其他"),
            "instruction": r["instruction"],
            "instruction_words": r["instruction_words"],
            "evaluator_func": r["evaluator_func"],
            "config_steps": r["config_steps"],
            "env_risk": env_by_id.get(r["task_id"], ""),
            "rule_tags": r["defect_tags"],
            "rule_verdict": "SUSPECT" if cnt > 0 else "CLEAN",
            "human_verdict": "",
            "human_issue_type": "",
            "note": "",
        })

    with (OUT / "annotation_sheet_round2.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(records)

    lines = "\n".join(
        f"| {s} | `{s}` | {len(strata[s])} | {quota[s]} |"
        for s in sorted(strata, key=lambda x: -len(strata[x]))
    )
    note = f"""# 第二轮独立抽样说明（规则 v2 的测试集）

**与第 2 步的 30 条完全不重叠**（已排除其全部 task_id），因此本报告里的指标
是规则 v2 在**独立样本**上的表现，不是「自己考自己」。固定随机种子 `{SEED}`，可复现。
> ⚠️ 口径更正（2026-11-21）：「独立」仅指样本零重叠，不指独立人工标注；
> 参考标签为人机协作产生，见 `output/LABEL_PROVENANCE.md`。

## 样本构成

| 组 | 条数 | 作用 |
|---|---|---|
| 必查项：v2 命中、第 1 轮未复核 | {len(must)} | 检验「报出来的是不是真有问题」→ Precision |
| 分层随机：v2 未命中 | {len(random_rows)} | 检验「有没有漏掉坏题」→ Recall / 漏判 |
| 合计 | {len(records)} | |

必查项按 `output/rule_v2/issues.csv` 全量纳入，是第 3 步报告第 8 节承诺的必查清单。

## 分层设计

按 `snapshot` 归并出 11 个应用领域（`vs_code`→`vscode`，`multiapps`→`multi_apps`），
26 个随机名额按各层可用题数**比例分配**、每层至少 1 条（最大余数法）。
这样大领域多抽、小领域不缺席，避免只测到 chrome / calc 两个大头。

| 中文领域 | app | 可用题数 | 抽中 |
|---|---|---|---|
{lines}

> 注意：这是**分层抽样**，每层抽样概率不同，因此样本上的整体缺陷率
> 不能外推成「全库有 X% 坏题」。分组指标只用于比较规则表现与发现漏判类型。

## 填写口径

`Y/N` 回答的是「按 `rule_tags` 指出的那条标准，这道题是不是真的有这个问题」，
不是「这题有没有任何毛病」。发现别类问题请写进 `note`，不要改填 `Y`。

- `Y` 该缺陷成立 / `N` 规则误报 / `U` 说不清需仲裁
- `human_issue_type` 选填：`ambiguous` / `evaluator` / `init_state` / `overlong` / `leak` / `other`
- `note` **强烈建议填一句话理由**，这些原话会进入 v1.1 规范的正反例

**先读题目自己判断，再看 `rule_tags`。** 遇到拿不准的可回查原始 JSON：
`data/osworld/evaluation_examples/examples/<app>/<task_id>.json`。
"""
    (OUT / "round2_sampling_note.md").write_text(note, encoding="utf-8")

    print("=" * 62)
    print(f"第 4 步 A：已生成第二轮独立样本标注表（seed {SEED}）")
    print("=" * 62)
    print(f"与第 1 轮重叠：0 条  |  v2 命中池 {len(flagged)} 道，未命中池 {len(pool)} 道")
    print(f"样本 {len(records)} 条 = 必查项 {len(must)} + 分层随机 {len(random_rows)}")
    print(f"覆盖领域 {len(strata)} 个：{', '.join(sorted(strata))}")
    print("-" * 62)
    print("已生成：")
    print("  output/annotation_sheet_round2.csv")
    print("  output/round2_sampling_note.md")
    print("=" * 62)


if __name__ == "__main__":
    main()
