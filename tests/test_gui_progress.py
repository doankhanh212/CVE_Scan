import pytest

from modules.gui import GUIController


class DummyVar:
    def __init__(self):
        self.v = 0
    def set(self, x):
        self.v = x
    def get(self):
        return self.v


class DummyLabel:
    def __init__(self):
        self.text = "0%"
    def config(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
    def cget(self, key):
        return self.text


class DummyButton:
    def config(self, **kwargs):
        pass


class DummyRoot:
    def after(self, ms, func):
        # Simulate environment where root.after is not usable in tests
        raise Exception("no tk mainloop")


def make_fake_gui():
    fake = type("F", (), {})()
    fake.root = DummyRoot()
    fake._ping_percent = 0
    fake._scan_percent = 0
    fake.overall_var = DummyVar()
    fake.overall_label = DummyLabel()
    fake.export_btn = DummyButton()
    # bind method
    fake.on_progress = GUIController.on_progress.__get__(fake, GUIController)
    return fake


def test_on_progress_only_shows_scan_without_tk():
    g = make_fake_gui()

    # initial overall should be 0
    assert g.overall_var.get() == 0

    # ping updates should not change overall
    g.on_progress("ping", 50)
    assert g.overall_var.get() == 0
    assert g.overall_label.cget("text") == "0%"

    # scan updates should change overall
    g.on_progress("scan", 25)
    assert g.overall_var.get() == 25
    assert g.overall_label.cget("text") == "25%"

    # scan complete should reach 100
    g.on_progress("scan", 100)
    assert g.overall_var.get() == 100
    assert g.overall_label.cget("text") == "100%"