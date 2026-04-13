# status-flow-check

- 日期：`2026-04-14`
- 模块：`监控观测属性`
- 来源：`archive/nightly-sidequests/2026-04-14-maker-status-flow-check`

## 功能简介
Tiny Python 3 CLI for quick workflow visibility from nightly-lab `status.jsonl`.

## 背景/目的
该页面用于沉淀 `2026-04-14-maker-status-flow-check` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-14-maker-status-flow-check`
- 文件列表：
  - `README.md`
  - `status_flow_check.py`

## 用法/测试方法
```bash
python3 status_flow_check.py
python3 status_flow_check.py --agent maker --task sidequest
python3 status_flow_check.py --file /path/to/status.jsonl --json
python3 status_flow_check.py --agent maker --task sidequest | head -n 30
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
