# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],  # 🔥 BẮT BUỘC
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('README.md', '.'),
        ('docs', 'docs'),
    ],
    hiddenimports=[
        # core
        'modules.config_manager',
        'modules.scan_manager',
        'modules.gui',

        # scanners
        'modules.scanners.nmap_scanner',
        'modules.scanners.rustscan_scanner',

        # discovery / cve
        'modules.discovery',
        'modules.cve.cve_matcher',
        'modules.cve.cpe_builder',

        # pipelines / report
        'modules.pipelines.basic_pipeline',
        'modules.report.json_report',

        # threat metrics
        'modules.threat_metric.cvss',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tests',
        'venv',
        'scripts',
        '__pycache__'
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='app',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='build'
)
