# Development Guide

## Architecture

`main.py` creates the Qt application and `MainWindow`. The UI snapshots each
request into `GenConfig` and sends it to `TaskManager`. Background workers route
the task to the Gemini or GPT-compatible client, save the returned image through
`ImageUtils`, and emit Qt signals back to the UI.

Key modules:

- `app_info.py`: application name, version, title, and executable name
- `config/config_mgr.py`: local profiles, prompt presets, settings, and task data
- `core/api_client.py`: Gemini-compatible requests
- `core/gpt_client.py`: OpenAI-compatible generation and edit requests
- `core/task_queue.py`: background worker pool and concurrency control
- `core/utils.py`: image encoding, collision-safe saving, and metadata
- `ui/main_window.py`: PySide6 user workflow
- `ui/themes.py`: QSS themes and runtime control assets

## Commands

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 main.py
py -3.11 -m unittest discover -s tests -v
py -3.11 -m PyInstaller build.spec --clean --noconfirm
```

Tests must remain offline. Real API probes, local configuration, generated
images, and packaged executables are intentionally excluded from Git.

## Versioning

Change only `APP_VERSION` in `app_info.py`. The window title, Qt application
version, build output name, and batch build messages derive from it.

## Branches

- `main`: stable releases
- `dev`: active development and pull-request target

Keep `main` releasable and merge verified `dev` changes by fast-forward when
possible.
