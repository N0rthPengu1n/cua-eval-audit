# CUA 评测任务质量审计

本项目审计 OSWorld 公开计算机操作任务的**任务设计与验收逻辑**。重点不是比较模型能力，而是检查一条任务的指令、初始状态和评分器是否相互一致：任务是否存在合理的多种完成方式却只接受一种结果，或题目写明的约束是否没有被评分器验证。

## 数据来源与使用范围

- **来源**：[xlang-ai/OSWorld](https://github.com/xlang-ai/OSWorld) 公开任务库，采用 Apache-2.0 许可证；许可证文件保留于 `data/osworld/LICENSE`。
- **审计对象**：`data/osworld/evaluation_examples/examples/` 中的 368 道任务 JSON。每条任务包含自然语言指令、初始环境配置和 evaluator（评分器）配置。
- **核对依据**：`data/osworld/desktop_env/evaluators/` 中与任务对应的评分器源码，用于确认 evaluator 实际检查的字段和选项语义。
- **边界**：项目只读取、统计和审计上游任务。

`data/osworld/` 是为复核保留的上游数据与源码快照；项目自身的分析脚本位于根目录，所有生成结果位于 `output/`。

为避免公开可能包含凭据的 Thunderbird 配置，`data/sample_files/x1_profile/` 与 `data/sample_files/thunderbird.profile.tar.gz` 仅保留在本地审计环境中，未纳入公开仓库；其余复现所需的代码、任务数据和审计产物均已包含。

## 审计流程

1. **全量画像**：扫描 368 道任务，提取任务长度、初始状态、评分器、外部依赖和风险标签。
2. **规则校准**：对第一轮 30 条分层样本生成参考标签，计算字段规则与参考标签的一致度，并据此修订规则。
3. **独立复测**：对与第一轮零重叠的第二轮 30 条样本复核，避免只在用于修订规则的样本上得出结论。
4. **源码举证**：对候选问题回查任务配置与 evaluator 源码，将问题区分为：
   - **A：验收过严**——存在多种合理完成方式，但实际评分器只接受一种；
   - **B：约束未被验收**——题目明确提出约束，但实际评分器没有对应检查。
5. **审计子集**：按 11 个任务领域分层抽取 80 条可复现子集，供后续按领域和评分器分析。

## 当前结果与解释边界

第二轮 30 条样本按完整 `task_id` 关联 [裁决表](output/adjudications.csv)。X3、X5 均以原评分器的实测结果确认 B 类缺陷。

| 指标 | 数值 |
|---|---:|
| TP / FP / FN / TN | 3 / 1 / 4 / 22 |
| Precision / Recall | 0.750 / 0.429 |
| Accuracy / Cohen's Kappa | 0.833 / 0.453 |
| 分层审计子集 | 80 条，11 个领域 |

这里的 Precision、Recall、Accuracy 和 Kappa 都表示**自动规则与人机协作参考标签的一致度**，不代表规则准确率、真实缺陷率或评分者间信度。样本量较小，且采用分层抽样，因此不能据此估计整个 OSWorld 的缺陷比例。完整口径见 [标注来源与统计口径](output/LABEL_PROVENANCE.md)，判定标准见 [标注规范](annotation_guideline_v1.1.md)。

## 目录与交付物

| 路径 | 作用 |
|---|---|
| `data/osworld/` | OSWorld 任务数据、评分器源码和许可证 |
| `step1_profile.py` | 全量任务画像与风险扫描，输出 `task_profile.csv`、`issues.csv` |
| `step2_sample.py` / `step2_agreement.py` | 第一轮分层抽样与一致度报告 |
| `step3_compare.py` | 规则 v1/v2 修订与回测 |
| `step4_resample.py` / `step4_evaluate.py` | 第二轮零重叠抽样与独立复测 |
| `step4_recompute.py` | 按最终裁决复算第二轮指标 |
| `step4b_subset.py` | 构建 80 条、11 领域的审计子集 |
| `verify_b_counterexample.py` | 构造 PPTX 反例并比较压缩包部件 |
| `verify_pptx_regression.py` | 运行原评分函数与增加逐页图片像素校验的本地原型 |
| `output/` | CSV 数据、审计报告、评分器证据和反例材料 |

关键产物：

- `output/task_profile.csv`：368 道任务的结构化画像；
- `output/issues.csv`：第一版规则筛出的待复核任务；
- `output/annotation_sheet*.csv`：两轮参考标签记录；
- `output/adjudications.csv`：按 task ID 记录 A/B 状态、证据来源、复核者和修订号；
- `output/round2_recomputed.md`：当前一致度统计与历史口径对照；
- `output/pptx_regression.json`：评分参数、评分器与资产摘要、逐例分数；
- `output/failure_taxonomy.md`：已确认问题与候选问题台账；
- `output/subset_80.csv`：80 条领域分层审计子集。

## 复现

画像、统计和抽样只需要 Python 3 标准库。PPTX 和 XLSX 评分回归各有独立依赖。生成报告写入 `output/`。

首次从头运行时，按以下顺序执行：

```bash
python step1_profile.py
python step2_sample.py
# 人工完成 output/annotation_sheet.csv 中的 human_verdict / note
python step2_agreement.py
python step3_compare.py
python step4_resample.py
# 人工完成 output/annotation_sheet_round2.csv 中的 human_verdict / note
python step4_evaluate.py
python step4_recompute.py
python step4b_subset.py
python verify_b_counterexample.py
```

注意：`step2_sample.py` 和 `step4_resample.py` 会重新生成对应的标注表。若只想复查当前已完成的结果，请不要运行这两个抽样脚本；可直接运行 `step4_recompute.py`、`step4b_subset.py` 或查看 `output/` 中的已生成报告。

### PPTX 评分回归

在隔离的 Python 环境中安装 `python-pptx==1.0.2`，然后运行：

```bash
python verify_pptx_regression.py
python step4_recompute.py
python step4b_subset.py
python -m unittest -v test_audit_regression
```

X3 检查第 2 页的图片，X5 检查 6 页的图片顺序。两个任务的原评分函数均接受正确稿、错误稿和无损重编码稿；本地原型在原有检查之后比较各页图片解码后的 RGBA 像素，只拒绝错误稿。像素等价覆盖无损重编码这一对照，尚未校准有损压缩或色彩配置差异。测试范围是本地文件评分函数。

离线重评分与逐项结果记录参考 [WebArena-Verified](https://github.com/ServiceNow/webarena-verified/blob/main/docs/index.md#part-1-evaluate-a-pre-run-task)。参考解重跑与失败断言参考 [Terminal-Bench Science 的评审流程](https://github.com/harbor-framework/terminal-bench-science/blob/main/REVIEWING.md)。

### XLSX 评分回归

在隔离的 Python 环境中运行以下命令。

```bash
python -m pip install -r requirements-xlsx-regression.txt
python verify_xlsx_regression.py
```

任务 `26a8440e` 要求在 `Sheet2` 按月汇总销售额，未指定月份顺序。原版 `compare_table` 要求与金标逐行一致。回归对比官方正序稿、月份倒序稿和把一个月的合计改错的稿件。原版分数依次为 `1 / 0 / 0`，本地原型为 `1 / 1 / 0`。原型从源表独立计算每月合计，用月份匹配结果，并复用原版的源表保留检查。测试调用原评分函数并读取实际 XLSX 文件，范围为离线文件评分。 [逐项评分记录](output/xlsx_regression.json)

### 试点复核

试点含 6 道表格题及 6 道演示文稿题，记录了预期能力、验收条件、评分配置和复核问题。 [试点设计](output/pilot_design.md) · [空白复核表](output/pilot_review.csv) · [复核指南](output/pilot_review_guide.md)
