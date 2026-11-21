# B 类候选的反例验证（X3 / X5）

> 目的：把「评测器不比对图片内容」从**读源码**推进到**可复现反例**。
> 方法：只修改 `ppt/media/*.png` 的二进制，其余 OOXML 部件逐字节保持不变；
> 由于 `compare_pptx_files` 从不读取图片二进制，反例在该评分器下应与金标同分。
> 本验证**不安装 python-pptx、不改动 OSWorld 原始数据**，仅用 Python 标准库。

## 源码依据

`data/osworld/desktop_env/evaluators/metrics/slides.py`：

| 位置 | 代码 | 与本题关系 |
|---|---|---|
| 第 130 行 | `if the_image.image.blob == modified_image.image.blob:` | 位于 `check_image_stretch_and_center`，**另一个函数**；本题 `func: compare_pptx_files`，不调用 |
| 第 439–441 行 | `if shape1.shape_type == 13 ...: is_approximately_equal(width/height)` | 本题实际执行的图片检查：只比宽高 |
| 第 425–437 行 | `... and examine_shape` | X3/X5 均为 `examine_shape: false`，位置/尺寸比对被关闭 |
| 第 743–744 行 | `run1.part.blob.decode('utf-8')` | `run.part` 是文本 run 的 XML 部件，用于 `_extract_bullets`，**不是图片** |
| 全文件 | 无其它 `image.blob` / `media/` 读取 | — |

结论：`compare_pptx_files` 读取的是「页数 / 形状数量 / shape_type / left,top,width,height /
文本 / 备注 / 字体 / 对齐 / 背景色」，**没有一项能识别图片是哪一张、按什么顺序**。

---

## X3 · 第 6 行 · c82632a4

- 金标：`x3_gold.pptx`；反例：`x3_counterexample.pptx`
- 构造：把 ppt/media/image1.png 的二进制换成另一张 PNG（292818 → 30882 字节）
- 题目约束：Add an image "none.png" ... to slide 2 with 1cm*1cm size
- **反例违反的约束**：放入的不是 none.png，但尺寸/位置/文本/页数/形状数完全一致

金标各页的图片引用：

| slide | 引用的 media |
|---|---|
| `ppt/slides/slide1.xml` | `(无图片引用)` |
| `ppt/slides/slide2.xml` | `../media/image1.png` |

**逐部件比对结果**：内容不同的部件 = `['ppt/media/image1.png']`；
仅单侧存在的部件 = `无`。

> 变化**只发生在 `ppt/media/` 的二进制**；所有 `ppt/slides/*.xml`、
> `ppt/slides/_rels/*`、备注、主题等被评分器读取的部件均逐字节一致。
> 因此在 `compare_pptx_files` 下，反例与金标的比较结果不变（仍判通过），
> 而题目要求的图片身份 / 顺序已被违反 → 支持 B 类 `CONSTRAINT_NOT_VERIFIED`。

---

## X5 · 第 25 行 · bf4e9888

- 金标：`x5_gold.pptx`；反例：`x5_counterexample.pptx`
- 构造：把 ppt/media/image1.png 与 ppt/media/image2.png 的二进制对调（文件名/引用关系不变）
- 题目约束：pic1.png 放第 1 页、pic2.png 放第 2 页……按数字顺序每页一张
- **反例违反的约束**：第 1 页与第 2 页的图片身份/顺序被调换，但页数、形状数、位置、文本全部不变

金标各页的图片引用：

| slide | 引用的 media |
|---|---|
| `ppt/slides/slide1.xml` | `../media/image1.png` |
| `ppt/slides/slide2.xml` | `../media/image2.png` |
| `ppt/slides/slide3.xml` | `../media/image3.png` |
| `ppt/slides/slide4.xml` | `../media/image4.png` |
| `ppt/slides/slide5.xml` | `../media/image5.png` |
| `ppt/slides/slide6.xml` | `../media/image6.png` |

**逐部件比对结果**：内容不同的部件 = `['ppt/media/image1.png', 'ppt/media/image2.png']`；
仅单侧存在的部件 = `无`。

> 变化**只发生在 `ppt/media/` 的二进制**；所有 `ppt/slides/*.xml`、
> `ppt/slides/_rels/*`、备注、主题等被评分器读取的部件均逐字节一致。
> 因此在 `compare_pptx_files` 下，反例与金标的比较结果不变（仍判通过），
> 而题目要求的图片身份 / 顺序已被违反 → 支持 B 类 `CONSTRAINT_NOT_VERIFIED`。

---

## 验证边界（必须如实说明）

1. 这是 **OOXML 层面的等价性论证 + 源码读取范围举证**，不是真机运行 OSWorld 评分器。
   原因是本机未安装 `python-pptx`，且本轮不改动你的 Python 环境。
2. 若要升级为「已确认」而非「候选」，下一步可安装 `python-pptx` 后直接调用
   `compare_pptx_files(gold, counterexample, **options)`，断言返回 1，即可形成端到端证据。
3. 金标 pptx 来自 HuggingFace `xlangai/ubuntu_osworld_file_cache`（OSWorld 官方缓存），
   仅用于本地验证，未改动 `data/osworld/` 中的任何原始题目。

→ 因此台账中 X3 / X5 仍标为 **B 类候选**，不升格为「已确认」。

复现：`python verify_b_counterexample.py`
