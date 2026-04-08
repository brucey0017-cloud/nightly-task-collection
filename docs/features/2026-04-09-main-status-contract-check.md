# status-contract-check

- 日期：`2026-04-09`
- 模块：`安全与风险属性`
- 来源：`archive/nightly-sidequests/2026-04-09-main-status-contract-check`

## 功能简介
Zero-dependency Python 3 CLI for auditing the `nightly-lab` sidequest lifecycle contract from `current-run.json` plus its `status.jsonl`.

## 背景/目的
该页面用于沉淀 `2026-04-09-main-status-contract-check` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-09-main-status-contract-check`
- 文件列表：
  - `README.md`
  - `acpx-task.txt`
  - `status_contract_check.py`

## 用法/测试方法
```bash
python3 status_contract_check.py
python3 status_contract_check.py --agent main
python3 status_contract_check.py --strict
python3 status_contract_check.py --current-run /root/.openclaw/workspace/nightly-lab/runs/2026-04-09/run.json --json
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-09-main-status-contract-check/status_contract_check.py --current-run /root/.openclaw/workspace/nightly-lab/runs/2026-04-09/run.json --agent vibe
```

## 产出与状态
- 产出：已归档文件数：`3`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
