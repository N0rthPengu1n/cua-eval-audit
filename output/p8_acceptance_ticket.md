# p8 标题样式评分误拒

**待实施 · A 类验收过严**

任务 `5c1a6c3d-c1b3-47cb-9b01-8d1b7544ffa1`，应用 LibreOffice Impress。原评测用 `or` 组合两个 PPTX 金标分支。 [任务配置](../data/osworld/evaluation_examples/examples/libreoffice_impress/5c1a6c3d-c1b3-47cb-9b01-8d1b7544ffa1.json) · [评分器实现](../data/osworld/desktop_env/evaluators/metrics/slides.py)

## 问题与影响

题目要求第 1 页文字加粗，标题为 44 pt 并加下划线。真实 Agent 产物满足样式要求，并将标题框高度保留在初始值 1,333,440 EMU。第一份金标的标题框高为 3,999,960 EMU。原评分的两个分支都给 0 分。只把 Agent 产物的标题框高度改成第一份金标的高度，该分支就给 1 分。 [真实运行记录](agent_run_01.md#p8-的误拒证据)

## 拟修复范围

在这道题的评分配置里，让第 1 页标题框高度可以保留初始值，也可以符合原金标。继续检查标题的粗体、字号、下划线，以及原有的其他形状几何和文本条件。先用下表验收，再接入常规评分。

| 验收输入 | 当前原评分 | 修复后预期 |
|---|---:|---:|
| [真实 Agent 产物](../data/sample_files/p8_title_style/agent_result.pptx)，标题样式正确，保留初始框高 | 0 | 1 |
| [缺下划线反例](../data/sample_files/p8_title_style/missing_underline.pptx)，保留 44 pt 和粗体 | 0 | 0 |
| 两份现有金标分别参与原有组合评分 | 1 | 1 |
| 在合格稿副本中改变其他形状的位置，使其超出原有几何容差 | 待加入回归 | 0 |

评测同学负责调整本题的判分配置并实现回归。数据质检同学逐项核对题面、合格稿和反例，确认通过的产物满足显式样式要求后再关闭工单。

## 复现当前误拒

在仓库根目录的隔离 Python 环境运行以下命令。`--fetch` 下载两份公开金标并校验 SHA-256。已有与资产清单一致的缓存时，也可直接运行脚本。

```bash
python -m pip install python-pptx==1.0.2
python verify_p8_regression.py --fetch
```

脚本核对真实产物的 SHA-256，分别输出两个原评分分支、临时关闭几何检查的诊断分数，以及仅修改标题框高度后的第一分支分数。临时关闭几何检查用于定位原因，工单的修复范围限定在本题第 1 页标题框的高度。 [逐题分数](agent_run_01.json) · [金标资产清单](pilot_review_assets.json)
