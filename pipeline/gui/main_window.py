from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow

APP_NAME = "Calcium + Behavior Platform"


class MainWindow(QMainWindow):
    """Top-level window. Placeholder until the v0.1 viewer (time slider over
    calcium movie, traces, behavior video and pose) lands."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)

        placeholder = QLabel("No session loaded")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(placeholder)
