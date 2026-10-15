import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pipeline.gui import MainWindow
from pipeline.gui.main_window import APP_NAME


def test_main_window_opens(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.isVisible()
    assert window.windowTitle() == APP_NAME
