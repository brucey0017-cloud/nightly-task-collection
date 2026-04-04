# Memory File Organizer

- 日期：`2026-04-02`
- 模块：`工具属性`
- 来源：`archive/nightly-sidequests/2026-04-02-commander-memory-organizer`

## 功能简介
A Python tool for parsing, indexing, and searching OpenClaw memory files.

## 背景/目的
该页面用于沉淀 `2026-04-02-commander-memory-organizer` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-02-commander-memory-organizer`
- 文件列表：
  - `README.md`
  - `memory_organizer.py`
  - `test_tool.sh`

## 用法/测试方法
```bash
python3 memory_organizer.py summary
python3 memory_organizer.py search --query "your search term"
python3 memory_organizer.py mentions --user-id "USER_ID"
python3 memory_organizer.py index
python3 memory_organizer.py mentions --user-id "1470262775006625990"
python3 memory_organizer.py search --query "project"
python3 memory_organizer.py search --query "technical"
python3 memory_organizer.py summary --output-format json
```

## 产出与状态
- 产出：已归档文件数：`3`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
