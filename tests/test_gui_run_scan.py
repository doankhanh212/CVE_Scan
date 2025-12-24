import tkinter as tk
import pytest

from modules.gui import GUIController

# Skip GUI-threading tests if Tk can't be initialized in this environment
try:
    _root = tk.Tk()
    _root.destroy()
    _HAS_TK = True
except Exception:
    _HAS_TK = False


class DummyManager:
    def __init__(self, config, logger=None, progress_cb=None):
        self.config = config
        self.logger = logger
        self.progress_cb = progress_cb

    def scan(self, targets, authenticated=False, auth_data=None, host_result_cb=None):
        # emulate returning results for each host
        out = []
        for t in targets:
            res = {"gui": {"ports": []}}
            out.append({"host": t, "result": res})
            # invoke host callback to mimic async updates
            if host_result_cb:
                host_result_cb(t, res, sync=True)
        return out


@pytest.mark.skipif(not _HAS_TK, reason="Tk not available in this environment")
def test_run_scan_basic(monkeypatch):
    g = GUIController()

    # replace ScanManager with our dummy
    monkeypatch.setattr("modules.gui.ScanManager", DummyManager)

    # put a valid host in the textbox
    g.host_box.delete("1.0", tk.END)
    g.host_box.insert("1.0", "127.0.0.1\n")

    # ensure scan mode is Basic
    g.scan_mode_var.set("Basic Scan")

    # call run_scan (synchronous)
    g.run_scan()

    # verify last_results were populated for the host
    assert "127.0.0.1" in g.last_results
    assert isinstance(g.last_results["127.0.0.1"], dict)


@pytest.mark.skipif(not _HAS_TK, reason="Tk not available in this environment")
def test_start_scan_thread(monkeypatch):
    g = GUIController()

    monkeypatch.setattr("modules.gui.ScanManager", DummyManager)

    g.host_box.delete("1.0", tk.END)
    g.host_box.insert("1.0", "127.0.0.1\n")
    g.scan_mode_var.set("Basic Scan")

    # Run the background thread synchronously by patching the Thread class to call target immediately
    class DummyThreadRunNow:
        def __init__(self, target, daemon=False):
            self._target = target
        def start(self):
            self._target()

    monkeypatch.setattr("modules.gui.threading.Thread", DummyThreadRunNow)

    g.start_scan_thread()

    # after synchronous run, scanning should be cleared
    assert not g.scanning
    assert "127.0.0.1" in g.last_results