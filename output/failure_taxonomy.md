# 缺陷类型台账 v1.0（**已定稿** · 2026-11-21）

> **状态：已定稿。** 2026-11-21 用户裁决「按 C + X1 结案 + 不装包」后定稿。
> v0.2 → v0.3 依据 2026-11-21 的暂定裁决重写；v0.3 → v1.0 为定稿裁决落地。
> A / B 是**两类可分别标记、非互斥**的缺陷维度，一题可同时命中、也可都不命中；
> **每项结论必须引用本题 evaluator 实际执行的检查项**（`func` + `options` + `expected.rules` + 评分器源码），
> 不得用「精确比对」「可能只接受一种」等推测句。
> 标注来源与统计口径见 `output/LABEL_PROVENANCE.md`（单一事实来源）。
>
> 证据：`output/evaluator_evidence.md`（X1 源邮件顺序补证）、
> `output/b_counterexample.md` + `verify_b_counterexample.py`（X3/X5 反例）、
> `output/round2_recomputed.md` + `step4_recompute.py`（定稿复算，口径 D）。
>
> **定稿三项裁决**：① X5 采用口径 C 的处理（台账保留 Y / 统计按 N，差异显式声明）；
> ② X1 顺序补证后结案，由 `U` 改判 `N`；③ B2/B3 **保持候选**，不安装 `python-pptx`。
> 最终指标采用口径 **D**：`2/2/4/22`、N=30、U=0、P 0.500 / R 0.333 / Acc 0.800 / Kappa 0.286。

---

## 0. 本轮裁决与核对结果

| # | 你的裁决 | 核对结果 | 本版处理 |
|---|---|---|---|
| 1 | A/B 可分别标记、非互斥；每项结论引用实际 evaluator 检查 | 认可 | 第 1 节定义不变；**举证要求升级**：须列出本题 `options` 实际启用的检查项清单 |
| 2 | X1 的 B、X2/X4 的 A、X3 的 A 撤销 | 成立 | 4 条原归因全部撤销 |
| 2 | **X1 保留为 A 类待补证据**，需核实源文件是否自然给出唯一顺序 | **已补证，结论相反**：源 docx 三图按 `image1→2→3` 在正文出现，金标 `1/2/3_gold.png` 与它们**字节完全相同**（sha256 前 16 位 `4f584d4b…` / `d5bfc619…` / `4e3e2dd1…`，30882/40335/27669 字节） | 顺序**唯一**，A 类推断不成立 → **已结案**：由 `U` 改判 `N`，计入 TN（用户确认） |
| 2 | X3、X5 **不移除**，改列 B 类候选 | 成立，且源码可证 | 两条**换类保留**为 B2 / B3 候选，见 2.2；并构造反例验证，见 `b_counterexample.md` |
| 3 | 两条 `U` 查证后改判 `N`；**标注表原值不动** | 成立 | 仅在复算的内存副本中改判；CSV 一字未改 |
| 4 | 现在重算 | 已复算并交叉校验 | 口径 C 复现你给的 `2/2/4/21`（P 0.500 / K 0.281）；X1 结案后**最终采用口径 D** `2/2/4/22`（P 0.500 / K 0.286），两组断言均通过 |
| 5 | v1.1 三条建议认可；第 21 行符号差异作口径观察、不判缺陷 | 已落地 | `annotation_guideline_v1.1.md` 已写；符号差异记入「口径观察」 |

> **口径差异已裁决**：X5 在台账按 B 候选（Y）保留、在一致度计算中按 N 处理，
> 两者有意区分并显式声明（B 类候选尚未端到端确认，不计入统计口径的 Y）。
> 详见 `round2_recomputed.md` 第 3 节。

---

## 1. 缺陷类型定义（两类，可分别标记，非互斥）

### A. 验收过严 `OVER_STRICT_EVALUATOR`

> 题目存在 ≥2 种都合理的完成方式，而**本题实际执行的检查项**只接受其中一种。

**举证要求（缺一不可）**：

1. 列出 `evaluator.func` 及 `options` / `expected.rules` 中**本题实际启用**的检查项；
2. 指出其中哪一条把结果限定为唯一值（如 `sheet_data` 全表逐格比对固定金标、
   `exact_match` 比对唯一 URL）；
3. 举出 ≥2 种题目未排除、但会产生不同结果的合理做法。

### B. 约束未被验收 `CONSTRAINT_NOT_VERIFIED`

> 题目写明某项约束，而**本题实际执行的检查项**里没有对应检查，违反约束也能拿满分。

**举证要求（缺一不可）**：

1. 逐条抄出题目里的约束；
2. 列出 `func`（含数组形式的全部函数）及本题 `options` 实际启用的检查项；
3. 指明「有约束、无检查」的那一对，并说明其它检查项为何无法覆盖它；
4. 有条件时构造反例（见 `verify_b_counterexample.py`）。

