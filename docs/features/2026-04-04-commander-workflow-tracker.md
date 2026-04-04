# Workflow Tracker（团队任务追踪器）

- 日期：`2026-04-04`
- 来源：`archive/nightly-sidequests/2026-04-04-commander-workflow-tracker`

## 功能简介
用于团队任务分配、状态更新、成员负载统计与摘要导出的轻量脚手架。

## 背景 / 目的
给 commander 提供侧任务中的协作可视化基础设施。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-04-commander-workflow-tracker`
- 文件列表：
  - `demo.py`
  - `demo_summary.json`
  - `workflow_tracker.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-04-commander-workflow-tracker/demo.py
python3 archive/nightly-sidequests/2026-04-04-commander-workflow-tracker/workflow_tracker.py dashboard
```

## 产出与状态
- 产出：demo_summary.json + 终端 dashboard（按状态/成员聚合）。
- 状态：✅ 已归档（含 demo 与报告）

## 后续迭代建议
- 将存储从 /tmp 切到项目内 data/
- 补齐 CLI 子命令帮助与参数校验
- 增加 CSV 导出与 web 视图
