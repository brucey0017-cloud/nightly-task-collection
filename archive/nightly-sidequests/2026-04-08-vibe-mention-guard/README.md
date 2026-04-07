# Mention Guard (Sidequest)

一个零依赖 Python 小工具：检查文案里出现团队别名/头衔时，是否在**同一行**带了必需的 Discord 用户 mention（`<@USER_ID>`）。

## Why
夜间协作里最容易漏掉的不是观点，是 mention 格式。漏了就会派单失联。

## Quick start

```bash
python3 mention_guard.py --text "首席技术看一下"
python3 mention_guard.py --text "<@1470705448343830539>（首席技术）看一下"
python3 mention_guard.py /path/to/file.md
python3 mention_guard.py /path/to/dir --recursive --ext .md,.txt
```

## Exit code
- `0`: 无违规
- `1`: 发现违规
- `2`: 参数错误或读取失败

## Current built-in rules
- commander → `<@1470262775006625990>`
- maker → `<@1470705448343830539>`
- vibe → `<@1470708702116974761>`
- killjoy → `<@1470710750912970915>`
- main/阿爪 → `<@1476127054469533748>`

别名词表在 `mention_guard.py` 的 `RULES` 常量里，可直接改。
