# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

如需报告安全漏洞，请发送邮件至 **2353404@qq.com**。

请勿在公开 Issue 中披露安全漏洞。我们会在 72 小时内回复确认，并在修复完成后公开致谢。

## Security Best Practices

- 所有 API 密钥通过 `.env` 文件管理，不在代码中硬编码
- `.env` 和 `.env.*` 文件已加入 `.gitignore`，不会提交到仓库
- 敏感配置使用 `.env.example` 作为模板参考
- haip-core 引擎不包含患者真实数据