from modules.gui import GUIController


def test_handle_open_settings_calls_open(monkeypatch):
    G = GUIController
    # create bare object
    g = object.__new__(G)

    called = {"ok": False}
    def fake_open():
        called["ok"] = True

    logs = []
    def fake_log(msg, lvl="INFO"):
        logs.append((lvl, msg))

    # wire minimal attributes
    g.open_settings = fake_open
    g.log = fake_log
    g._safe_after = lambda f: f()

    # call handler
    G._handle_open_settings(g)

    assert called["ok"] is True
    assert any("Opening settings" in m or "Error" in m for l,m in logs)


def test_handle_open_settings_when_missing(monkeypatch):
    G = GUIController
    g = object.__new__(G)

    logs = []
    def fake_log(msg, lvl="INFO"):
        logs.append((lvl, msg))

    g.log = fake_log
    g._safe_after = lambda f: f()

    # ensure no open methods
    # remove methods at the class level for this test to emulate a missing implementation
    monkeypatch.delattr(G, 'open_settings', raising=False)
    monkeypatch.delattr(G, '_open_settings_wrapper', raising=False)

    # call handler - should not raise
    G._handle_open_settings(g)

    assert any(l == "ERROR" and "No settings handler available" in m for l,m in logs)


def test_handle_open_settings_exception_schedules_safe_callback(monkeypatch):
    G = GUIController
    g = object.__new__(G)

    logs = []
    def fake_log(msg, lvl="INFO"):
        logs.append((lvl, msg))

    def raise_open():
        raise RuntimeError("boom")

    g.open_settings = raise_open
    g.log = fake_log

    captured = {}
    def fake_safe_after(fn):
        # capture the scheduled callback without executing it
        captured['fn'] = fn

    g._safe_after = fake_safe_after

    # patch messagebox to avoid GUI calls
    monkeypatch.setattr('modules.gui.messagebox.showerror', lambda *a, **k: captured.setdefault('shown', (a, k)))

    # call handler - should not raise, should log an error and schedule callback
    G._handle_open_settings(g)

    assert any(l == "ERROR" and "Failed to open settings" in m for l,m in logs)
    assert 'fn' in captured

    # invoking the scheduled callback must not raise (no NameError for 'e')
    captured['fn']()

    assert 'shown' in captured
