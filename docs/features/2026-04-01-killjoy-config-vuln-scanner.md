# Config Vulnerability Scanner（配置漏洞扫描）

- 日期：`2026-04-01`
- 来源：`archive/nightly-sidequests/2026-04-01-killjoy-config-vuln-scanner`

## 功能简介
扫描配置文件中的硬编码密钥、危险权限、HTTP 明文等风险模式。

## 背景 / 目的
在配置进入生产前快速发现显著风险项。

## 目录与文件
- 根目录：`archive/nightly-sidequests/2026-04-01-killjoy-config-vuln-scanner`
- 文件列表：
  - `production.conf`
  - `test-config.conf`
  - `vuln-scanner.py`

## 用法 / 测试方法
```bash
python3 archive/nightly-sidequests/2026-04-01-killjoy-config-vuln-scanner/vuln-scanner.py archive/nightly-sidequests/2026-04-01-killjoy-config-vuln-scanner/
```

## 产出与状态
- 产出：按严重级别分组报告；存在高危时非零退出。
- 状态：✅ 已归档（含测试/生产配置样例）

## 后续迭代建议
- 增加 allowlist 降噪
- 支持 SARIF 输出
- 增加目录扫描排除规则
