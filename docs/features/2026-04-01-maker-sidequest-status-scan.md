# Sidequest Status Scan（侧任务状态扫描）

- 日期：`2026-04-01`
- 来源：`archive/nightly-sidequests/2026-04-01-maker-sidequest-status-scan`

## 功能简介
扫描 sidequest 报告目录并汇总状态与产出项。

## 背景 / 目的
给 maker 提供 nightly sidequest 执行可见性。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-01-maker-sidequest-status-scan`
- 文件列表：
  - `README.md`
  - `sidequest_status.py`
  - `summary-2026-04-01.json`
  - `summary-2026-04-01.txt`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-01-maker-sidequest-status-scan/sidequest_status.py --date 2026-04-01 --format text
python3 archive/nightly-sidequests/2026-04-01-maker-sidequest-status-scan/sidequest_status.py --date 2026-04-01 --format json
```

## 产出与状态
- 产出：文本摘要或 JSON 汇总。
- 状态：✅ 已归档（含 json/txt 样例）

## 后续迭代建议
- 支持跨日期趋势视图
- 增加异常缺失报告
- 支持 markdown dashboard 输出
