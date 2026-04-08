# status-lens

- 日期：`2026-04-09`
- 模块：`设计与内容属性`
- 来源：`archive/nightly-sidequests/2026-04-09-vibe-status-lens`

## 功能简介
Tiny zero-dependency CLI to inspect `nightly-lab` `status.jsonl` progress.

## 背景/目的
该页面用于沉淀 `2026-04-09-vibe-status-lens` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-09-vibe-status-lens`
- 文件列表：
  - `README.md`
  - `status_lens.py`

## 用法/测试方法
```bash
python3 status_lens.py
python3 status_lens.py --task sidequest
python3 status_lens.py --json
python3 status_lens.py --status-file /path/to/status.jsonl
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
