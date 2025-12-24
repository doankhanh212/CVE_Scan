import threading
from queue import Queue

import pytest

from modules.scan_manager import ScanManager
from modules.discovery.host_discovery import HostDiscovery


class DummyDiscovery(HostDiscovery):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def discover(self, targets):
        # Simulate discovery that marks many targets as processed but only 1 alive host
        self.total = max(1, len(targets))
        self.done = len(targets)
        # push a single alive host
        self.alive_queue.put(targets[0])
        # capture alive_total before finishing
        self.alive_total = 1
        # mark finished so scan loop will stop after consuming alive queue
        self.finished.set()


def test_scan_progress_does_not_jump_to_100(monkeypatch):
    # capture progress callbacks
    progress_calls = []
    def progress_cb(phase, percent, message=None):
        progress_calls.append((phase, percent, message))

    sm = ScanManager({}, logger=lambda *a, **k: None, progress_cb=progress_cb)

    # patch HostDiscovery used by ScanManager to our DummyDiscovery
    monkeypatch.setattr('modules.scan_manager.HostDiscovery', DummyDiscovery)

    # make a large target list
    targets = [f"10.0.0.{i}" for i in range(1, 201)]

    # prevent running real pipelines which may block; return trivial result
    monkeypatch.setattr('modules.scan_manager.ScanManager._run_basic', lambda self, t: {"gui": {"ports": []}})

    # Patch Thread used by ScanManager to run discovery synchronously to avoid background hangs
    class DummyThreadRunNow:
        def __init__(self, target, args=(), daemon=False):
            self._target = target
            self._args = args
        def start(self):
            self._target(*self._args)

    monkeypatch.setattr('modules.scan_manager.Thread', DummyThreadRunNow)

    # run scan (synchronous since discovery/discover runs inline via patched Thread)
    results = sm.scan(targets)

    # we should have at least one progress 'scan' call (after processing the single alive host)
    scan_calls = [c for c in progress_calls if c[0] == 'scan']

    assert scan_calls, "No scan progress reported"

    # percent after first host should not be 100 (should reflect denominator of 200 initially)
    first_percent = scan_calls[0][1]
    assert first_percent < 100, "Progress jumped to 100% after one host"