### 两者关系

```
一道题 → 分别判定 A?  B?  → 可同时为 Y，也可同时为 N
```

不是根因二分、不按「题数」加总；「v2 规则是否报出」是独立维度，与 A/B 无关。
**计数单位是「标记」**，A、B 各算一个。

---

## 2. 逐条台账

### 2.1 A 类 · 已确认 6 个标记（本轮无变动）

| # | 来源 / task_id | 题目留下的自由度 | **本题实际执行的检查项** | 结论 |
|---|---|---|---|---|
| A1 | 第 1 轮 12 · `c7c1e4c3` | 教授主页可能同时列个人/机构邮箱，未指定取哪个 | `compare_table` → `options.rules: [{type: sheet_data, sheet_idx0: 0, sheet_idx1: "EI0"}]` 与固定 `Professor_Contact_Gold.xlsx` **全表逐格比对** | A ✅ |
| A2 | 第 1 轮 22 · `59155008` | "similar names" 可按读音/拼写/来源理解 | `is_expected_active_tab` → `expected.rules: {type: url, url: "https://www.babycenter.com/baby-names/details/carl-853"}` → **唯一 URL** | A ✅ |
| A3 | 第 2 轮 5 · `3e3fc409` | "IMDb Top 30" 未限定榜单类别与取数时点 | `compare_table` → `sheet_data` + `preserve_cells` 与固定 `gold_movies.xlsx` 逐格比对；`config` 打开 `imdb.com`，榜单随时间漂移 | A ✅ |
| A4 | 第 2 轮 8 · `b5062e3e` | 首位作者可能署多个单位 | `compare_table` → `sheet_fuzzy`，`C2:C5` 为 `exact_match`（仅 `ignore_case`）→ affiliation 列只认一个值 | A ✅ |
| A5 | 第 2 轮 19 · `d1acdb87` | 同品牌可能有多个分店/电话/网站 | `compare_table` → `sheet_fuzzy`：`B1:B6` `exact_match`、`C1:C6` `phone_match`、`D1:D6` `domain_match`。三者是**格式宽松匹配**、仍要求唯一取值 | A ✅ |
| A6 | 第 2 轮 29 · `869de13e` | 「学术论文/编程项目/其他」无可复核边界 | `func: [exact_match ×3]`，`expected` 为三个目录的**固定文件名清单**（`ls` 输出逐字比对） | A ✅ |

### 2.2 B 类 · 1 个已确认 + 2 个候选（本轮换类保留）

| # | 来源 / task_id | 题目约束 | **本题实际执行的检查项** | 未覆盖的约束 | 结论 |
|---|---|---|---|---|---|
| B1 | 第 2 轮 9 · `42f4d1c7` | `Test by **writing code** to resize the image`（需编写并执行 GIMP script-fu 脚本） | `func: [is_extension_installed, check_image_size]`；`expected.rules` 只有 `{contain: "lisp"}` 与 `{height:128, width:128}` → 只验扩展安装与输出图尺寸 | **无任何脚本编写/执行检查** | B ✅ 已确认 |
| **B2** | 第 2 轮 6 · `c82632a4`（原 X3） | `Add an image **"none.png"** on the Desktop **to slide 2** with **1cm×1cm** size` | `func: compare_pptx_files`，`options: {examine_shape: false, examine_image_size: true, approximately_tolerance: 0.01}` → 实际执行：页数、形状数量、`shape_type`、**图片宽高**（`slides.py` 第 439–441 行）、文本/备注/字体/对齐/背景色；`examine_shape:false` 关闭 `left/top` | **图片身份（是不是 none.png）**：`slides.py` 主循环不读取 `image.blob`，全文件仅第 130 行 `check_image_stretch_and_center` 使用，该函数本题不调用 | **B 候选**（换类保留） |
| **B3** | 第 2 轮 25 · `bf4e9888`（原 X5） | `pic1.png 放第 1 页、pic2.png 放第 2 页…… following the numerical order` + `six blank slides (no textbox or any other stuff)` | `func: compare_pptx_files`，`options: {examine_shape: false}`（唯一选项）→ 实际执行：页数 6、形状数量、文本（空白页）、备注/字体/对齐/背景色；**位置、尺寸均不比对** | **图片身份与顺序**：同上，主循环不读取图片二进制/文件名 | **B 候选**（换类保留） |

**B2 / B3 的反例验证**（`output/b_counterexample.md`，可复现）：

| 反例 | 构造 | 逐部件比对结果 |
|---|---|---|
| `x3_counterexample.pptx` | 把金标 `ppt/media/image1.png` 换成另一张 PNG（292818 → 30882 字节） | 变化部件 **仅** `ppt/media/image1.png`，其余 XML 全部逐字节一致 |
| `x5_counterexample.pptx` | 把 `image1.png` 与 `image2.png` 二进制对调（文件名与引用关系不变） | 变化部件 **仅** 两个 media，其余 XML 全部逐字节一致 |

