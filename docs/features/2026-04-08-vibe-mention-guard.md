# Mention Guard (Sidequest)

- 日期：`2026-04-08`
- 模块：`设计与内容属性`
- 来源：`archive/nightly-sidequests/2026-04-08-vibe-mention-guard`

## 功能简介
一个零依赖 Python 小工具：检查文案里出现团队别名/头衔时，是否在**同一行**带了必需的 Discord 用户 mention（`<@USER_ID>`）。

## 背景/目的
该页面用于沉淀 `2026-04-08-vibe-mention-guard` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-08-vibe-mention-guard`
- 文件列表：
  - `README.md`
  - `mention_guard.py`

## 用法/测试方法
```bash
python3 mention_guard.py --text "首席技术看一下"
python3 mention_guard.py --text "<@1470705448343830539>（首席技术）看一下"
python3 mention_guard.py /path/to/file.md
python3 mention_guard.py /path/to/dir --recursive --ext .md,.txt
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
