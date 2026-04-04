# Log Level Digest（日志级别摘要）

- 日期：`2026-04-01`
- 来源：`archive/nightly-sidequests/2026-04-01-main-log-level-digest`

## 功能简介
按日志级别统计总量并抽取最近 error/fatal 片段。

## 背景 / 目的
在夜间任务后快速评估日志健康度。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-01-main-log-level-digest`
- 文件列表：
  - `README.md`
  - `log_level_digest.py`
  - `sample.log`
  - `test-output.txt`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-01-main-log-level-digest/log_level_digest.py archive/nightly-sidequests/2026-04-01-main-log-level-digest/sample.log --json
```

## 产出与状态
- 产出：级别统计 + 最近高危日志片段。
- 状态：✅ 已归档（含 sample 与测试输出）

## 后续迭代建议
- 支持多文件聚合
- 增加时间窗口过滤
- 支持阈值告警退出码
