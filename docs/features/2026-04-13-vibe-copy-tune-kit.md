# Copy Tune Kit (VIBE Sidequest)

- 日期：`2026-04-13`
- 模块：`设计与内容属性`
- 来源：`archive/nightly-sidequests/2026-04-13-vibe-copy-tune-kit`

## 功能简介
一个零依赖小工具：快速扫出文案里的“企业宣传片腔调”和可读性风险。

## 背景/目的
该页面用于沉淀 `2026-04-13-vibe-copy-tune-kit` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-13-vibe-copy-tune-kit`
- 文件列表：
  - `README.md`
  - `microcopy_guard.py`
  - `sample_clean.txt`

## 用法/测试方法
```bash
python3 microcopy_guard.py README.md
python3 microcopy_guard.py /path/to/folder --max-line-len 65
```

## 产出与状态
- 产出：已归档文件数：`3`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
