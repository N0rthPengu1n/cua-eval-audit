# Evaluator 证据底稿（2026-11-21 核对 · 第 2 版）

> 用途：支撑 `failure_taxonomy.md` **v0.3** 的每一条归类与换类。
> 每条都给出 **原始 JSON 配置片段 + 评分器源码行为**，不使用「精确比对」「可能只接受」等推测句。
> 证据来源均为 `xlang-ai/OSWorld`（Apache-2.0），本地路径 `data/osworld/`。

## 0. 核对范围与方法

| 项 | 内容 |
|---|---|
| 原始任务 JSON | `data/osworld/evaluation_examples/examples/**/*.json`（368 道） |
| 评分器源码 | `data/osworld/desktop_env/evaluators/metrics/{slides,animation,chrome,table}.py` |
| 初始文件 | `data/sample_files/`：`review_template.pdf`、`Quarterly_Product_Sales_by_Zone.xlsx`、`movies.xlsx`、`Multiply_Time_Number.xlsx`、`lecture-notes.docx`、`thunderbird.profile.tar.gz`、`x1_gold/{1,2,3}_gold.png`、`x3_gold.pptx`、`x5_gold.pptx`、`x3_counterexample.pptx`、`x5_counterexample.pptx` |
| 核对对象 | 两轮参考标签判 `Y` 的 12 条 + 判 `U` 的 2 条 + 1 条旁证，共 15 道 |
| 本版新增 | X1 源邮件顺序补证（第 3.1 节）、X3/X5 的 B 类源码举证与反例（第 3.3/3.5/6 节） |

> 源码通过 `git sparse-checkout add desktop_env/evaluators` 取得，未改动任何原始题目。

---

## 1. `compare_pptx_files` 的选项语义（关键，5 条撤销里有 3 条靠它）

源码：`data/osworld/desktop_env/evaluators/metrics/slides.py`，函数 `compare_pptx_files`（第 235 行起）。

| 选项 | 默认值 | 实际作用 |
|---|---|---|
| `examine_shape` | `true` | 控制 `left / top / width / height` 四项的 `is_approximately_equal` 比对。**设为 false 则位置与尺寸都不比** |
| `examine_image_size` | `false` | 对 `shape_type == 13`（图片）只校验 `width / height`；**不校验 `left / top`** |
| `examine_title_bottom_position` | `false` | 专用分支，只针对标题的纵向位置判定，不是全量坐标比对 |
| `examine_number_of_slides` | `true` | 页数 |
| `examine_text` / `examine_note` / `examine_font_*` / `examine_alignment` / `examine_background_color` | `true` | 文本、备注、字体、对齐、背景色 |
| （无条件） | — | `len(slide1.shapes) != len(slide2.shapes)` 直接返回 0 → **形状数量仍被校验** |

关键源码片段：

```python
examine_shape = options.get("examine_shape", True)
...
if (not is_approximately_equal(shape1.left, shape2.left) or
    not is_approximately_equal(shape1.top,  shape2.top)  or
    not is_approximately_equal(shape1.width,shape2.width) or
    not is_approximately_equal(shape1.height,shape2.height)) and examine_shape:
    return 0
```

**结论**：`examine_shape: false` 时，「位置 / 尺寸自由度导致被拒」这一推断不成立。
但「页数、形状数量、文本、备注、字体、对齐、背景色」仍在校验范围内，
所以也不能反过来说「完全不精确比对」——**必须逐选项核实**。

---

## 2. 逐题证据

### A1 · 第 1 轮 12 · `c7c1e4c3`（教授邮箱）

```json
"func": "compare_table",
"expected": { "type": "cloud_file", "path": ".../Professor_Contact_Gold.xlsx" },
"options": { "rules": [ { "type": "sheet_data", "sheet_idx0": 0, "sheet_idx1": "EI0" } ] }
```
`sheet_data` 为全表逐格比对固定金标文件 → 邮箱列只认一个值。题目未指定取个人还是机构邮箱 → **A 成立**。

### A2 · 第 1 轮 22 · `59155008`（similar names）

```json
"func": "is_expected_active_tab",
"expected": { "type": "rule", "rules": { "type": "url",
  "url": "https://www.babycenter.com/baby-names/details/carl-853" } }
```
唯一 URL → **A 成立**。

