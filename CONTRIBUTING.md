# Contributing / 贡献指南

## 中文

1. 从 `dev` 创建功能分支。
2. 不要提交 `GNBP_config.json`、API Key、生成图片或构建产物。
3. 保持 API 客户端行为兼容，并为行为修复添加离线测试。
4. 运行 `py -3.11 -m unittest discover -s tests -v`。
5. 将 Pull Request 合并目标设为 `dev`。

提交安全问题前请阅读 [SECURITY.md](SECURITY.md)。

## English

1. Create feature branches from `dev`.
2. Never commit `GNBP_config.json`, API keys, generated images, or build output.
3. Preserve API-client compatibility and add offline tests for behavioral fixes.
4. Run `py -3.11 -m unittest discover -s tests -v`.
5. Target pull requests at `dev`.

Read [SECURITY.md](SECURITY.md) before reporting security issues.
