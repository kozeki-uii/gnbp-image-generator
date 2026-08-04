# Development Guide

## Architecture

`main.py` creates a PySide6 QtWebEngine desktop shell. `ui/web_window.py` serves
the bundled `web_dist` directory on loopback and renders it in a persistent
browser profile. The UI is the production build of CookSleep's GPT Image
Playground, so its gallery, API profiles, IndexedDB history, reference-image
workflow, mask editor, batching, and optional Agent mode remain intact.

Legacy Python API and Qt widget modules are retained for tests and migration,
but the shipping window is `WebMainWindow`.

## Commands

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
.venv\Scripts\python.exe -m PyInstaller build.spec --clean --noconfirm
```

`打包脚本.bat` is only a convenience wrapper for the optional portable onedir
build. The project does not produce a Windows installer.

## Frontend Updates

Build the local upstream checkout with `npm run build`, replace `web_dist` with
the resulting `dist` directory, and retain the upstream MIT license as
`web_dist/LICENSE-CookSleep.txt`. Run the upstream frontend tests before
updating the bundled files.

## Versioning

Change `APP_VERSION` in `app_info.py`. The optional portable build reads the
same version when naming its output directory and executable.

Tests must remain offline. Real API keys, local profiles, generated images, and
release binaries are excluded from Git.
