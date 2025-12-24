"""Find files that look like they are not referenced anywhere in the repository.

Heuristic: for each file under repo (limited to certain extensions), search for its basename in all files; if only reference is itself, mark as candidate orphan.
"""
import os
import fnmatch
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTS = ['*.csv', '*.json', '*.html', '*.py', '*.md']

candidates = []

for root, dirs, files in os.walk(ROOT):
    # skip venv and .git
    if 'venv' in root or '.git' in root:
        continue
    for f in files:
        path = Path(root) / f
        if any(fnmatch.fnmatch(f, pat) for pat in EXTS):
            # skip test files and obvious binaries
            if f.startswith('test_'):
                continue
            # skip scripts we know are useful
            if str(path).startswith(str(ROOT / 'scripts')) and f in ('rebuild_local_db.py', 'download_nvd_feeds.py', 'full_migration_runner.py'):
                continue
            # search for basename occurrences
            try:
                res = subprocess.run(['git', 'grep', '-n', '--', f], cwd=str(ROOT), capture_output=True, text=True)
                out = res.stdout.strip()
                if not out:
                    candidates.append((str(path.relative_to(ROOT)), 0))
                else:
                    # count matches excluding the file itself
                    lines = [l for l in out.splitlines() if not l.startswith(str(path.relative_to(ROOT)) + ':')]
                    if not lines:
                        candidates.append((str(path.relative_to(ROOT)), 1))
            except Exception:
                # fallback: use simple scan
                candidates.append((str(path.relative_to(ROOT)), -1))

# print small report
print('Potential orphan candidates (basename only referenced in own file or not referenced):\n')
for p, score in sorted(candidates):
    note = 'no refs found' if score == 0 else ('only self reference' if score == 1 else 'unknown')
    print(f" - {p}  ({note})")

print('\nReview the list and remove or archive items you are sure are not needed.')