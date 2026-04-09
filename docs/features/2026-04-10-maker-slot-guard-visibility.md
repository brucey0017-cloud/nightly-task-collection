# Sidequest: slot-guard visibility

- 日期：`2026-04-10`
- 模块：`工具属性`
- 来源：`archive/nightly-sidequests/2026-04-10-maker-slot-guard-visibility`

## 功能简介
A small self-contained visibility helper for diagnosing why `agent_slot_guard.py` blocks sidequest start.

## 背景/目的
该页面用于沉淀 `2026-04-10-maker-slot-guard-visibility` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-10-maker-slot-guard-visibility`
- 文件列表：
  - `README.md`
  - `active-tasks.md`
  - `build_active_tasks.py`
  - `status-full.jsonl`
  - `status-tail-120.jsonl`

## 用法/测试方法
```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-10-maker-slot-guard-visibility/build_active_tasks.py
```

## 产出与状态
- 产出：已归档文件数：`5`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
