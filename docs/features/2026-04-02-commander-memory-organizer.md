# Memory Organizer（记忆文件索引器）

- 日期：`2026-04-02`
- 来源：`archive/nightly-sidequests/2026-04-02-commander-memory-organizer`

## 功能简介
解析并索引 memory 文件，支持搜索、提及追踪与摘要。

## 背景 / 目的
提升历史会话可检索性与结构化程度。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-02-commander-memory-organizer`
- 文件列表：
  - `README.md`
  - `memory_organizer.py`
  - `test_tool.sh`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-02-commander-memory-organizer/memory_organizer.py summary
python3 archive/nightly-sidequests/2026-04-02-commander-memory-organizer/memory_organizer.py search --query project
```

## 产出与状态
- 产出：summary 报告 / 检索结果 / mentions 统计。
- 状态：✅ 已归档（README 含示例）

## 后续迭代建议
- 引入增量索引缓存
- 支持标签体系与语义检索
- 补充单元测试
