# 第二轮独立抽样说明（规则 v2 的测试集）

> ⚠️ 口径更正（2026-11-21）：此处的「独立」**仅指样本与第 1 轮零重叠**，
> 不指「独立人工标注」。参考标签为人机协作产生，见 `output/LABEL_PROVENANCE.md`。

**与第 2 步的 30 条完全不重叠**（已排除其全部 task_id），因此本报告里的指标
是规则 v2 在**独立样本**上的表现，不是「自己考自己」。固定随机种子 `44`，可复现。

## 样本构成

| 组 | 条数 | 作用 |
|---|---|---|
| 必查项：v2 命中、第 1 轮未复核 | 4 | 检验「报出来的与参考标签是否一致」→ 一致率 |
| 分层随机：v2 未命中 | 26 | 检验「有没有漏掉参考标签判 Y 的题」→ 漏判 |
| 合计 | 30 | |

必查项按 `output/rule_v2/issues.csv` 全量纳入，是第 3 步报告第 8 节承诺的必查清单。

## 分层设计

按 `snapshot` 归并出 11 个应用领域（`vs_code`→`vscode`，`multiapps`→`multi_apps`），
26 个随机名额按各层可用题数**比例分配**、每层至少 1 条（最大余数法）。
这样大领域多抽、小领域不缺席，避免只测到 chrome / calc 两个大头。

| 中文领域 | app | 可用题数 | 抽中 |
|---|---|---|---|
| chrome | `chrome` | 65 | 4 |
| libreoffice_calc | `libreoffice_calc` | 62 | 4 |
| libreoffice_impress | `libreoffice_impress` | 47 | 3 |
| gimp | `gimp` | 30 | 2 |
| vscode | `vscode` | 30 | 2 |
| os | `os` | 28 | 2 |
| libreoffice_writer | `libreoffice_writer` | 27 | 2 |
| thunderbird | `thunderbird` | 19 | 2 |
| multi_apps | `multi_apps` | 12 | 2 |
| base_setup | `base_setup` | 11 | 2 |
| vlc | `vlc` | 3 | 1 |

> 注意：这是**分层抽样**，每层抽样概率不同，因此样本上的整体缺陷率
> 不能外推成「全库有 X% 坏题」。分组指标只用于比较规则表现与发现漏判类型。

## 填写口径（与《标注规范 v1》第 1 节完全一致）

`Y/N` 回答的是「按 `rule_tags` 指出的那条标准，这道题是不是真的有这个问题」，
不是「这题有没有任何毛病」。发现别类问题请写进 `note`，不要改填 `Y`。

- `Y` 该缺陷成立 / `N` 规则误报 / `U` 说不清需仲裁
- `human_issue_type` 选填：`ambiguous` / `evaluator` / `init_state` / `overlong` / `leak` / `other`
- `note` **强烈建议填一句话理由**，这些原话会进入 v1.1 规范的正反例

**先读题目自己判断，再看 `rule_tags`。** 遇到拿不准的可回查原始 JSON：
`data/osworld/evaluation_examples/examples/<app>/<task_id>.json`。
