import sys
from PySide6.QtWidgets import QApplication
from sbbpygui import SBBPyGui

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SBBPyGui()
    window.show()
    sys.exit(app.exec())
