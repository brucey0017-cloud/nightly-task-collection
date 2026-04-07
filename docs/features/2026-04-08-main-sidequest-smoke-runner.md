# sidequest-smoke-runner

- 日期：`2026-04-08`
- 模块：`工具属性`
- 来源：`archive/nightly-sidequests/2026-04-08-main-sidequest-smoke-runner`

## 功能简介
Zero-dependency Python 3 CLI for validating `nightly-lab` sidequest reports and optionally running their declared smoke tests.

## 背景/目的
该页面用于沉淀 `2026-04-08-main-sidequest-smoke-runner` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-08-main-sidequest-smoke-runner`
- 文件列表：
  - `README.md`
  - `sidequest_smoke_runner.py`

## 用法/测试方法
```bash
python3 sidequest_smoke_runner.py --list
python3 sidequest_smoke_runner.py
python3 sidequest_smoke_runner.py --agent maker
python3 sidequest_smoke_runner.py --agent maker --run-tests --timeout 90
python3 sidequest_smoke_runner.py --report /root/.openclaw/workspace/nightly-lab/sidequests/2026-04-08/maker.md --run-tests
python3 sidequest_smoke_runner.py --agent maker --run-tests --json
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-08-main-sidequest-smoke-runner/sidequest_smoke_runner.py --agent maker --run-tests
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
