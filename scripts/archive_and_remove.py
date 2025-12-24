"""Archive a list of files/dirs into backups/{timestamp}.tar.gz then remove them.

Usage:
  python scripts/archive_and_remove.py

The script will create 'backups/' if necessary and print what it archives and removes.
"""
import os
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / 'backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Files to archive & remove (relative to repo root)
TARGETS = [
    '121212.csv',
    'scan_report.csv',
    'scan_result_2025-12-12_16-57-51.csv',
    'nvd_cache.json',
    'scripts/cleanup_v1.py',
    'tests/run_quick_tests.py',
    '.pytest_cache/README.md',
]

TS = time.strftime('%Y%m%d_%H%M%S')
ARCHIVE = BACKUP_DIR / f'cleanup_candidates_backup_{TS}.tar.gz'

found = []
missing = []
for p in TARGETS:
    full = ROOT / p
    if full.exists():
        found.append(full)
    else:
        missing.append(p)

if not found:
    print('No target files found to archive/remove. Nothing to do.')
    if missing:
        print('Missing (not found):', missing)
    sys.exit(0)

print(f'Archiving {len(found)} items into {ARCHIVE}...')
with tarfile.open(ARCHIVE, 'w:gz') as tf:
    for f in found:
        arcname = f.relative_to(ROOT)
        print(f' - adding {arcname}')
        tf.add(f, arcname=str(arcname))

print('Archive created successfully.')

# Double-check archive contents
with tarfile.open(ARCHIVE, 'r:gz') as tf:
    print('Archive contains:')
    for m in tf.getmembers():
        print('  -', m.name)

# Now remove the files/directories we archived
print('Removing archived items...')
for f in found:
    try:
        if f.is_dir():
            import shutil
            shutil.rmtree(f)
            print(f' - removed dir {f.relative_to(ROOT)}')
        else:
            f.unlink()
            print(f' - removed file {f.relative_to(ROOT)}')
    except Exception as e:
        print(f' ! failed to remove {f.relative_to(ROOT)}: {e}')

print('\nMissing (not found):', missing)
print('\nDone. Archive stored at:', ARCHIVE)
