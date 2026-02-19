# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building a standalone vibe-clock binary."""

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

a = Analysis(
    ["entry_point.py"],
    pathex=[],
    binaries=[],
    datas=copy_metadata("vibe-clock"),
    hiddenimports=[
        "vibe_clock.collectors.claude_code",
        "vibe_clock.collectors.codex",
        "vibe_clock.collectors.opencode",
        "vibe_clock.svg.bars",
        "vibe_clock.svg.card",
        "vibe_clock.svg.donut",
        "vibe_clock.svg.heatmap",
        "vibe_clock.svg.hourly",
        "vibe_clock.svg.token_bars",
        "vibe_clock.svg.weekly",
    ] + collect_submodules("rich._unicode_data"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="vibe-clock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
