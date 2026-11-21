# 第 2 步产出：规则 v1 与参考标签的一致度报告

> ⚠️ **口径更正（2026-11-21）**：数值保留不改动，「人工判断 / 独立标注 / 真值」等表述
> 已作废。参考标签为**人机协作产生**，非独立人工标注；Kappa 是「规则与参考标签的一致率」。
> 详见 `output/LABEL_PROVENANCE.md`。

样本：`output/annotation_sheet.csv`，30 条参考标签（另有 0 条标为 U 待仲裁）。
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
| **规则报可疑 (SUSPECT)** | TP = 2 | FP = 22（误报） |
| **规则判正常 (CLEAN)** | FN = 0（漏判） | TN = 6 |

## 2. 核心指标

| 指标 | 数值 | 人话解释 |
|---|---|---|
| Precision（精确率） | 0.083 | 规则报出来的可疑题里，真的有问题占多少 → **衡量误报** |
| Recall（召回率） | 1.000 | 真正的坏题里，规则抓到了多少 → **衡量漏判**（靠对照组估计） |
| Accuracy（一致率） | 0.267 | 规则和人判断一致的比例 |
| 期望随机一致率 pe | 0.240 | 两者碰巧猜对的概率 |
| **Cohen's Kappa** | **0.035** | 扣除碰巧一致后的一致性 → 极低（规则基本不可信，需要重写） |

Kappa = (po − pe) / (1 − pe)。Landis & Koch 常用分档：<0.2 极低、0.21–0.40 一般、
0.41–0.60 中等、0.61–0.80 较高、>0.80 几乎完全一致。

## 3. 逐条规则的命中率（第 3 步该修谁）

| 规则 | 含义 | 命中/样本 | 命中率 |
|---|---|---|---|
| `OVERLONG_INSTRUCTION` | 题目过长/多重约束 | 0/8 | 0.0% |
| `NO_INIT_STATE` | 缺少初始状态 | 0/8 | 0.0% |
| `VAGUE_X_STRICT` | 模糊指令撞精确打分器 | 2/8 | 25.0% |

**优先修订：`OVERLONG_INSTRUCTION`**（命中率最低，说明这条规则最容易被领域语义误导）。

## 4. 误报样例（规则报了，人工判没问题）

| 序号 | 规则 | 题目（截断） | 复核理由 |
|---|---|---|---|
| 1 | `OVERLONG_INSTRUCTION` | I have calculated the total work hours from the everday hours. And I have an hourly rate.  | 长描述是背景解释，实际目标是把总金额填入 E3，且验收值与工时乘时薪一致；“不改无关空白区”未被验收。 |
| 2 | `VAGUE_X_STRICT` | Change the text color in the textboxes to on slide 1 yellow, red, and green, respectively, | etc. 位于排除颜色变体的例子中，明确强调颜色必须精确，不存在多种合理做法。 |
| 3 | `NO_INIT_STATE` | I want to switch on the Bluetooth. Can you help me? | 开关蓝牙是直接系统设置，不依赖预置文件或状态；infeasible 说明任务不可执行，不构成初始状态缺失。 |
| 4 | `OVERLONG_INSTRUCTION` | Calculate the total sales in an underneath row called "Total" and display the total of eac | 总计、月增长率及两种图表的要求彼此兼容，月份范围和标题来源均已写明，步骤多但验收目标清楚。 |
| 5 | `OVERLONG_INSTRUCTION` | Could you please review the 'case study.docx' file located in the 'students work' folder o | 虽然包含核验、修正和排序等多个步骤，但范围限定为参考文献，APA 7 标准及保留文档其他部分的要求明确。 |
| 6 | `NO_INIT_STATE` | I want to see the battery percentage. Can you help me display it on my screen? | 显示电池百分比属于系统设置，不要求先有特定文件；config_steps 为 0 不足以判定初始状态缺失。 |
| 8 | `OVERLONG_INSTRUCTION` | A certain railway company in Hong Kong uses a signaling system to keep track of trains in  | 核心目标是按 train_id 去重以统计不同列车，说明了记录格式和时间范围；文字较长但没有相互冲突的要求。 |
| 9 | `NO_INIT_STATE` | I am currently using a ubuntu system. Could you help me set the default video player as VL | 设置 Ubuntu 默认视频播放器不依赖预置文件；题目明确指定 VLC 和默认应用这一目标。 |

## 5. 漏判样例（规则没报，参考标签判 Y）

| 序号 | 题目（截断） | 问题类型 | 复核理由 |
|---|---|---|---|
| （无） | | | |

## 6. 说不清 / 待仲裁（U）

| 序号 | 题目（截断） | 备注 |
|---|---|---|
| （无） | | |

这些「说不清」最有价值：它们说明**标准本身有边界模糊**，第 3 步写《标注规范 v1》时要专门定义。

## 7. 一个必须写进结论的限制

本样本是**分层抽样**（三类缺陷各约 8 条）并人为加入了 6 条对照组，
不是从 368 道题里等概率随机抽的。因此 Precision / Recall **只用于校准规则，
不能外推成「全题库有 X% 的坏题」**。第 1 步那个 14.1% 才是全量扫描的命中率。

