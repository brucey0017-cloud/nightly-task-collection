# API Health Checker（接口健康探针）

- 日期：`2026-04-02`
- 来源：`archive/nightly-tools/2026-04-02-api-health-checker`

## 功能简介
检测 API 的 HTTP 状态、JSON 可解析性与响应时延。

## 背景 / 目的
为 on-call 场景提供最小可运行（MVB）健康巡检脚本。

## 目录与文件
- 根目录：`archive/nightly-tools/2026-04-02-api-health-checker`
- 文件列表：
  - `README.md`
  - `api_pulse.py`
  - `pulse.py`
  - `sample-config.txt`

## 用法 / 测试方法
```bash
python3 archive/nightly-tools/2026-04-02-api-health-checker/api_pulse.py --file archive/nightly-tools/2026-04-02-api-health-checker/sample-config.txt
python3 archive/nightly-tools/2026-04-02-api-health-checker/pulse.py https://api.example.com/health
```

## 产出与状态
- 产出：按 FAIL/SLOW/HEALTHY 分组的终端报告 + exit code。
- 状态：✅ 已归档（双版本脚本）

## 后续迭代建议
- 增加并发请求与重试策略
- 支持结果写入 JSON
- 支持 webhook 告警
