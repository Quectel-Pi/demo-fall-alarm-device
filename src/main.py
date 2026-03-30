# -*- coding: gbk -*-

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui_manager import UIManager
from log_manager import LogManager


def main():
    LogManager.append_log("Starting Fall Alarm Application...", "INFO")
    
    app = QApplication(sys.argv)
    
    window = UIManager()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

