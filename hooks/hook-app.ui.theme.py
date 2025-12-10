# Hook para PyInstaller: incluye todos los submódulos dentro de app.ui.theme
from PyInstaller.utils.hooks import collect_submodules

# Collect all submodules under the theme package so dynamic imports via importlib work.
hiddenimports = collect_submodules('app.ui.theme') or []