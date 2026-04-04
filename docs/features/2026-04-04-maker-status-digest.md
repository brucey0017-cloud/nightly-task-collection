# Status Digest（日报摘要生成）

- 日期：`2026-04-04`
- 来源：`archive/nightly-sidequests/2026-04-04-maker-status-digest`

## 功能简介
解析 run status JSONL 并生成 STATUS_DIGEST.md。

## 背景 / 目的
用一份固定格式摘要代替人工翻日志，提高晨间接班效率。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-04-maker-status-digest`
- 文件列表：
  - `README.md`
  - `STATUS_DIGEST.md`
  - `status_digest.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-04-maker-status-digest/status_digest.py
```

## 产出与状态
- 产出：STATUS_DIGEST.md（总事件、分 agent、最新 stage、最近事件）。
- 状态：✅ 已归档（含产出样例）

## 后续迭代建议
- 支持模板化输出（简版/详版）
- 增加失败任务高亮
- 支持按日期批量生成
