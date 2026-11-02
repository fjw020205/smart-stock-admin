# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：单文件 exe，内置两套前端与入口模板。"""
import os
import sys

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

for required in (STATIC_DIR, TEMPLATE_DIR):
    if not os.path.isdir(required):
        raise SystemExit(f'缺少打包资源目录：{required}')

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
    a.binaries,
    a.datas,
    [],
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
