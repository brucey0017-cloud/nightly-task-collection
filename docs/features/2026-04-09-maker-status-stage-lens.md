# status-stage-lens

- 日期：`2026-04-09`
- 模块：`监控观测属性`
- 来源：`archive/nightly-sidequests/2026-04-09-maker-status-stage-lens`

## 功能简介
Tiny Python 3 CLI that summarizes nightly-lab `status.jsonl` by stage, agent, and `(agent, task)` workflow timeline.

## 背景/目的
该页面用于沉淀 `2026-04-09-maker-status-stage-lens` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-09-maker-status-stage-lens`
- 文件列表：
  - `README.md`
  - `stage_lens.py`

## 用法/测试方法
```bash
python3 stage_lens.py
python3 stage_lens.py --task sidequest --agent maker
python3 stage_lens.py --stage start --stage done --json
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