> 由于 `compare_pptx_files` 读取的所有部件在反例中不变，反例与金标在该评分器下同分，
> 而题目要求的图片身份 / 顺序已被违反 → 支持 B 类。
> **仍标「候选」**：这是 OOXML 等价性论证 + 源码举证，本机未装 `python-pptx`，
> 尚未端到端调用评分器断言返回 1。升格条件见 `b_counterexample.md` 第 3 节。
>
> 这两条正是你说的「**不只是证据不足**」：撤销的是原 A 归因（位置自由度），
> 换上的是有源码与反例支撑的 B 类（约束未被验收），**没有从台账移除**。

**旁证（判 `N`，不计入缺陷数）**：第 1 轮 1 · `357ef137`，
`compare_table` → `rules: [{type: check_cell, coordinate: "E3", ...}]` 全表只有 `E3` 一处检查，
题目 "Don't touch irrelevant blank regions" 无对应检查项 → B 现象成立，但该行参考标签判 `N`。

### 2.3 原归因撤销 / 换类记录

| # | 来源 | 原归类 | 核对到的实际检查项 | 本版结论 |
|---|---|---|---|---|
| X1 | 第 2 轮 11 · `46407397` | B「数字命名未被验收」 | `compare_image_list`：`query_list` 分别检索 `1.png/2.png/3.png`，`expected.gives: [0,1,2]` 与 `1/2/3_gold.png` 逐一对应 → **命名约束有验收** | 撤销 B；A 待补证经补证后**也不成立**（顺序唯一）→ **已结案改判 `N`**，计入 TN |
| X2 | 第 2 轮 28 · `2fe4b718` | A「帧率/尺寸自由度」 | `compare_animated_images`，`options: {duration_tolerance_ms: 100}`；`animation.py` 明写 `independently of frame rate`、`Splitting one frame into identical shorter frames leaves the score unchanged`，尺寸 `min(w,h)` resize 后算时间轴 SSIM | **完全撤销**，无替代归类 → 改判 `N` |
| X3 | 第 2 轮 6 · `c82632a4` | A「位置未指定 → 只认一种坐标」 | `examine_shape:false` → 位置根本不参与比对 | **撤销 A，换列 B2 候选**（见 2.2） |
| X4 | 第 2 轮 16 · `15aece23` | A「只认一个横向坐标」 | `examine_shape:false` + 专用 `examine_title_bottom_position:true`，仅判标题纵向位置 | **完全撤销**，无替代归类 → 改判 `N` |
| X5 | 第 2 轮 25 · `bf4e9888` | A「尺寸/摆放自由度」 | `examine_shape:false` 是唯一选项，位置/尺寸均不比对 | **撤销 A，换列 B3 候选**（见 2.2），不再标「证据不足」 |

> 「撤销 / 改判 N」仅表示**按现有证据该行不计入缺陷标记**，
> 不等于「这些题一定没问题」；归因一律回到具体检查项，不靠推测。

### 2.4 两条 `U`：查证后改判 `N`（标注表原值不动）

| # | 原 `U` 理由 | 上下文证据 | 本版处理 |
|---|---|---|---|
| 21 · `185f29bd` | 「在字符上做标记」无法判断 | 初始 `review_template.pdf` 解压后有 `UNSATISFACTORY/SATISFACTORY/GOOD/EXCELLENT` × 17 维度表单字段；`compare_pdf_form_fields`（`chrome.py`）用 `_MARK_GLYPHS_PFF = set("√Ã·✓✔")` 判定勾选 | 歧义消解 → 改判 `N`。**符号差异另记为口径观察**，不判缺陷（题目只说 `use "√" as mark`，未写「只能用 √」） |
| 30 · `f9584479` | 缺工作簿上下文 | `Quarterly_Product_Sales_by_Zone.xlsx` 3 个 Zone，各 `F` 列表头 `Total` 但数据空、`Total` 行 `B:E` 空 → 补哪些行列在工作簿内唯一确定 | 歧义消解 → 改判 `N` |

> 两条 `U` 的成因是**标注时未打开初始文件**，不是标准边界模糊。
> v1.1 写入「先查证、后判 U」流程，**不收录为边界案例**。
> 按你的要求，`annotation_sheet_round2.csv` 中这两行**原值仍为 `U`**，
> 改判只存在于 `step4_recompute.py` 的内存副本里。

---

## 3. 统计（定稿口径 D，详见 `round2_recomputed.md`）

