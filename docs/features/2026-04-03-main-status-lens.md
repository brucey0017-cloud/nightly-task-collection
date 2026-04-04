# Status Lens（状态时间线透镜）

- 日期：`2026-04-03`
- 来源：`archive/nightly-sidequests/2026-04-03-main-status-lens`

## 功能简介
从 status.jsonl 提取每个 agent/task 的阶段时间线与最新快照。

## 背景 / 目的
帮助 main 一眼判断夜间流程推进轨迹。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-03-main-status-lens`
- 文件列表：
  - `README.md`
  - `sample.json`
  - `status_lens.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-03-main-status-lens/status_lens.py --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-03/status.jsonl
```

## 产出与状态
- 产出：文本或 JSON 视图（timeline + latest stage）。
- 状态：✅ 已归档（可运行）

## 后续迭代建议
- 支持 stage 耗时排行榜
- 增加异常 stage 自动提示
- 支持跨 run 对比
