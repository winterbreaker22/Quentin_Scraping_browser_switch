1.  Used multi-tasking for browser switch
    To implement it, get pid and hwnd of browsers

2.  To make exe, use pyinstaller.
    Steps:
    - Venv create
    - Activate it
    - pip install dependencies
    - pip install auto-py-to-exe
    - $env:PLAYWRIGHT_BROWSERS_PATH="0"; playwright install chromium
    - pip freeze
    - auto-py-to-exe
