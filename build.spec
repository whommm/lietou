# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller packaging configuration.

Usage:
    .venv38\Scripts\python.exe -m PyInstaller build.spec --clean --noconfirm
"""

import os

from PyInstaller.utils.hooks import collect_data_files


BASE_DIR = os.path.abspath(SPECPATH)
SRC_DIR = os.path.join(BASE_DIR, "src")
VENV_SITE_PACKAGES = os.path.join(BASE_DIR, ".venv38", "Lib", "site-packages")

block_cipher = None

datas = []
datas += collect_data_files("certifi")
datas += collect_data_files("customtkinter")
datas += collect_data_files("lxml")
datas += collect_data_files("trafilatura")

datas.append((os.path.join(BASE_DIR, "config.json"), "."))
datas.append((os.path.join(BASE_DIR, "config.json.example"), "."))

hiddenimports = [
    # Local packages
    "src",
    "src.core",
    "src.ui",
    "src.models",
    "src.utils",
    "src.ui.themes",
    "src.ui.main_window",
    "src.ui.job_analysis_widget",
    "src.ui.batch_match_widget",
    "src.ui.greeting_generator_widget",
    "src.ui.candidate_library_widget",
    "src.ui.search_strategy_widget",
    "src.ui.match_criteria_widget",
    "src.ui.match_criteria_editor",
    "src.ui.resume_match_widget",
    "src.ui.selector_dialog",
    "src.ui.task_panel",
    "src.ui.html_renderer",
    "src.ui.history_widget",
    "src.ui.history_picker",
    "src.ui.company_research_widget",
    "src.core.config",
    "src.core.llm_client",
    "src.core.database",
    "src.core.history",
    "src.core.analysis_history_repository",
    "src.core.candidate_excel_service",
    "src.core.batch_match_service",
    "src.core.greeting_text_generation_service",
    "src.core.auto_greeting_service",
    "src.core.match_criteria_service",
    "src.core.search_strategy_service",
    "src.core.search_strategy_generation_service",
    "src.core.search_task_repository",
    "src.core.liepin_browser",
    "src.core.liepin_search_service",
    "src.core.liepin_search_task_service",
    "src.core.liepin_resume_extractor",
    "src.core.company_research_client",
    "src.core.task_queue",
    "src.core.prompt",
    "src.models.candidate",
    "src.models.candidate_excel",
    "src.models.batch_match",
    "src.models.match_criteria",
    "src.models.search_task",
    "src.utils.city_data",
    "src.utils.text_normalizer",
    "src.utils.html_sanitizer",
    "src.utils.helpers",
    # Third-party packages used by the desktop app.
    "customtkinter",
    "openai",
    "pyperclip",
    "tavily",
    "trafilatura",
    "lxml",
    "lxml.etree",
    "lxml.html",
    "lxml.html.clean",
    "certifi",
    "charset_normalizer",
    "courlan",
    "htmldate",
    "justext",
    "urllib3",
    "httpx",
    "requests",
    "tiktoken",
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    "openpyxl",
    "et_xmlfile",
    "PIL",
    "PIL._imagingtk",
    "PIL._tkinter_finder",
    "darkdetect",
    "tkinterweb",
    "tkinterweb.bindings",
    "markdown",
    "sqlite3",
    # setuptools/pkg_resources vendors jaraco and backports. In frozen mode the
    # vendor importer needs the concrete vendored modules present in the PYZ.
    "pkg_resources._vendor.jaraco",
    "pkg_resources._vendor.jaraco.context",
    "pkg_resources._vendor.jaraco.functools",
    "pkg_resources._vendor.jaraco.text",
    "pkg_resources._vendor.backports",
    "pkg_resources._vendor.backports.tarfile",
]

a = Analysis(
    ["main.py"],
    pathex=[
        BASE_DIR,
        SRC_DIR,
        VENV_SITE_PACKAGES,
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        "torch",
        "tensorflow",
        "pytest",
        "_pytest",
    ],
    win_no_prefer_redirects=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="智能岗位分析助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
