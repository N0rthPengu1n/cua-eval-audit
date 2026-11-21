# 第 3 步产出：质量规则 v1 → v2 修订与回测报告

> ⚠️ **口径更正（2026-11-21）**：数值保留不改动，「人工复核结论 / 真值 / 单标注者」
> 等表述已作废。参考标签为**人机协作产生**，非独立人工标注；所有指标为一致率。
> 详见 `output/LABEL_PROVENANCE.md`。

依据：`output/annotation_sheet.csv` 的 **30 条参考标签**（28 N / 2 Y / 0 U）
与 `output/agreement_report.md`（Precision 0.083、Kappa 0.035）。
规则 v1 的完整产物保留在 `output/` 未改动，v2 产物在 `output/rule_v2/`。

## 一句话结论

规则 v1 报出 **52 道**可疑题，人工抽样复核后 Precision 仅 **0.083**、
Kappa **0.035** —— 三条字段规则里两条 0% 命中。
按人工结论修订后，v2 报出 **6 道**（摘掉 46 道、新增 0 道），
在 30 条样本上 Precision 升至 **1.000**、Kappa 升至 **1.000**。

> ⚠️ 1.000 来自用于修订规则的同一批样本，只能作为训练集回测结果，不能代表泛化表现。
> 规则 v1 报出的 24 条抽样任务中，22 条被参考标签判为误报，说明字段规则必须经语义复核校准。

## 1. 规则变更清单（每一条都能追到人工标注证据）

| 规则 | 变更 | 理由 | 证据 |
|---|---|---|---|
| `OVERLONG_INSTRUCTION` | 缺陷 → 风险提示 LONG_INSTRUCTION_REVIEW | 8/8 全误报。长 ≠ 歧义；词数无法判断多个要求是否冲突，降级为「必须人工读题」的提示。 | 第 1/4/5/8/14/15/19/21/30 行 note |
| `NO_INIT_STATE` | 收窄触发条件 | 8/8 全误报。新增 infeasible 排除、纯系统设置排除，并要求题目确实提到文件/文档。 | 第 3/6/9/17/23/24/27/28 行 note |
| `VAGUE_X_STRICT` | 精修词表 + 排除性语境 | 2/8 命中，是唯一有效规则。移除 etc/some/any 等数量词，保留主观多解词；模糊词落在 no / except / don't 语境时不报。 | 第 2/11/16/20/29 行 note（反例）；第 22 行（正例） |
| `AMBIGUOUS_TARGET_X_EXACT` | 新增规则（经第二轮收窄） | 题目涉及「邮箱地址 / 联系信息」这类待填字段值，打分器精确比对、又没限定取哪个 → 可疑。初版只匹配 email，误报 10 道「email 作邮件对象」的题，故收窄为 email address / contact information。它还把参考标签判 Y 的第 12 行的归因从「some 是模糊词」修正为「多值实体未限定」。 | 第 12 行 note + 全量核对 10 道新增误报 |
| `EVALUATOR_COVERAGE_GAP` | 不自动化，列入人工复核清单 | 题目提出保留性约束但打分器没校验（第 1 行「不改无关空白区」）。字段规则无法可靠判定，做成自动红线只会制造新误报。 | 第 1 行 note |

## 2. 全量 368 道题：标签数量变化

| 缺陷标签 | v1 | v2 | 变化 |
|---|---|---|---|
| `AMBIGUOUS_TARGET_X_EXACT` | 0 | 2 | +2 |
| `NO_INIT_STATE` | 11 | 0 | -11 |
| `OVERLONG_INSTRUCTION` | 28 | 0 | -28 |
| `VAGUE_X_STRICT` | 20 | 4 | -16 |

风险类（v2，只提示不判缺陷）：

| 风险标签 | 题数 |
|---|---|
| `EXTERNAL_DEPENDENCY` | 231 |
| `NETWORK_SPECIAL` | 57 |
| `LONG_INSTRUCTION_REVIEW` | 28 |
| `INFEASIBLE_TASK` | 26 |
| `ENV_CHANGE_RISK` | 7 |
| `HAS_HINT` | 4 |

