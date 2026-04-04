# log_level_digest.py

- 日期：`2026-04-01`
- 模块：`监控观测属性`
- 来源：`archive/nightly-sidequests/2026-04-01-main-log-level-digest`

## 功能简介
A tiny Python 3 zero-dependency utility that digests a log file by level.

## 背景/目的
该页面用于沉淀 `2026-04-01-main-log-level-digest` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-01-main-log-level-digest`
- 文件列表：
  - `README.md`
  - `log_level_digest.py`
  - `sample.log`
  - `test-output.txt`

## 用法/测试方法
```bash
python3 log_level_digest.py sample.log
python3 log_level_digest.py sample.log -n 5
python3 log_level_digest.py sample.log --json
```

## 产出与状态
- 产出：已归档文件数：`4`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