### A3 · 第 2 轮 5 · `3e3fc409`（IMDb Top 30）

```json
"func": "compare_table",
"expected": { "type": "cloud_file", "path": ".../gold_movies.xlsx" },
"options": { "rules": [
  { "type": "sheet_data", "sheet_idx0": "RNunseen_movies", "sheet_idx1": "ENunseen_movies" },
  { "type": "preserve_cells", "sheet_idx0": "RNseen_movies", "sheet_idx1": "ENseen_movies" } ] }
```
`config` 中 `chrome_open_tabs: ["https://www.imdb.com"]`，榜单为外部实时数据，随时间漂移；
验收却与固定 `gold_movies.xlsx` 逐格比对 → **A 成立**（时点 / 口径自由度）。

初始 `movies.xlsx`：表头 `title / release year / ratings / description`，为「已看电影」清单。

### A4 · 第 2 轮 8 · `b5062e3e`（首位作者 affiliation）

```json
"func": "compare_table",
"options": { "rules": [ { "type": "sheet_fuzzy", "sheet_idx0": "RI0", "sheet_idx1": "EI0",
  "rules": [
    { "range": ["A1:C1"], "type": "exact_match", ... },
    { "range": ["A2:B5"], "type": "exact_match", ... },
    { "range": ["C2:C5"], "type": "exact_match", "ignore_case": true } ] } ] }
```
`C2:C5`（affiliation 列）为 `exact_match` → 只认一个单位 → **A 成立**。

### A5 · 第 2 轮 19 · `d1acdb87`（餐馆信息）

```json
"func": "compare_table",
"options": { "rules": [ { "type": "sheet_fuzzy", "rules": [
  { "range": ["A1:A6"], "type": "exact_match" },
  { "range": ["B1:B6"], "type": "exact_match", "normalization_regex": [["Rd","Road"],["St","Street"], ...] },
  { "range": ["C1:C6"], "type": "phone_match", "allow_missing_expected": true },
  { "range": ["D1:D6"], "type": "domain_match" } ] } ] }
```
`phone_match` / `domain_match` 是**格式宽松匹配**，仍要求唯一取值，不是「接受多个答案」→ **A 成立**。

### A6 · 第 2 轮 29 · `869de13e`（桌面归类）

```json
"func": ["exact_match", "exact_match", "exact_match"],
"result": [ { "command": ["ls", "/home/user/Desktop/Paper_reading"] }, ... ],
"expected": [ { "rules": { "expected": "1706.03762.pdf\n1802.05365.pdf\n..." } }, ... ]
```
三个目录的 `ls` 输出逐字比对固定清单 → 只认唯一分组 → **A 成立**。

### B1 · 第 2 轮 9 · `42f4d1c7`（GIMP 脚本）

```json
"func": ["is_extension_installed", "check_image_size"],
"expected": [
  { "rules": { "type": "contain", "expected": "lisp" } },
  { "rules": { "height": 128, "width": 128 } } ]
```
题目约束 `Test by writing code to resize the image`；检查项只有「扩展含 lisp」与
「输出图 128×128」，**无任何脚本编写/执行检查** → **B 成立**。

### 旁证 · 第 1 轮 1 · `357ef137`（不要动其它空白区，该行判 N）

```json
"func": "compare_table",
"options": { "rules": [ { "type": "check_cell", "coordinate": "E3",
  "props": { "value": { "method": "approx:0.001", "ref": 191.6667 } } } ] }
```
全表只有 `E3` 一处检查 → 约束「Don't touch irrelevant blank regions」无对应检查项。
**B 现象成立**，但该行 `human_verdict = N`（按原规则标准判为误报），不计入缺陷数。

---

## 3. X1–X5 原归因撤销 / 换类的证据

### X1 · 第 2 轮 11 · `46407397`（数字命名）— 撤销 B；A 待补证据经补证后**亦不成立**

