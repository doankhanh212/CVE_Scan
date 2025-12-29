from modules.discovery.host_discovery import HostDiscovery


def test_discover_puts_alive_hosts(monkeypatch):
    """Test that discover() correctly populates alive_queue using nmap -sn mock."""
    hd = HostDiscovery(workers=2, retries=1, timeout=0.01)

    # Mock _run_nmap_sn to return subset of targets
    def mock_nmap(target_str):
        # Simulate nmap finding 1.2.3.4 alive
        return ["1.2.3.4"]
    
    monkeypatch.setattr(hd, "_run_nmap_sn", mock_nmap)

    targets = ["1.2.3.4", "5.6.7.8"]
    hd.discover(targets)

    alive = []
    while not hd.alive_queue.empty():
        alive.append(hd.alive_queue.get_nowait())

    assert "1.2.3.4" in alive
    assert hd.finished.is_set()


def test_progress_cb_called(monkeypatch):
    """Test that progress callback is called during discovery."""
    calls = []
    def cb(phase, percent):
        calls.append((phase, percent))

    hd = HostDiscovery(workers=1, retries=1, timeout=0.01, progress_cb=cb)
    
    # Mock _run_nmap_sn to return alive hosts
    def mock_nmap(target_str):
        return ["1.2.3.4", "5.6.7.8"]
    
    monkeypatch.setattr(hd, "_run_nmap_sn", mock_nmap)

    targets = ["1.2.3.4", "5.6.7.8"]
    hd.discover(targets)

    # ensure ping progress was reported at least once
    assert any(c[0] == "ping" for c in calls)


def test_discover_cidr_range(monkeypatch):
    """Test discover_cidr() method for subnet scanning."""
    hd = HostDiscovery(timeout=1, retries=3)
    
    # Mock _run_nmap_sn to simulate finding IPs in a /24 subnet
    def mock_nmap(target_str):
        # Simulate nmap finding 5 hosts in subnet
        return ["192.168.1.1", "192.168.1.5", "192.168.1.10", "192.168.1.254"]
    
    monkeypatch.setattr(hd, "_run_nmap_sn", mock_nmap)

    hd.discover_cidr("192.168.1.0/24")

    alive = []
    while not hd.alive_queue.empty():
        alive.append(hd.alive_queue.get_nowait())

    assert len(alive) == 4
    assert hd.finished.is_set()
    assert hd.alive_total == 4