#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import io
sys.path.insert(0, '/Users/dhqkh/Documents/CVE_Scan')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from modules.pipelines.basic_pipeline import BasicPipeline

def test_logger(msg, level="INFO"):
    try:
        print(f"[{level}] {msg}")
    except:
        print(f"[{level}] (unicode error)")

config = {}
pipeline = BasicPipeline(config, logger=test_logger)
print('=' * 60)
print('[TEST] Starting pipeline with hqg.vn (will ping CIDR, then scan alive)...')
print('=' * 60)
result = pipeline.execute('hqg.vn')
print('=' * 60)
print('[TEST] Done')
print(f"[TEST] Services scanned: {len(result.get('gui', {}).get('ports', []))}")
print(f"[TEST] CVEs found: {len([c for p in result.get('gui', {}).get('ports', []) for c in p.get('cves', [])])}")

