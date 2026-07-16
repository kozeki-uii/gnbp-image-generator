# Security Policy / 安全策略

## 中文

GNBP 在本地处理 API Key、提示词和参考图片。提交安全问题时，请勿在
Issue、日志或截图中粘贴真实 API Key、私有端点凭据或个人图片。

当前版本为了兼容用户提供的中转服务，会关闭 HTTPS 证书验证。该行为已在
README 中明确说明，使用者应仅连接可信端点并尽量使用可信网络。

发现安全问题时，请优先使用 GitHub 的私密安全报告功能。如果该功能不可用，
可以创建不包含敏感细节的 Issue，请维护者建立私密沟通渠道。

## English

GNBP handles API keys, prompts, and reference images locally. Never include real
API keys, private endpoint credentials, or personal images in issues, logs, or
screenshots.

The current release disables HTTPS certificate verification for compatibility
with user-provided relay services. This behavior is documented in the README.
Only connect to trusted endpoints, preferably over a trusted network.

Report vulnerabilities through GitHub private vulnerability reporting when it
is available. Otherwise, open an issue without sensitive details and ask the
maintainer to establish a private communication channel.