> `LONG_INSTRUCTION_REVIEW` 从缺陷降为风险，是本次最重要的决策：
> 词数只能说明「需要人工读一遍」，不能说明「这道题有歧义」。
> 把无法自动判定的维度硬写成红线，只会产出大量无效工单。

## 3. 题目级别的增减

| 项目 | 数量 |
|---|---|
| v1 报、v2 仍报（保留） | 6 |
| v1 报、v2 摘掉（消除误报） | 46 |
| v1 没报、v2 新报 | 0 |

被摘掉的题（示例）：

| task_id | 题目（截断） |
|---|---|
| `00fa164e` | I need to include the experiment results from "~/Documents/awesome-desktop/e |
| `0326d92d` | Calculate the total sales in an underneath row called "Total" and display th |
| `035f41ba` | Help me fill in the Gross profit column by subtracting all the available exp |
| `04578141` | Change the text color in the textboxes to on slide 1 yellow, red, and green, |
| `09a37c51` | I've received a request from my friend who asked for assistance in editing a |
| `0a211154` | Set the background color to yellow for any slide that contains one or more i |
| `0c825995` | I'm working on a comprehensive report for our environmental policy review me |
| `0f84bef9` | On it Whenever I launch a LibreOffice Impress, it uses both screens, one for |

新增的题（示例）：

| task_id | 题目（截断） |
|---|---|
| （无） | |

> 「新增 0 道」不等于「新增规则没用」：`AMBIGUOUS_TARGET_X_EXACT` 命中的题
> 原本就在 v1 名单里（被别的标签报过），它的作用是**把归因改对** ——
> 例如第 12 行（参考标签判 Y），v1 说它「有模糊词 some」，v2 说它「邮箱是多值实体却没限定取哪个」，
> 后者才是能直接拿去修题目的诊断。

## 4. 两道参考标签判 Y 的样本，v2 有没有守住

| 序号 | task_id | v2 结果 | 命中标签 | 人工复核理由 |
|---|---|---|---|---|
| 12 | `c7c1e4c3` | ✅ 仍命中 | AMBIGUOUS_TARGET_X_EXACT | 教授主页可能同时列个人邮箱和机构邮箱，题目未指定取哪一个，而表格精确比对只接受预设答案。 |
| 22 | `59155008` | ✅ 仍命中 | VAGUE_X_STRICT | “相似名字”可按读音、拼写或来源作不同理解；验收器却只检查 Carl 的单一详情页地址，结果边界不清。 |

守住这两道是修订的底线：如果为了降低误报把规则改到连真问题都不报，
Precision 会好看、Recall 会塌掉，等于用「少报」粉饰指标。

## 5. 30 条样本上的回测

| 指标 | 规则 v1 | 规则 v2 | 说明 |
|---|---|---|---|
| TP / FP / FN / TN | 2/22/0/6 | 2/0/0/28 | 以 30 条人工标注为参照 |
| Precision | 0.083 | 1.000 | 报出来的里面真有问题的比例 |
| Recall | 1.000 | 1.000 | 真问题里被抓到的比例 |
| Accuracy | 0.267 | 1.000 | 与人工判断一致的比例 |
| Cohen's Kappa | 0.035 | 1.000 | 扣除碰巧一致 |

### 数字变漂亮 ≠ 规则变好（更重要的一段）

v2 只报 6 道、比 v1 少 46 道，看起来「干净」了，
但代价是**规则变保守了，只覆盖能用字段判定的维度**：

- 你在第 1 行 note 里发现的「题目写了不要改无关空白区，打分器却完全不校验」，
  属于**约束—验收覆盖缺口**，v2 没有任何规则能抓到它（见变更清单第 5 行，故意不自动化）。
- 除两道已复核的样本外，v2 命中的其余 4 道**尚未经过复核**，
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
第二轮请把 `output/rule_v2/issues.csv` 里尚未人工判断的 4 道
作为必查项：它们数量少、优先级最高，正好用来检验「少报是否掩盖了漏判」。
