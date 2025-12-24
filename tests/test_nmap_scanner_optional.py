from modules.scanners.nmap_scanner import NmapScanner


def test_nmap_missing_behaviour(monkeypatch):
    # Simulate missing python-nmap by forcing internal nm to None
    n = NmapScanner(logger=lambda *a, **k: None)
    n.nm = None

    # ensure scan_host returns empty dict and does not raise
    assert n.scan_host("127.0.0.1") == {}

    # if n.nm is present (fake object), ensure method attempts to use it
    class FakeNM:
        def __init__(self):
            self._hosts = set()
        def scan(self, hosts, arguments):
            # simulate a successful scan with no hosts
            pass
        def all_hosts(self):
            return []

    n2 = NmapScanner(logger=lambda *a, **k: None)
    n2.nm = FakeNM()
    assert n2.scan_host("127.0.0.1") == {}
