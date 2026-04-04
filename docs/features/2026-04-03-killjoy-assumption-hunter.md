# Assumption Hunter（假设风险扫描）

- 日期：`2026-04-03`
- 来源：`archive/nightly-sidequests/2026-04-03/killjoy`

## 功能简介
扫描文档中的“假设/过度自信/风险词”，输出风险等级报告。

## 背景 / 目的
提前暴露需求与方案中的隐性假设，减少后期返工。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-03/killjoy`
- 文件列表：
  - `README.md`
  - `assumption_hunter.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-03/killjoy/assumption_hunter.py .
python3 archive/nightly-sidequests/2026-04-03/killjoy/assumption_hunter.py . --output report.md
```

## 产出与状态
- 产出：Markdown 风险报告（高/中风险分层）。
- 状态：✅ 已归档（可运行）

## 后续迭代建议
- 接入 PR 文档自动扫描
- 支持中文风险词库
- 增加项目级趋势统计