| 口径 | TP/FP/FN/TN | N / U | Precision | Recall | Accuracy | Kappa |
|---|---|---|---|---|---|---|
| 原始（未裁决） | 3 / 1 / 7 / 17 | 28 / 2 | 0.750 | 0.300 | 0.714 | 0.282 |
| 裁决·文字口径（X5 保留 Y） | 3 / 1 / 4 / 21 | 29 / 1 | 0.750 | 0.429 | 0.828 | 0.449 |
| 口径 C（X5 按 N，X1 仍 U） | 2 / 2 / 4 / 21 | 29 / 1 | 0.500 | 0.333 | 0.793 | 0.281 |
| **口径 D（C + X1 结案）· 最终采用** | **2 / 2 / 4 / 22** | **30 / 0** | **0.500** | **0.333** | **0.800** | **0.286** |

- 所有数字是**规则 v2 与协作参考标签的一致度**，不是准确率、不是真值校验。
- 第 1 轮（训练）P/Kappa = 1.000 是「自己考自己」；独立样本才是可对外陈述的数字。
- `step4_recompute.py` 内置**两组断言**：口径 C 复现用户给定数字，口径 D 校验最终定稿数字，均已通过。
- **口径区分（已确认，非计算错误）**：X5 台账保留为 B 候选（Y）、统计按 N；
  X3 同为 B 候选但按 Y 计入 FN —— 差别在于前者整条改判、后者撤销 A 后换类保留，保留原始裁决轨迹。

**缺陷标记计数（按标记，不按题数）**：A 已确认 6 个；B 已确认 1 个 + 候选 2 个；
撤销 4 条原归因（X1 B、X2 A、X3 A、X4 A）+ 1 条改判（X5 A→B）；
原「10 A + 2 B = 12 条真坏题」的表述**继续作废**。

---

## 4. 规则 v2 的覆盖能力

| v2 判据 | 实际命中 | 说明 |
|---|---|---|
| `VAGUE_X_STRICT` 模糊词表 | 第 25、29 行 | 第 25 行真实原因是「图片顺序约束未被验收」，词表撞对；第 29 行是归类边界 |
| `AMBIGUOUS_TARGET_X_EXACT` 多值实体 | 第 12、19 行 | 归因准确，但只覆盖「实体词」这一类自由度 |
| 无规则 | A 类的时间/顺序/布局自由度、B 类全部 | 字段规则无法把自然语言约束映射到结构化检查项 |

**核心发现（未变）**：训练集一致度 1.000 → 独立样本显著下降，且参考标签自身的
归因错误在复核中被发现多处 —— 自动规则与协作判断**都需要 evaluator 证据约束**。
B2 / B3 尤其说明：规则依赖词表，抓不到「约束写了但验收没检查」这一类。

---

## 5. 《标注规范 v1.1》三条修订（已认可，已写入文件）

| # | 建议 | 落地位置 |
|---|---|---|
| 1 | 新增 A 类判据 `UNDERSPECIFIED_FREEDOM`，把 3.1 模糊词降为子类信号；**举证必须引用具体 evaluator 规则** | `annotation_guideline_v1.1.md` 第 3 节 |
| 2 | 把覆盖缺口升为正式缺陷类型 B `CONSTRAINT_NOT_VERIFIED`，**列为正式人工检查项但不自动化**、不与 A 互斥 | 同上第 3、4 节 |
| 3 | 「先查 `config` 初始文件 / evaluator 配置 / 评分器源码，仍无法判断才用 `U`」的查证流程；`U` 是证据不足状态，不预设边界案例清单 | 同上第 5 节 |
| 附 | 第 21 行 `√` 与 `✓✔` 的符号差异 | 记入「口径观察记录」，**不判缺陷**；题目未明确「只能用 √」 |

X1–X5 的撤销理由作为**反面例**写入规范：禁止用「精确比对」「可能只接受」等推测句作判据。

---

## 6. 定稿裁决记录（2026-11-21）

| 事项 | 裁决 | 落地 |
|---|---|---|
| X5 统计口径 | **按 C**：台账保留 B 候选（Y）、一致度计算按 N，差异显式声明 | 第 0、3 节；`round2_recomputed.md` 第 3 节 |
| X1 | **结案**：顺序补证后 A 不成立，由 `U` 改判 `N`，采用口径 D | 2.3 节；`evaluator_evidence.md` 第 3.1 节 |
| B2 / B3 | **保持候选**：不安装 `python-pptx`、不端到端升格，证据边界如实保留 | 2.2 节；`b_counterexample.md` 第 3 节 |

> `annotation_guideline_v1.1.md` 同步定稿。所有改判只存在于复算的内存副本与
> 定稿裁决记录中，**两轮标注表 CSV 原值一字未改**（第 21、30 行仍为 `U`，第 11 行仍为 `Y`）。
>
> 台账至此定稿，可作为审计子集与后续复核的事实依据。
