def test_package_import():
    import importlib
    pkg = importlib.import_module('wakeonpi')
    assert pkg is not None
