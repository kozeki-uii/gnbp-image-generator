# GNBP Image Generator

<p align="center">
  <img src="logo.png" width="128" alt="GNBP Image Generator">
</p>

一个本地运行的 Windows 图像生成客户端。界面基于
[`CookSleep/gpt_image_playground`](https://github.com/CookSleep/gpt_image_playground)
的前端构建，外层使用 PySide6 QtWebEngine 提供桌面窗口。

GNBP 是独立的非官方 API 客户端，不内置模型、API Key、调用额度或在线服务，
也不代表 OpenAI 或任何第三方中转服务。

## 主要功能

- 自定义 OpenAI 兼容 API URL、API Key 和模型
- 保存多个 API 配置并快速切换
- 支持 Images API 与 Responses API
- 文生图、图片编辑、多张参考图和批量生成
- 图库、任务卡片、大图预览、历史记录和本地收藏
- 参考图预览中的画笔遮罩编辑器
- 参数配置、尺寸、质量、输出格式和生成数量
- 设置、历史图片和任务数据保存在本机
- 默认界面缩放 125%，支持 `Ctrl++`、`Ctrl+-` 和 `Ctrl+0`
- 可选 Agent 模式

## 快速启动

系统需要安装 Python 3.11 或更高版本。

下载或克隆项目后，直接双击项目根目录中的：

```text
启动 GNBP.cmd
```

首次启动会自动创建 `.venv` 并安装依赖，可能需要几分钟。后续启动会直接打开
客户端，不会重复检查或安装依赖。

也可以手动运行：

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe main.py
```

## API 配置

打开客户端设置，新增一个 API 配置并填写：

- `API URL`：例如 `https://example.com/v1`
- `API Key`：由你使用的服务提供
- `Model`：服务支持的图像模型名称
- `API Mode`：普通图像接口选择 Images API，需要 Responses 工具调用时选择 Responses API

兼容地址可以填写为 `https://example.com` 或 `https://example.com/v1`。
桌面界面直接向所配置的服务发送请求，不经过额外的 GNBP 后端转发。

## 基本使用

1. 在设置中保存并选中 API 配置。
2. 在底部输入提示词，按需设置尺寸、质量、格式和生成数量。
3. 点击生成，任务和结果会显示在中间图库。
4. 上传图片即可作为参考图或编辑输入。
5. 点击参考图缩略图打开预览，再从预览操作中进入遮罩编辑。

遮罩不是首页上的独立文件选择功能。保存遮罩后，第一张编辑图会作为遮罩目标参与请求。

## Agent 模式

Agent 模式不是普通生图所必需的。它要求服务端同时支持：

- Responses API 文本推理
- `image_generation` 工具调用
- 可用于推理的文本模型

如果中转接口只提供图像模型，使用普通 Gallery 生图和编辑功能即可。

## 本地数据与安全

- API 配置、历史记录和图片数据保存在 QtWebEngine 的本地存储中。
- `GNBP_config.json`、`.env`、`.venv`、生成结果和打包产物已被 Git 忽略。
- API Key 为了重复使用会保存在本机，但没有使用硬件凭据保险库加密。
- 请只配置你信任的 API 地址，不要把包含 Key 的配置文件提交到仓库。
- 桌面壳仅加载项目内置前端，外部网页链接会交给系统浏览器打开。

## 测试

自动化测试不会调用真实图像 API：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
```

## 可选便携构建

本项目默认按完整源码运行，不提供 Windows 安装包。确实需要本地 EXE 时，可以双击：

```text
打包脚本.bat
```

它会在 `dist` 下生成一个 PyInstaller onedir 便携目录。程序文件已展开，因此日常启动
比单文件自解压 EXE 更快；`build` 和 `dist` 均不会提交到 Git。

## 前端更新

仓库中的 `web_dist` 是已经构建好的前端文件，当前基于 GPT Image Playground
`v0.7.3`。桌面性能改动保存在 `frontend-patches/desktop-performance.patch`。
更新上游前端时，应使用 `git apply --unidiff-zero` 应用该补丁（或手动迁移改动），
再运行测试和构建，最后用新的 `dist` 替换 `web_dist` 并保留上游 MIT 许可证。

## 项目结构

```text
main.py                 桌面程序入口
启动 GNBP.cmd           推荐的一键启动文件
ui/web_window.py        QtWebEngine 桌面窗口和本地前端服务
web_dist/               已构建的 GPT Image Playground 前端
core/                   旧版 Python API 客户端和任务模块
tests/                  离线自动化测试
make_icon.py            可复现的项目图标生成器
打包脚本.bat            可选便携 EXE 构建脚本
```

## 许可证与致谢

GNBP 自有源码使用 [MIT License](LICENSE)。前端衍生自 CookSleep 的 MIT 项目，
详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和
`web_dist/LICENSE-CookSleep.txt`。
