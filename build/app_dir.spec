# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 目录模式打包：启动快、兼容性好，适合交付给客户。"""
import os

from PyInstaller.utils.hooks import collect_submodules

try:
    SPEC_DIR = os.path.abspath(SPECPATH)  # noqa: F821
    if not os.path.isdir(SPEC_DIR):
        SPEC_DIR = os.path.dirname(SPEC_DIR)
except NameError:
    SPEC_DIR = os.path.abspath('build')

PROJECT = os.path.dirname(SPEC_DIR)
STATIC_DIR = os.path.join(PROJECT, 'backend', 'static')
TEMPLATE_DIR = os.path.join(PROJECT, 'backend', 'templates')

a = Analysis(
    [os.path.join(PROJECT, 'run.py')],
    pathex=[PROJECT],
    binaries=[],
    datas=[
        (STATIC_DIR, 'static'),
        (TEMPLATE_DIR, 'templates'),
    ],
    hiddenimports=['sqlalchemy.dialects.sqlite'] + collect_submodules('sqlalchemy.dialects'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'PyInstaller'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartStock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='SmartStock',
)
