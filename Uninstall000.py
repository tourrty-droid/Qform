import sys
import os
import shutil
import winreg
import time
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QMessageBox,
                             QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class UninstallWorker(QThread):
    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal()

    def run(self):
        steps = [
            (10, "Removing application files..."),
            (25, "Removing settings and data..."),
            (40, "Removing registry entries..."),
            (55, "Removing shortcuts..."),
            (70, "Cleaning temporary files..."),
            (85, "Removing recent files..."),
            (100, "Uninstall complete")
        ]

        for progress, message in steps:
            self.progress_update.emit(progress, message)
            time.sleep(0.5)

        # Actually remove files
        app_data = os.path.join(os.environ['APPDATA'], 'Qform')
        if os.path.exists(app_data):
            shutil.rmtree(app_data, ignore_errors=True)

        # Remove from registry
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "Qform")
            except:
                pass
            winreg.CloseKey(key)
        except:
            pass

        # Remove shortcuts
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        for file in os.listdir(desktop):
            if 'Qform' in file:
                try:
                    os.remove(os.path.join(desktop, file))
                except:
                    pass

        self.finished.emit()


class UninstallWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qform Uninstall")
        self.setFixedSize(450, 300)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Qform Uninstall")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Message
        message = QLabel("Please wait while Qform is being removed from your computer.")
        message.setWordWrap(True)
        layout.addWidget(message)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel("Preparing to uninstall...")
        layout.addWidget(self.status_label)

        # Removed items
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(80)
        layout.addWidget(self.log)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        # Start uninstall
        self.worker = UninstallWorker()
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log.append(f"  {message}")

    def on_finished(self):
        self.cancel_btn.setText("Close")
        self.log.append("\nQform has been successfully removed.")

        QMessageBox.information(
            self,
            "Uninstall Complete",
            "Qform has been successfully removed from your computer."
        )


def main():
    # Ask for confirmation
    app = QApplication(sys.argv)

    reply = QMessageBox.question(
        None,
        "Qform Uninstall",
        "Do you REALLY want to delete Qform from your PC?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.No:
        sys.exit(0)

    window = UninstallWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()