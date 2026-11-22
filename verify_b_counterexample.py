"""构造 PPTX 反例，验证图片身份与顺序约束未被 `compare_pptx_files` 检查。"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SF = ROOT / "data" / "sample_files"
OUT = ROOT / "output" / "b_counterexample.md"

X3_GOLD = SF / "x3_gold.pptx"
X5_GOLD = SF / "x5_gold.pptx"
X5_PIC1 = SF / "x1_gold" / "1_gold.png"   # 任意一张不同的 PNG 即可
X5_PIC2 = SF / "x1_gold" / "2_gold.png"


def _build(path: Path, mapping: dict[str, bytes]) -> bytes:
    """读入 pptx，返回只替换指定 media 二进制、其余部件逐字节不变的新 pptx 字节。"""
    zin = zipfile.ZipFile(path)
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zout:
        for item in zin.infolist():
            data = mapping.get(item.filename, zin.read(item.filename))
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
    return bio.getvalue()


def diff_parts(a: bytes, b: bytes) -> tuple[list[str], list[str]]:
    """返回（内容不同的部件名, 只在某一侧存在的部件名）。"""
    za, zb = zipfile.ZipFile(io.BytesIO(a)), zipfile.ZipFile(io.BytesIO(b))
    na, nb = set(za.namelist()), set(zb.namelist())
    changed = sorted(n for n in na & nb if za.read(n) != zb.read(n))
    exclusive = sorted((na ^ nb))
    return changed, exclusive


def slide_media_map(path: Path) -> dict[str, str]:
    """每页 slide 引用的 media 文件（通过 slideN.xml.rels 的 r:embed -> Target）。"""
    z = zipfile.ZipFile(path)
    out = {}
    for s in sorted(n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)):
        num = re.search(r"slide(\d+)\.xml", s).group(1)
        rel = f"ppt/slides/_rels/slide{num}.xml.rels"
        xml = z.read(s).decode("utf-8", "replace")
        embeds = re.findall(r'r:embed="([^"]+)"', xml)
        targets = []
        if rel in z.namelist():
            rxml = z.read(rel).decode("utf-8", "replace")
            rmap = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rxml))
            targets = [rmap.get(e, "?") for e in embeds]
        out[s] = ", ".join(targets) if targets else "(无图片引用)"
    return out


def main() -> None:
    results = []

    z3 = zipfile.ZipFile(X3_GOLD)
    media3 = [n for n in z3.namelist() if n.startswith("ppt/media/")]
    assert len(media3) == 1, media3
    alt = X5_PIC1.read_bytes()
    orig3 = z3.read(media3[0])
    assert orig3 != alt, "替换图与原图不能相同"
    x3_ce = _build(X3_GOLD, {media3[0]: alt})
    c3, e3 = diff_parts(X3_GOLD.read_bytes(), x3_ce)
    (SF / "x3_counterexample.pptx").write_bytes(x3_ce)
    results.append({
        "name": "X3 · 第 6 行 · c82632a4",
        "gold": X3_GOLD.name, "ce": "x3_counterexample.pptx",
        "action": f"把 {media3[0]} 的二进制换成另一张 PNG（{len(orig3)} → {len(alt)} 字节）",
        "changed": c3, "exclusive": e3, "media_map": slide_media_map(X3_GOLD),
        "constraint": 'Add an image "none.png" ... to slide 2 with 1cm*1cm size',
        "violation": "放入的不是 none.png，但尺寸/位置/文本/页数/形状数完全一致",
    })

    z5 = zipfile.ZipFile(X5_GOLD)
    media5 = sorted(n for n in z5.namelist() if n.startswith("ppt/media/"))
    assert len(media5) == 6, media5
    m1, m2 = "ppt/media/image1.png", "ppt/media/image2.png"
    assert m1 in media5 and m2 in media5
    b1, b2 = z5.read(m1), z5.read(m2)
    assert b1 != b2, "两张图不能相同"
    x5_ce = _build(X5_GOLD, {m1: b2, m2: b1})   # 内容对调，文件名不变
    c5, e5 = diff_parts(X5_GOLD.read_bytes(), x5_ce)
    (SF / "x5_counterexample.pptx").write_bytes(x5_ce)
    results.append({
        "name": "X5 · 第 25 行 · bf4e9888",
        "gold": X5_GOLD.name, "ce": "x5_counterexample.pptx",
        "action": f"把 {m1} 与 {m2} 的二进制对调（文件名/引用关系不变）",
        "changed": c5, "exclusive": e5, "media_map": slide_media_map(X5_GOLD),
        "constraint": "pic1.png 放第 1 页、pic2.png 放第 2 页……按数字顺序每页一张",
        "violation": "第 1 页与第 2 页的图片身份/顺序被调换，但页数、形状数、位置、文本全部不变",
    })

    lines = [
        "# B 类候选的反例验证（X3 / X5）",
        "",
        "> 此报告记录 OOXML 对照的构造过程。实际评分见 [PPTX 回归结果](pptx_regression.json)。",
        "",
        "> 目的：把「评测器不比对图片内容」从**读源码**推进到**可复现反例**。",
        "> 方法：只修改 `ppt/media/*.png` 的二进制，其余 OOXML 部件逐字节保持不变；",
        "> 由于 `compare_pptx_files` 从不读取图片二进制，反例在该评分器下应与金标同分。",
        "> 本验证**不安装 python-pptx、不改动 OSWorld 原始数据**，仅用 Python 标准库。",
        "",
        "## 源码依据",
        "",
        "`data/osworld/desktop_env/evaluators/metrics/slides.py`：",
        "",
        "| 位置 | 代码 | 与本题关系 |",
        "|---|---|---|",
        "| 第 130 行 | `if the_image.image.blob == modified_image.image.blob:` | 位于 `check_image_stretch_and_center`，**另一个函数**；本题 `func: compare_pptx_files`，不调用 |",
        "| 第 439–441 行 | `if shape1.shape_type == 13 ...: is_approximately_equal(width/height)` | 本题实际执行的图片检查：只比宽高 |",
        "| 第 425–437 行 | `... and examine_shape` | X3/X5 均为 `examine_shape: false`，位置/尺寸比对被关闭 |",
        "| 第 743–744 行 | `run1.part.blob.decode('utf-8')` | `run.part` 是文本 run 的 XML 部件，用于 `_extract_bullets`，**不是图片** |",
        "| 全文件 | 无其它 `image.blob` / `media/` 读取 | — |",
        "",
        "结论：`compare_pptx_files` 读取的是「页数 / 形状数量 / shape_type / left,top,width,height /",
        "文本 / 备注 / 字体 / 对齐 / 背景色」，**没有一项能识别图片是哪一张、按什么顺序**。",
        "",
    ]
    for r in results:
        lines += [
            "---",
            "",
            f"## {r['name']}",
            "",
            f"- 金标：`{r['gold']}`；反例：`{r['ce']}`",
            f"- 构造：{r['action']}",
            f"- 题目约束：{r['constraint']}",
            f"- **反例违反的约束**：{r['violation']}",
            "",
            "金标各页的图片引用：",
            "",
            "| slide | 引用的 media |",
            "|---|---|",
        ]
        lines += [f"| `{s}` | `{t}` |" for s, t in r["media_map"].items()]
        lines += [
            "",
            f"**逐部件比对结果**：内容不同的部件 = `{r['changed']}`；",
            f"仅单侧存在的部件 = `{r['exclusive'] or '无'}`。",
            "",
            "> 变化**只发生在 `ppt/media/` 的二进制**；所有 `ppt/slides/*.xml`、",
            "> `ppt/slides/_rels/*`、备注、主题等被评分器读取的部件均逐字节一致。",
            "> 因此在 `compare_pptx_files` 下，反例与金标的比较结果不变（仍判通过），",
            "> 而题目要求的图片身份 / 顺序已被违反 → 支持 B 类 `CONSTRAINT_NOT_VERIFIED`。",
            "",
        ]

    lines += [
        "---",
        "",
        "## 验证边界（必须如实说明）",
        "",
        "1. 这是 **OOXML 层面的等价性论证 + 源码读取范围举证**，不是真机运行 OSWorld 评分器。",
        "   原因是本机未安装 `python-pptx`，且本轮不改动你的 Python 环境。",
        "2. 若要升级为「已确认」而非「候选」，下一步可安装 `python-pptx` 后直接调用",
        "   `compare_pptx_files(gold, counterexample, **options)`，断言返回 1，即可形成端到端证据。",
        "3. 金标 pptx 来自 HuggingFace `xlangai/ubuntu_osworld_file_cache`（OSWorld 官方缓存），",
        "   仅用于本地验证，未改动 `data/osworld/` 中的任何原始题目。",
        "",
        "→ 因此台账中 X3 / X5 仍标为 **B 类候选**，不升格为「已确认」。",
        "",
        "复现：`python verify_b_counterexample.py`",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print("=" * 70)
    print("B 类候选反例验证（仅改 media 二进制，其余部件逐字节不变）")
    print("=" * 70)
    for r in results:
        print(f"{r['name']}")
        print(f"  构造: {r['action']}")
        print(f"  变化部件: {r['changed']}")
        print(f"  单侧部件: {r['exclusive'] or '无'}")
        ok = all(c.startswith("ppt/media/") for c in r["changed"]) and not r["exclusive"]
        print(f"  => {'PASS: 变化仅限 media' if ok else 'FAIL: 存在非 media 变化'}")
    print("-" * 70)
    print(f"已生成：{OUT.relative_to(ROOT)}")
    print("已生成：data/sample_files/x3_counterexample.pptx, x5_counterexample.pptx")


if __name__ == "__main__":
    main()
