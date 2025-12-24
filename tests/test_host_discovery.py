from modules.discovery.host_discovery import HostDiscovery


def test_discover_puts_alive_hosts(monkeypatch):
    hd = HostDiscovery(workers=2, retries=1, timeout=0.01)

    # monkeypatch _ping to return True for 1.2.3.4 only
    monkeypatch.setattr(hd, "_ping", lambda ip: ip == "1.2.3.4")

    targets = ["1.2.3.4", "5.6.7.8"]
    hd.discover(targets)

    alive = []
    while not hd.alive_queue.empty():
        alive.append(hd.alive_queue.get_nowait())

    assert "1.2.3.4" in alive
    assert hd.finished.is_set()


def test_progress_cb_called(monkeypatch):
    calls = []
    def cb(phase, percent):
        calls.append((phase, percent))

    hd = HostDiscovery(workers=1, retries=1, timeout=0.01, progress_cb=cb)
    monkeypatch.setattr(hd, "_ping", lambda ip: True)

    targets = ["1.2.3.4", "5.6.7.8"]
    hd.discover(targets)

    # ensure ping progress was reported at least once
    assert any(c[0] == "ping" for c in calls)