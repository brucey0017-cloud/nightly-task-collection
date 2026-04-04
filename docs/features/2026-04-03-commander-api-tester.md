# API Tester（接口回归脚本）

- 日期：`2026-04-03`
- 来源：`archive/nightly-sidequests/2026-04-03-commander-api-tester`

## 功能简介
按 JSON 配置批量执行 API 请求并产出测试报告。

## 背景 / 目的
给 commander 提供轻量接口回归工具，降低临时验证成本。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-03-commander-api-tester`
- 文件列表：
  - `README.md`
  - `api_tester.py`
  - `sample_config.json`
  - `sample_config_report.txt`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-03-commander-api-tester/api_tester.py archive/nightly-sidequests/2026-04-03-commander-api-tester/sample_config.json
```

## 产出与状态
- 产出：终端实时结果 + sample_config_report.txt。
- 状态：✅ 已归档（含示例配置）

## 后续迭代建议
- 支持断言规则（JSONPath）
- 增加重试与并发
- 输出 JUnit XML 便于 CI 集成