```json
"func": "compare_image_list",
"result": { "type": "googledrive_file", "query_list": [
  [ "...'figures'...", "title = '1.png' and trashed = false" ],
  [ "...'figures'...", "title = '2.png' and trashed = false" ],
  [ "...'figures'...", "title = '3.png' and trashed = false" ] ],
  "dest": ["1.png", "2.png", "3.png"] },
"expected": { "path": [".../1.png", ".../2.png", ".../3.png"],
  "dest": ["1_gold.png", "2_gold.png", "3_gold.png"], "multi": true, "gives": [0,1,2] }
```
`query_list` 明确按 `1/2/3.png` 检索，`gives: [0,1,2]` 与三张金标图逐一对应
→ **命名约束有验收**，原 B 归因撤销。

#### 3.1 本轮新增：源文件顺序补证（回应「需核实源文件是否自然给出唯一顺序」）

证据链（全部本地可复现，未改动 OSWorld 原始题目）：

1. `config` 中 `thunderbird.profile.tar.gz` → 解包得到
   `.thunderbird/.../ImapMail/outlook.office365.com/Notes`（mbox，168,311 字节）；
2. 该 mbox 中唯一邮件 **Subject: Lecture Document**，含附件
   `lecture-notes.docx`（122,101 字节）；
3. docx 内 `word/media/image1.png / image2.png / image3.png`；
   `word/_rels/document.xml.rels` 中 `rId4→image1.png`、`rId5→image2.png`、`rId6→image3.png`；
   `word/document.xml` 的 `r:embed` 按 **`rId4 → rId5 → rId6`** 依次出现
   → **三张图在正文中按 1→2→3 的自然顺序出现，顺序唯一**；
4. 金标 `1_gold.png / 2_gold.png / 3_gold.png` 与上述三张图**字节完全相同**：

| 文件 | 字节 | sha256 前 16 位 |
|---|---|---|
| `image1.png` = `1_gold.png` | 30882 | `4f584d4b99a2ae04` |
| `image2.png` = `2_gold.png` | 40335 | `d5bfc6194ab0ff2f` |
| `image3.png` = `3_gold.png` | 27669 | `4e3e2dd11a39dcb6` |

字节级一一对应矩阵（`SAME` 表示完全相同）：

```
            1_gold   2_gold   3_gold
image1      SAME     diff     diff
image2      diff     SAME     diff
image3      diff     diff     SAME
```

**结论**：源文档自然给出了唯一的图片顺序，且 evaluator 的固定映射与该顺序一致；
「指令未规定编号顺序 → 多种合理做法只认一种」的 **A 类推断不成立**。
因此 X1 建议由 `U` **结案改判 `N`**（撤销 A 待补证据）。
本轮按用户暂定裁决**仍把 X1 留在 `U`**，台账保持未定稿，等待拍板。

### X2 · 第 2 轮 28 · `2fe4b718`（GIF）— 撤销 A

```json
"func": "compare_animated_images",
"options": { "duration_tolerance_ms": 100 }
```

源码 `data/osworld/desktop_env/evaluators/metrics/animation.py`：

```python
"""Compare GIF content on its playback timeline, independently of frame rate."""
def compare_animated_images(actual_path, expected_path, duration_tolerance_ms=100):
    """Return time-weighted grayscale SSIM after checking the GIF duration.
    Splitting one frame into identical shorter frames leaves the score unchanged.
    ...
    """
    if abs(actual_ends[-1] - expected_ends[-1]) > duration_tolerance_ms:
        return 0.0
    # Integrate each overlapping interval, rather than comparing frame indices.
    # This permits different frame counts and frame durations for the same clip.
    ...
    size = (min(actual.width, expected.width), min(actual.height, expected.height))
    ... structural_similarity(...)
```

帧率、帧分段、帧数、尺寸均未被限定为唯一值；仅总时长有 100ms 容差。
原 note「若按动画逐帧精确比对」是**假设**，与实现相反 → 撤销 A。

### X3 · 第 2 轮 6 · `c82632a4`（1cm×1cm 图片）— 撤销 A，**换列 B2 候选**

```json
"func": "compare_pptx_files",
"expected": { "type": "cloud_file", "path": ".../31_2_Gold.pptx" },
"options": { "examine_shape": false, "examine_image_size": true,
             "approximately_tolerance": 0.01 }
```

