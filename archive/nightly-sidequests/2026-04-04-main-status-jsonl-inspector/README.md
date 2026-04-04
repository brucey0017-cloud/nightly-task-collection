# status-jsonl-inspector

一个零依赖 Python 3 小工具，用来快速看懂 `status.jsonl`：

- 事件总数
- 每个 agent 的事件数
- 每个 `(agent, task)` 当前最新 stage
- 支持过滤 `--agent / --task / --stage / --since`
- 支持 `--json` 输出

## 文件

- `status_jsonl_inspector.py`：CLI 脚本

## 用法

默认读取：
`/root/.openclaw/workspace/nightly-lab/runs/2026-04-04/status.jsonl`

```bash
python3 status_jsonl_inspector.py
```

指定文件：

```bash
python3 status_jsonl_inspector.py --file /path/to/status.jsonl
```

按条件过滤：

```bash
python3 status_jsonl_inspector.py --agent main --task sidequest
python3 status_jsonl_inspector.py --stage done
python3 status_jsonl_inspector.py --since 2026-04-03T20
```

JSON 输出：

```bash
python3 status_jsonl_inspector.py --json
```

## 示例输出（文本）

```text
Status JSONL Inspector
Source: /root/.openclaw/workspace/nightly-lab/runs/2026-04-04/status.jsonl
Filters: agent=*, task=*, stage=*, since=*

Total events: 12

Per-agent counts:
  - main: 3
  - commander: 3
  - vibe: 3
  - killjoy: 3

Latest stage per (agent, task):
  - (commander, sidequest): done @ 2026-04-03T20:10:00Z
  - (main, sidequest): artifact @ 2026-04-03T20:31:18Z
```

## 设计说明

- 只用标准库，便于 cron / 临时环境直接跑。
- 对坏行（非 JSON）容错：跳过继续处理。
- `--since` 使用时间戳前缀匹配（ISO 字符串前缀），简单可靠。
