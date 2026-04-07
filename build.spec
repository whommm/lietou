# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置
使用方法: pyinstaller build.spec
"""

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 收集需要的数据文件
datas = []
datas += collect_data_files('certifi')
datas += collect_data_files('lxml')
datas += collect_data_files('trafilatura')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'openai',
        'pyperclip',
        'tavily',
        'trafilatura',
        'lxml',
        'lxml.etree',
        'certifi',
        'charset_normalizer',
        'courlan',
        'htmldate',
        'justext',
        'urllib3',
        'httpx',
        'requests',
        'tiktoken',
        'playwright',
        'openpyxl',
        'et_xmlfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    # win_private_assemblies removed in PyInstaller 6.0+
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
    name='智能岗位分析助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标路径，如 'assets/icon.ico'
)