**本题实际执行的检查项**：页数（`examine_number_of_slides` 默认 true）、
形状数量（无条件 `len(slide.shapes)`）、`shape_type`、
图片宽高（`slides.py` 第 439–441 行，`examine_image_size`）、
文本 / 备注 / 字体 / 对齐 / 背景色 / 项目符号（各项 `examine_*` 默认 true）。
`examine_shape: false` → `left/top` 不参与比对。

- 撤销 A：「没指定位置 → 其他位置会被拒绝」无规则依据。
- **换列 B**：题目约束 `Add an image "none.png" ... with 1cm*1cm size` 指定了**具体图片文件**；
  但 `slides.py` 主循环**不读取 `image.blob`**，全文件唯一读取图片二进制的是第 130 行
  `check_image_stretch_and_center`（另一个独立函数，本题 `func` 未调用）；
  第 743–744 行的 `run.part.blob` 是文本 run 的 XML 部件，用于 `_extract_bullets`，与图片无关。
  → 换成任意一张 1cm×1cm 的图片也能通过，**图片身份约束无对应检查项**。
- 反例：`x3_counterexample.pptx` 把 `ppt/media/image1.png` 换成另一张 PNG，
  变化部件仅此一项，其余 OOXML 逐字节一致 → 见第 6 节与 `b_counterexample.md`。

### X4 · 第 2 轮 16 · `15aece23`（标题移到底部）— 撤销 A

```json
"func": "compare_pptx_files",
"options": { "examine_shape": false, "examine_title_bottom_position": true }
```
源码 `slides.py` 第 380 行起有 `examine_title_bottom_position` 专用分支，
只处理标题纵向位置；`examine_shape` 已关闭通用坐标比对。
「只接受一个具体横向坐标」无规则依据 → 撤销 A。

### X5 · 第 2 轮 25 · `bf4e9888`（六页六图）— 撤销 A，**换列 B3 候选**（不再标「证据不足」）

```json
"func": "compare_pptx_files",
"expected": { "type": "cloud_file", "path": ".../4.3-Template_4.29.2016_Gold.pptx" },
"options": { "examine_shape": false }
```

题目约束：`insert one image per slide in order—pic1.png on the first slide,
pic2.png on the second, and so on—following the numerical order` +
`six blank slides (no textbox or any other stuff)` → **图片身份 + 顺序 + 空白页**。

**本题实际执行的检查项**：页数 6、形状数量（每页 1 个 `<p:pic>`）、
文本（空白页 → 无文本可比）、备注 / 字体 / 对齐 / 背景色（默认 true）；
`examine_shape: false` 是唯一选项 → 位置与尺寸均不比对。

- 撤销 A：原 note「精确比对可能拒绝其他合理布局」未指明比的是什么，且 `examine_shape` 已关闭。
- **换列 B（用户裁决：不只是证据不足）**：`slides.py` 主循环不读取图片二进制、
  文件名或顺序；金标 `x5_gold.pptx` 为 6 页 / 6 个 media / 每页 1 个 `<p:pic>`。
  → 六张图**任意顺序、任意内容**（只要页数、形状数、空白文本一致）都能通过，
  **图片身份与顺序约束无对应检查项**。
- 反例：`x5_counterexample.pptx` 把 `image1.png` 与 `image2.png` 二进制对调
  （文件名与引用关系不变），变化部件仅两个 media，其余 OOXML 逐字节一致
  → 见第 6 节与 `b_counterexample.md`。

> 两条均标**候选**：尚未端到端调用 `compare_pptx_files` 断言返回 1
> （本机未装 `python-pptx`，本轮不改动 Python 环境）。升格条件见 `b_counterexample.md` 第 3 节。

---

## 4. 两条 `U` 的上下文证据（查证后建议改判 `N`，标注表原值不动）

### 第 2 轮 21 · `185f29bd`（PDF 评价表「√」）

初始 `review_template.pdf`（104 KB）内容流 zlib 解压后，表单字段为：

```
EMPLOYEE NAMERow1, EMPLOYEE IDRow1, ..., DATE SUBMITTEDRow1,
UNSATISFACTORYWorks to Full Potential, SATISFACTORYWorks to Full Potential,
GOODWorks to Full Potential, EXCELLENTWorks to Full Potential,
...（17 个评价维度 × 4 个等级）
```

