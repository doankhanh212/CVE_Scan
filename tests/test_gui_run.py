from modules.gui import GUIController


def test_run_callable():
    g = GUIController()
    assert hasattr(g, 'run')
    assert callable(getattr(g, 'run'))
