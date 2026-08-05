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

Start from the CookSleep v0.7.3 checkout, apply
`frontend-patches/desktop-performance.patch` with `git apply --unidiff-zero`,
then run `npm test -- --run` and `npm run build`. Replace `web_dist` with the
resulting `dist` directory and retain the upstream MIT license as
`web_dist/LICENSE-CookSleep.txt`.

The desktop patch keeps the upstream visual structure while code-splitting
secondary tools, disabling Service Worker ownership inside QtWebEngine, and
reducing only the full-screen blur and scale animations that trigger expensive
page recomposition. It also carries the desktop clipboard/drop bridge and the
longer 4K-friendly timeout defaults. Small translucent controls, shadows, and
short modal motion remain enabled.

## Versioning

Change `APP_VERSION` in `app_info.py`. The optional portable build reads the
same version when naming its output directory and executable.

Tests must remain offline. Real API keys, local profiles, generated images, and
release binaries are excluded from Git.