评分器 `compare_pdf_form_fields`（`metrics/chrome.py` 第 591 行起）：

```python
_MARK_GLYPHS_PFF = set("√Ã·✓✔")
_RATING_COLS_PFF = ["UNSATISFACTORY", "SATISFACTORY", "GOOD", "EXCELLENT"]
...
def _is_mark_pff(tok): return bool(tok) and all(c in _MARK_GLYPHS_PFF for c in tok)
...
# use_widgets 路径：按 widget.field_value 判定每个维度哪一列被勾选
# 几何路径：按 √ 所在 x 坐标落入哪一评级列判定
```

**「在字符上做标记」的歧义被表单结构消解**：`√` 就是打在评级选项上。
附带发现：评分器把 `√` 与 `✓✔`（及 `Ã·` 编码变体）一并接受，
属于「约束表述 vs 验收口径」的容差差异，但题目未写「只能用 √」，**不宜据此判缺陷**。

### 第 2 轮 30 · `f9584479`（Fill the missing rows and columns which show the total value）

初始 `Quarterly_Product_Sales_by_Zone.xlsx` 实际内容：

| 行 | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| 1 | Zone 1 | | | | | |
| 2 | Product | Q1 | Q2 | Q3 | Q4 | **Total** |
| 3–5 | 三个产品 | 有值 | 有值 | 有值 | 有值 | **空** |
| 6 | **Total** | 空 | 空 | 空 | 空 | 空 |
| 8–13 | Zone 2（同构） | | | | | |
| 15–20 | Zone 3（同构） | | | | | |

「补哪些总计行列」在工作簿内**唯一确定**（各产品行的 F 列合计 + 各季度列的 Total 行）。
原 `U` 的成因是标注时未打开初始文件，而非标准边界模糊。

```json
"func": "compare_table",
"expected": { "type": "cloud_file", "path": ".../Quarterly_Product_Sales_by_Zone_gold.xlsx" },
"options": { "rules": [ { "type": "sheet_data", "sheet_idx0": 0, "sheet_idx1": "EI0" } ] }
```
`sheet_data` 全表比对固定金标 —— 若题目对「合计的口径」另有自由度，
可另作 A 类待核，但**不能靠「缺上下文」维持 U**。

---

## 5. 证据使用规则（写入 v1.1）

1. 缺陷判定必须引用 `evaluator.func` + 具体 `options` / `expected.rules` 字段；
2. 遇到 `examine_*` / `*_tolerance` / `*_match` 等选项，**必须查评分器源码**确认语义，
   不得按字面推断；
3. 涉及「题目未说明」的判断，须先查 `config` 指向的初始文件（工作簿 / PDF 表单 / 图片）；
4. 禁止使用「精确比对」「可能只接受一种」「若按…比对」等未落地的推测句；
5. `U` 只在「查过配置 + 源码 + 初始文件仍无法判定」时使用，是证据不足状态，不是缺陷类型；
6. **B 类必须列出本题 `options` 实际启用的检查项清单**，并指明「有约束、无检查」的那一对；
   有条件时构造反例（只改被断言未检查的内容，其余部件保持不变）。

---

## 6. B 类反例验证摘要（`verify_b_counterexample.py`）

| 反例 | 构造 | 内容不同的部件 | 单侧部件 |
|---|---|---|---|
| `x3_counterexample.pptx` | 金标 `ppt/media/image1.png` 换成另一张 PNG（292818 → 30882 字节） | `ppt/media/image1.png` | 无 |
| `x5_counterexample.pptx` | `image1.png` 与 `image2.png` 二进制对调 | `ppt/media/image1.png`、`ppt/media/image2.png` | 无 |

两次构造中，**所有被 `compare_pptx_files` 读取的 OOXML 部件（slide XML、rels、备注、主题等）
均逐字节一致**，变化只发生在图片二进制。结合第 1 节的源码读取范围举证，
可推出反例与金标在该评分器下同分，而题目要求的图片身份 / 顺序已被违反。

复现：`python verify_b_counterexample.py`；完整输出：`output/b_counterexample.md`。

**边界**：这是 OOXML 等价性论证 + 源码举证，不是真机运行评分器；
因此台账中 B2 / B3 仍为「候选」，未升格为「已确认」。
