def test_main_window_module_imports():
    from archivum.ui.main_window import MainWindow, ScanWorker, TMDBWorker

    assert MainWindow is not None
    assert ScanWorker is not None
    assert TMDBWorker is not None
