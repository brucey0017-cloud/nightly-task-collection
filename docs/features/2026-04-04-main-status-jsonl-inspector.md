# Status JSONL Inspector（状态流检查器）

- 日期：`2026-04-04`
- 来源：`archive/nightly-sidequests/2026-04-04-main-status-jsonl-inspector`

## 功能简介
对 status.jsonl 做快速结构化汇总，支持 agent/task/stage/since 过滤。

## 背景 / 目的
让 main 能快速判断夜间流程是否推进、卡在哪个阶段。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-04-main-status-jsonl-inspector`
- 文件列表：
  - `README.md`
  - `status_jsonl_inspector.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-04-main-status-jsonl-inspector/status_jsonl_inspector.py
python3 archive/nightly-sidequests/2026-04-04-main-status-jsonl-inspector/status_jsonl_inspector.py --json
```

## 产出与状态
- 产出：文本或 JSON 汇总：事件数、agent 分布、最新 stage。
- 状态：✅ 已归档（可直接运行）

## 后续迭代建议
- 增加 stage 耗时计算
- 支持多文件合并分析
- 增加异常 stage 规则告警
