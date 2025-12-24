def test_open_settings_wrapper_exists_in_source():
    # Confirm the wrapper function was added to the source file (sanity check for manual debugging)
    p = "modules/gui.py"
    with open(p, "r", encoding="utf-8") as f:
        src = f.read()
    assert "def _open_settings_wrapper" in src
    assert "Opening settings..." in src
