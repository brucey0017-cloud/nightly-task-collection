# premortem — KILLJOY's Pre-Mortem Attack Tool 🔪

- 日期：`2026-04-10`
- 模块：`安全与风险属性`
- 来源：`archive/nightly-sidequests/2026-04-10-killjoy-premortem-cli`

## 功能简介
A zero-dependency Python 3 CLI that reads any plan document (markdown) and generates a structured pre-mortem analysis using the **5-Layer Attack Framework**.

## 背景/目的
该页面用于沉淀 `2026-04-10-killjoy-premortem-cli` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-10-killjoy-premortem-cli`
- 文件列表：
  - `README.md`
  - `premortem.py`
  - `test-plan.md`

## 用法/测试方法
```bash
python3 premortem.py plan.md
python3 premortem.py plan.md --json
python3 premortem.py plan.md --layer 3
python3 premortem.py plan.md --severity high
```

## 产出与状态
- 产出：已归档文件数：`3`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
