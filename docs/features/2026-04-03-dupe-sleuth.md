# DupeSleuth（重复文件侦测）

- 日期：`2026-04-03`
- 来源：`archive/nightly-tools/2026-04-03-dupe-sleuth`

## 功能简介
基于 SHA256 的精确重复文件识别，不执行删除。

## 背景 / 目的
给磁盘清理提供“可回看、可手动确认”的安全候选集。

## 目录与文件
- 根目录：`archive/nightly-tools/2026-04-03-dupe-sleuth`
- 文件列表：
  - `README.md`
  - `create_sample_input.py`
  - `dupe_sleuth.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-tools/2026-04-03-dupe-sleuth/create_sample_input.py /tmp/dupe-sample
python3 archive/nightly-tools/2026-04-03-dupe-sleuth/dupe_sleuth.py /tmp/dupe-sample --verbose
```

## 产出与状态
- 产出：重复组列表 + KEEP/DEL 建议 + 可回收空间估算。
- 状态：✅ 已归档（可运行）

## 后续迭代建议
- 增加按目录白名单/黑名单过滤
- 支持结果输出到 JSON
- 增加硬链接识别
