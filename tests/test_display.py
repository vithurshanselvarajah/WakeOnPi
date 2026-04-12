import wakeonpi.display as display


def test_set_display_handles_exceptions(monkeypatch, tmp_path):
    monkeypatch.setattr(display, '__name__', 'wakeonpi.display')
    def fake_open(*a, **k):
        raise OSError('nope')
    monkeypatch.setattr('builtins.open', fake_open)
    display.set_display(True)
