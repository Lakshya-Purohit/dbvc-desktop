# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DBVC Desktop.
Build with: pyinstaller build.spec
"""

import subprocess
import os

version = "0.0.0-dev"

# 1. Check GITHUB_REF_NAME for CI
if os.environ.get('GITHUB_REF_NAME'):
    version = os.environ.get('GITHUB_REF_NAME').lstrip('vV')
else:
    # 2. Try git describe
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        version = result.stdout.strip().lstrip('vV')
    except Exception as e:
        # 3. Fall back to existing version.txt
        try:
            with open('app/resources/version.txt', 'r') as f:
                version = f.read().strip().lstrip('vV')
        except Exception:
            pass

# Ensure app/resources exists and write version.txt
os.makedirs('app/resources', exist_ok=True)
with open('app/resources/version.txt', 'w', encoding='utf-8') as f:
    f.write(version)

print(f"--- Baked version {version} into app/resources/version.txt ---")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/resources/logo.png', 'app/resources'),
        ('app/resources/version.txt', 'app/resources')
    ],
    hiddenimports=[
        'psycopg2',
        'psycopg2._psycopg',
        'pyodbc',
        'sqlparse',
        'sqlalchemy',
        'cryptography',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DBVC-Desktop',
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
    icon='app/resources/logo.ico',
)
