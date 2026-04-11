# json-delta

- 日期：`2026-04-12`
- 模块：`工具属性`
- 来源：`archive/nightly-tools/2026-04-12-json-delta`

## 功能简介
Semantic JSON diff CLI for quick before/after checks.

## 背景/目的
该页面用于沉淀 `2026-04-12-json-delta` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-tools/2026-04-12-json-delta`
- 文件列表：
  - `README.md`
  - `json-delta`

## 用法/测试方法
```bash
./json-delta <file_a> <file_b> [--mode detail|summary] [--exit-code]
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json b.json
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json b.json --mode summary
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json b.json --exit-code; echo "exit: $?"
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json a.json --exit-code; echo "exit: $?"
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json bad.json --exit-code; echo "exit: $?"
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
