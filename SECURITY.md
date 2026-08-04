# Security Policy / 安全策略

## 中文

GNBP 在本地 WebEngine 配置中处理 API Key、提示词和参考图片。提交安全问题时，请勿在
Issue、日志或截图中粘贴真实 API Key、私有端点凭据或个人图片。

桌面壳只加载随程序打包的本地前端，并允许该可信前端直连用户配置的 API，
以避免浏览器 CORS 限制。不要在程序内导航或加载不可信网页。

当前版本默认启用 HTTPS 证书验证。请不要为了绕过无效证书而关闭安全校验，
应要求 API 服务方修复证书配置。

发现安全问题时，请优先使用 GitHub 的私密安全报告功能。如果该功能不可用，
可以创建不包含敏感细节的 Issue，请维护者建立私密沟通渠道。

## English

GNBP handles API keys, prompts, and reference images in a local persistent
WebEngine profile. Never include real
API keys, private endpoint credentials, or personal images in issues, logs, or
screenshots.

The shell only loads its bundled local frontend and permits that trusted UI to
contact user-configured API endpoints without browser CORS restrictions. Do not
navigate the embedded engine to untrusted websites.

The current release enables HTTPS certificate verification by default. Use a
valid HTTPS endpoint instead of disabling certificate validation.

Report vulnerabilities through GitHub private vulnerability reporting when it
is available. Otherwise, open an issue without sensitive details and ask the
maintainer to establish a private communication channel.
