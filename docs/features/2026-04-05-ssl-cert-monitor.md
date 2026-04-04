# SSL Cert Monitor

- 日期：`2026-04-05`
- 模块：`监控观测属性`
- 来源：`archive/nightly-tools/2026-04-05-ssl-cert-monitor`

## 功能简介
Quick Python 3 (stdlib-only) CLI to check certificate expiration for: - HTTPS endpoints (`https://...`) - Local certificate files (`.pem`, `.crt`, `.cer`)

## 背景/目的
该页面用于沉淀 `2026-04-05-ssl-cert-monitor` 的用途、运行方式和交付状态，避免夜间任务信息散落。

## 目录与文件
- 根目录：`archive/nightly-tools/2026-04-05-ssl-cert-monitor`
- 文件列表：
  - `README.md`
  - `example-targets.txt`
  - `sample_targets.txt`
  - `ssl_cert_monitor.py`
  - `ssl_check.py`

## 用法/测试方法
```bash
python3 ssl_cert_monitor.py https://sha256.badssl.com https://expired.badssl.com
python3 ssl_cert_monitor.py --input-file sample_targets.txt
python3 ssl_cert_monitor.py --warn-days 14 --timeout 8 https://sha256.badssl.com
python3 ssl_cert_monitor.py --input-file sample_targets.txt --warn-days 30 --timeout 5
```

## 产出与状态
- 产出：已归档文件数：`5`。
- 状态：✅ 已归档（自动生成）

## 后续迭代建议
- 补充更清晰的输入/输出示例，降低接手成本。
- 增加自动化测试或最小 smoke 命令，提升可回归性。
- 根据实际使用频次，评估是否需要接入 CI 定时巡检。
