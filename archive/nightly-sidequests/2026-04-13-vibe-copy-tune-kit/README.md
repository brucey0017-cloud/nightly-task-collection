# Copy Tune Kit (VIBE Sidequest)

一个零依赖小工具：快速扫出文案里的“企业宣传片腔调”和可读性风险。

## 包含内容
- `microcopy_guard.py`：扫描 `.md/.txt/.rst` 文件，输出命中行号 + 改写方向

## 能抓什么
- 禁用词：赋能、一站式、全方位、极致体验、开启新篇章、引领未来、匠心打造
- 英文 AI 口头禅：Great question / I'd be happy to help / Absolutely
- 长句风险：默认单行超过 70 字符
- 语气噪音：感叹号过多
- 大段落可读性风险

## 用法
```bash
python3 microcopy_guard.py README.md
python3 microcopy_guard.py /path/to/folder --max-line-len 65
```

## 退出码
- `0`：未发现明显问题
- `1`：发现问题（适合挂到 pre-commit / CI）
