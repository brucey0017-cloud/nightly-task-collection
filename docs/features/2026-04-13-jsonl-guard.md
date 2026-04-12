# jsonl-guard

- 日期：`2026-04-13`
- 模块：`工具属性`
- 来源：`archive/nightly-tools/2026-04-13-jsonl-guard`

## 功能简介
Fast JSONL validator for line-level correctness checks.

## 背景/目的
该页面用于沉淀 `2026-04-13-jsonl-guard` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-tools/2026-04-13-jsonl-guard`
- 文件列表：
  - `README.md`
  - `jsonl-guard`
  - `samples/invalid.jsonl`
  - `samples/valid.jsonl`
  - `tests/test_jsonl_guard.sh`

## 用法/测试方法
```bash
python3 ./jsonl-guard --help
python3 ./jsonl-guard ./samples/valid.jsonl
python3 ./jsonl-guard ./samples/invalid.jsonl; echo "exit: $?"
./tests/test_jsonl_guard.sh
python3 ./jsonl-guard <path-to-jsonl> [--max-errors N]
python3 ./jsonl-guard ./samples/invalid.jsonl --max-errors 50
```

## 产出与状态
- 产出：已归档文件数：`5`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
