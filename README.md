# GNBP Image Generator

Windows desktop image playground based on the React interface from
[`CookSleep/gpt_image_playground`](https://github.com/CookSleep/gpt_image_playground).

GNBP is an independent, unofficial API client. It does not include an image
model, API quota, API key, or third-party service endorsement.

## Features

- Original GPT Image Playground gallery, composer, task cards, history, lightbox, and settings UI
- OpenAI-compatible Images API and Responses API modes
- Custom API URL, API key, model, and multiple saved profiles
- Image generation, editing, multiple reference images, mask editor, and batch generation
- Local IndexedDB/localStorage persistence for settings, history, images, and collections
- 110% default UI scale with `Ctrl++`, `Ctrl+-`, and `Ctrl+0`; the selected scale is remembered
- Optional Agent mode when the provider supports Responses API text reasoning and the `image_generation` tool

## Run Locally

Create the local environment once:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then start the app from the project directory:

```powershell
.venv\Scripts\pythonw.exe main.py
```

The application stores its browser data under the current user's application
data directory. API keys remain local and are not committed to this repository.
Like most local API clients, keys are stored for reuse rather than protected by
a hardware-backed credential vault.

## API Compatibility

OpenAI-compatible base URLs may be entered as either `https://host` or
`https://host/v1`. Direct requests are sent by the trusted local desktop UI,
without browser CORS restrictions.

Agent mode is optional. It requires an endpoint and text model that implement
Responses API tool calls with `image_generation`. A provider that only exposes
an image model can still use the normal Gallery workflow.

## Development

The desktop shell uses PySide6 QtWebEngine, while the bundled interface is built
from the local `CookSleep/gpt_image_playground` checkout.

```powershell
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
```

To refresh `web_dist`, check out the upstream repository, build it, and copy its
`dist` output into this repository:

```powershell
cd gpt_image_playground
npm run build
```

`打包脚本.bat` is optional. It creates a local portable application directory
under `dist`; it does not create or install a Windows setup package.

## License

GNBP source code is released under the [MIT License](LICENSE). The bundled web
interface is derived from CookSleep's MIT-licensed project; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and
`web_dist/LICENSE-CookSleep.txt`.
