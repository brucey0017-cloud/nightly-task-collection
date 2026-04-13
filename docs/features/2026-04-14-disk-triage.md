# disk-triage

- 日期：`2026-04-14`
- 模块：`工具属性`
- 来源：`archive/nightly-tools/2026-04-14-disk-triage`

## 功能简介
Find what is eating disk in 5 seconds.

## 背景/目的
该页面用于沉淀 `2026-04-14-disk-triage` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-tools/2026-04-14-disk-triage`
- 文件列表：
  - `README.md`
  - `disk_triage.py`

## 用法/测试方法
```bash
python3 disk_triage.py [path] [--top N] [--depth N] [--warn-mb N] [--json] [--no-color]
python3 disk_triage.py /tmp --top 10 --depth 2
python3 disk_triage.py / --warn-mb 500
python3 disk_triage.py /var --json | python3 -m json.tool | head -40
python3 disk_triage.py /tmp/triage-demo --top 5 --depth 2 --warn-mb 50
python3 disk_triage.py /tmp/triage-demo --json | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>0"
python3 disk_triage.py /tmp/triage-demo --depth 2 --top 5
```

## 产出与状态
- 产出：已归档文件数：`2`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
