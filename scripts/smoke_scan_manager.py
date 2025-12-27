import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.scan_manager import ScanManager

collected = []

def host_cb(h, r):
    collected.append(h)

sm = ScanManager({}, logger=lambda *a, **k: None, progress_cb=lambda *a, **k: None)
res = sm.scan(['8.8.8.8'], authenticated=False, host_result_cb=host_cb)
print('per-ip callbacks:', len(collected))
print('results items:', len(res))
print('sample hosts:', [item['host'] for item in res][:5])
