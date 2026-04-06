# 🔪 Pre-Mortem Assumption Hunter

- 日期：`2026-04-07`
- 模块：`安全与风险属性`
- 来源：`archive/nightly-sidequests/2026-04-07-killjoy-premortem-cli`

## 功能简介
A zero-dependency Python 3 CLI tool that tears apart any plan/proposal by exposing hidden assumptions, weasel words, and the single most lethal question you should be asking.

## 背景/目的
该页面用于沉淀 `2026-04-07-killjoy-premortem-cli` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-07-killjoy-premortem-cli`
- 文件列表：
  - `README.md`
  - `premortem.py`
  - `sample-plan.md`

## 用法/测试方法
```bash
python3 premortem.py plan.md
python3 premortem.py plan.md --json
python3 premortem.py sample-plan.md
```

## 产出与状态
- 产出：已归档文件数：`3`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
