# status-jsonl-inspector

- 日期：`2026-04-04`
- 模块：`监控观测属性`
- 来源：`archive/nightly-sidequests/2026-04-04-main-status-jsonl-inspector`

## 功能简介
一个零依赖 Python 3 小工具，用来快速看懂 `status.jsonl`：

## 背景/目的
该页面用于沉淀 `2026-04-04-main-status-jsonl-inspector` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-04-main-status-jsonl-inspector`
- 文件列表：
  - `README.md`
  - `status_jsonl_inspector.py`

## 用法/测试方法
```bash
python3 status_jsonl_inspector.py
python3 status_jsonl_inspector.py --file /path/to/status.jsonl
python3 status_jsonl_inspector.py --agent main --task sidequest
python3 status_jsonl_inspector.py --stage done
python3 status_jsonl_inspector.py --since 2026-04-03T20
python3 status_jsonl_inspector.py --json
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
