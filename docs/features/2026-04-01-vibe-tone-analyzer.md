# Tone Analyzer（语气与节奏分析）

- 日期：`2026-04-01`
- 来源：`archive/nightly-sidequests/2026-04-01-vibe-tone-analyzer`

## 功能简介
对文案进行品牌语气 lint：禁词、弱词、句长节奏、可读性。

## 背景 / 目的
提升内容表达的一致性和可读性，降低“企业黑话”风险。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-01-vibe-tone-analyzer`
- 文件列表：
  - `README.md`
  - `tone_analyzer.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-01-vibe-tone-analyzer/tone_analyzer.py my_copy.txt
echo "sample text" | python3 archive/nightly-sidequests/2026-04-01-vibe-tone-analyzer/tone_analyzer.py
```

## 产出与状态
- 产出：文案 verdict（CORPORATE/ BORING / OK / SOLID）。
- 状态：✅ 已归档（可运行）

## 后续迭代建议
- 支持可配置词典
- 增加多语言模式
- 输出逐句建议与评分
