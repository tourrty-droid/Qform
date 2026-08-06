import sys
import os
import time
import json
import pickle
import shutil
import winreg
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QLabel,
                             QProgressBar, QLineEdit, QTextEdit, QMessageBox,
                             QDialog, QComboBox, QCheckBox, QDialogButtonBox,
                             QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
                             QFrame, QStatusBar, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QSpinBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSettings, QTimer
from PyQt6.QtGui import QAction, QFont
import libtorrent as lt


class Installer:
    @staticmethod
    def install():
        app_data = os.path.join(os.environ['APPDATA'], 'Qform')
        if not os.path.exists(app_data):
            os.makedirs(app_data)

        dirs = ['torrents', 'resume', 'settings']
        for d in dirs:
            dir_path = os.path.join(app_data, d)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        if QMessageBox.question(
                None, 'Qform Setup',
                'Would you like Qform to start with Windows?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, "Qform", 0, winreg.REG_SZ, sys.executable)
                winreg.CloseKey(key)
            except:
                pass

        default_settings = {
            'theme': 'Dark Gray',
            'language': 'English',
            'download_path': os.path.expanduser('~/Downloads'),
            'confirm_delete': True,
            'confirm_stop': True,
            'confirm_exit': True
        }

        settings_file = os.path.join(app_data, 'settings', 'default.json')
        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=4)

        return True


class ResumeData:
    def __init__(self):
        self.resume_dir = os.path.join(os.environ['APPDATA'], 'Qform', 'resume')
        if not os.path.exists(self.resume_dir):
            os.makedirs(self.resume_dir)

    def save(self, torrent_id, data):
        filepath = os.path.join(self.resume_dir, f"{torrent_id}.resume")
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving resume data: {e}")

    def load(self, torrent_id):
        filepath = os.path.join(self.resume_dir, f"{torrent_id}.resume")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return None

    def delete(self, torrent_id):
        filepath = os.path.join(self.resume_dir, f"{torrent_id}.resume")
        if os.path.exists(filepath):
            os.remove(filepath)

    def load_all(self):
        resumes = []
        if os.path.exists(self.resume_dir):
            for filename in os.listdir(self.resume_dir):
                if filename.endswith('.resume'):
                    torrent_id = filename.replace('.resume', '')
                    data = self.load(torrent_id)
                    if data:
                        data['id'] = torrent_id
                        resumes.append(data)
        return resumes


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Theme
        theme_group = QGroupBox("Interface Theme")
        theme_layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Gray", "Dark"])
        self.theme_combo.currentTextChanged.connect(self.preview_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Language
        lang_group = QGroupBox("Language")
        lang_layout = QVBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Russian"])
        lang_layout.addWidget(self.lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # Download settings
        dl_group = QGroupBox("Download Settings")
        dl_layout = QFormLayout()

        self.max_downloads = QSpinBox()
        self.max_downloads.setRange(1, 20)
        self.max_downloads.setValue(5)

        self.dl_limit = QSpinBox()
        self.dl_limit.setRange(0, 1000000)
        self.dl_limit.setSuffix(" KB/s")
        self.dl_limit.setSpecialValueText("Unlimited")

        self.ul_limit = QSpinBox()
        self.ul_limit.setRange(0, 1000000)
        self.ul_limit.setSuffix(" KB/s")
        self.ul_limit.setSpecialValueText("Unlimited")

        dl_layout.addRow("Max active downloads:", self.max_downloads)
        dl_layout.addRow("Download limit:", self.dl_limit)
        dl_layout.addRow("Upload limit:", self.ul_limit)
        dl_group.setLayout(dl_layout)
        layout.addWidget(dl_group)

        # Confirmations
        confirm_group = QGroupBox("Confirmation Dialogs")
        confirm_layout = QVBoxLayout()

        self.confirm_delete = QCheckBox("Show confirmation before deleting torrent")
        self.confirm_stop = QCheckBox("Show confirmation before stopping download")
        self.confirm_exit = QCheckBox("Show confirmation before exiting application")

        confirm_layout.addWidget(self.confirm_delete)
        confirm_layout.addWidget(self.confirm_stop)
        confirm_layout.addWidget(self.confirm_exit)
        confirm_group.setLayout(confirm_layout)
        layout.addWidget(confirm_group)

        self.load_current_settings()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_and_apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_current_settings(self):
        if self.parent:
            self.theme_combo.setCurrentText(self.parent.current_theme)
            self.lang_combo.setCurrentText(self.parent.current_language)
            self.confirm_delete.setChecked(self.parent.confirm_delete)
            self.confirm_stop.setChecked(self.parent.confirm_stop)
            self.confirm_exit.setChecked(self.parent.confirm_exit)

    def preview_theme(self, theme_name):
        if self.parent:
            self.parent.apply_theme(theme_name)

    def save_and_apply(self):
        if self.parent:
            self.parent.current_theme = self.theme_combo.currentText()
            self.parent.current_language = self.lang_combo.currentText()
            self.parent.confirm_delete = self.confirm_delete.isChecked()
            self.parent.confirm_stop = self.confirm_stop.isChecked()
            self.parent.confirm_exit = self.confirm_exit.isChecked()

            self.parent.apply_language(self.lang_combo.currentText())
            self.parent.apply_theme(self.theme_combo.currentText())
            self.parent.save_settings()

        self.accept()


class DeviceManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Manager")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        title = QLabel("Connected Devices")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.device_list = QListWidget()
        self.detect_devices()
        layout.addWidget(self.device_list)

        options_group = QGroupBox("Transfer Options")
        options_layout = QVBoxLayout()

        self.convert_video = QCheckBox("Convert video for device compatibility")
        self.convert_audio = QCheckBox("Convert audio for device compatibility")
        self.delete_after = QCheckBox("Delete from computer after transfer")

        options_layout.addWidget(self.convert_video)
        options_layout.addWidget(self.convert_audio)
        options_layout.addWidget(self.delete_after)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        self.transfer_btn = QPushButton("Transfer Selected Files to Device")
        self.transfer_btn.clicked.connect(self.transfer_files)
        layout.addWidget(self.transfer_btn)

    def detect_devices(self):
        self.device_list.clear()

        if sys.platform == "win32":
            try:
                import win32api
                drives = win32api.GetLogicalDriveStrings()
                drives = drives.split('\000')[:-1]

                for drive in drives:
                    if drive != "C:\\":
                        try:
                            drive_type = win32api.GetDriveType(drive)
                            if drive_type == 2:
                                self.device_list.addItem(f"Removable Drive: {drive}")
                            elif drive_type == 3:
                                self.device_list.addItem(f"External Drive: {drive}")
                        except:
                            self.device_list.addItem(f"Drive: {drive}")
            except:
                for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        self.device_list.addItem(f"Drive: {drive}")
        else:
            media_paths = ["/media", "/mnt", "/Volumes"]
            for path in media_paths:
                if os.path.exists(path):
                    for device in os.listdir(path):
                        device_path = os.path.join(path, device)
                        if os.path.ismount(device_path):
                            self.device_list.addItem(f"Device: {device} ({device_path})")

    def transfer_files(self):
        if not self.device_list.selectedItems():
            QMessageBox.warning(self, "Error", "Please select a device first!")
            return

        source_files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Transfer")
        if source_files:
            selected = self.device_list.selectedItems()[0].text()
            device_path = selected.split(": ")[1] if ": " in selected else selected

            try:
                for file_path in source_files:
                    dest = os.path.join(device_path, os.path.basename(file_path))
                    shutil.copy2(file_path, dest)

                QMessageBox.information(
                    self, "Success",
                    f"Successfully transferred {len(source_files)} files!"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Transfer failed: {str(e)}")


class TorrentSession(QThread):
    progress_update = pyqtSignal(str, dict)
    torrent_added = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.session = None
        self.torrents = {}
        self.is_running = True
        self.resume_data = ResumeData()

    def run(self):
        settings = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
        }

        self.session = lt.session(settings)
        self.load_saved_torrents()

        while self.is_running:
            try:
                if self.session:
                    self.session.post_torrent_updates()

                    for torrent_id, data in list(self.torrents.items()):
                        if data['handle'].is_valid():
                            status = data['handle'].status()

                            # Calculate ETA
                            if status.download_rate > 0 and status.total_wanted > 0:
                                remaining = status.total_wanted - status.total_wanted_done
                                eta_seconds = remaining / status.download_rate
                                eta = str(timedelta(seconds=int(eta_seconds)))
                            else:
                                eta = "∞"

                            # Calculate elapsed time
                            elapsed = str(timedelta(seconds=status.active_time))

                            # Determine status text using integer values
                            state_int = int(status.state)

                            # libtorrent state values (correct for newer versions)
                            state_map = {
                                0: "Queued",
                                1: "Checking Files",
                                2: "Downloading Metadata",
                                3: "Downloading",
                                4: "Finished",
                                5: "Seeding",
                                6: "Allocating",
                                7: "Checking Resume Data"
                            }

                            state_text = state_map.get(state_int, f"State {state_int}")

                            # Override for paused
                            if status.paused:
                                if state_int in [3, 5]:
                                    state_text = "Paused"

                            info = {
                                'progress': status.progress * 100,
                                'download_rate': status.download_rate / 1024,
                                'upload_rate': status.upload_rate / 1024,
                                'peers': status.num_peers,
                                'seeds': status.num_seeds,
                                'state': state_text,
                                'total_size': status.total_wanted,
                                'total_done': status.total_done,
                                'total_uploaded': status.total_upload,
                                'is_seeding': status.is_seeding,
                                'name': data['name'],
                                'eta': eta,
                                'elapsed': elapsed,
                                'remaining_bytes': status.total_wanted - status.total_wanted_done,
                                'paused': status.paused
                            }

                            self.progress_update.emit(torrent_id, info)

                time.sleep(1)

            except Exception as e:
                print(f"Session error: {e}")

    def add_torrent(self, torrent_id, source, save_path):
        try:
            params = {
                'save_path': save_path,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            }

            resume = self.resume_data.load(torrent_id)

            if source.startswith('magnet:'):
                handle = lt.add_magnet_uri(self.session, source, params)

                timeout = 0
                while not handle.has_metadata():
                    time.sleep(1)
                    timeout += 1
                    if timeout > 120:
                        raise Exception("Metadata download timeout")
            else:
                info = lt.torrent_info(source)
                handle = self.session.add_torrent({'ti': info, 'save_path': save_path})

            name = handle.status().name or os.path.basename(source)

            self.torrents[torrent_id] = {
                'handle': handle,
                'source': source,
                'save_path': save_path,
                'name': name,
                'added_date': datetime.now().isoformat(),
                'completed': False
            }

            self.torrent_added.emit(torrent_id, name)

            if resume and 'resume_data' in resume:
                try:
                    handle.apply_resume_data(resume['resume_data'])
                except:
                    pass

            self.save_progress(torrent_id)
            return True

        except Exception as e:
            print(f"Error adding torrent: {e}")
            return False

    def remove_torrent(self, torrent_id, delete_files=False):
        if torrent_id in self.torrents:
            try:
                if delete_files and self.torrents[torrent_id]['handle'].is_valid():
                    try:
                        info = self.torrents[torrent_id]['handle'].torrent_file()
                        if info:
                            save_path = self.torrents[torrent_id]['save_path']
                            for f in info.files():
                                file_path = os.path.join(save_path, f.path)
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                    except:
                        pass

                self.session.remove_torrent(self.torrents[torrent_id]['handle'])
                self.resume_data.delete(torrent_id)
                del self.torrents[torrent_id]
                return True
            except Exception as e:
                print(f"Error removing torrent: {e}")
        return False

    def save_progress(self, torrent_id):
        if torrent_id in self.torrents:
            data = self.torrents[torrent_id]
            if data['handle'].is_valid():
                try:
                    resume = {
                        'source': data['source'],
                        'save_path': data['save_path'],
                        'name': data['name'],
                        'added_date': data['added_date'],
                        'resume_data': data['handle'].save_resume_data()
                    }
                    self.resume_data.save(torrent_id, resume)
                except:
                    pass

    def save_all_progress(self):
        for torrent_id in self.torrents:
            self.save_progress(torrent_id)

    def load_saved_torrents(self):
        saved = self.resume_data.load_all()
        for data in saved:
            if data and 'source' in data and 'save_path' in data:
                self.add_torrent(
                    data['id'],
                    data['source'],
                    data['save_path']
                )

    def stop(self):
        self.is_running = False
        self.save_all_progress()
        if self.session:
            self.session.pause()


class TorrentWidget(QFrame):
    def __init__(self, torrent_id, name):
        super().__init__()
        self.torrent_id = torrent_id
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setMaximumHeight(150)

        layout = QVBoxLayout(self)
        layout.setSpacing(3)

        # Name
        self.name_label = QLabel(name[:55] + "..." if len(name) > 55 else name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self.name_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Status row
        status_row = QHBoxLayout()
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-weight: bold; color: #4caf50;")
        self.eta_label = QLabel("ETA: --")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.eta_label)
        layout.addLayout(status_row)

        # Stats row
        stats_row = QHBoxLayout()
        self.speed_label = QLabel("↓ 0 KB/s ↑ 0 KB/s")
        self.peers_label = QLabel("P: 0 S: 0")
        self.size_label = QLabel("0 B / 0 B")

        stats_row.addWidget(self.speed_label)
        stats_row.addWidget(self.peers_label)
        stats_row.addWidget(self.size_label)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Time row
        time_row = QHBoxLayout()
        self.downloaded_label = QLabel("Downloaded: 0 B")
        self.uploaded_label = QLabel("Uploaded: 0 B")
        self.time_label = QLabel("Time: 00:00:00")

        time_row.addWidget(self.downloaded_label)
        time_row.addWidget(self.uploaded_label)
        time_row.addStretch()
        time_row.addWidget(self.time_label)
        layout.addLayout(time_row)


class QformMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resume_data = ResumeData()
        self.torrent_widgets = {}
        self.active_torrents = []

        self.current_theme = "Dark Gray"
        self.current_language = "English"
        self.confirm_delete = True
        self.confirm_stop = True
        self.confirm_exit = True

        self.load_settings()
        self.initUI()
        self.create_menu()
        self.create_statusbar()
        self.apply_theme(self.current_theme)
        self.apply_language(self.current_language)

        self.torrent_session = TorrentSession()
        self.torrent_session.progress_update.connect(self.update_torrent_info)
        self.torrent_session.torrent_added.connect(self.on_torrent_added)
        self.torrent_session.start()

    def initUI(self):
        self.setWindowTitle("Qform")
        self.setMinimumSize(850, 650)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Add torrent section
        add_group = QGroupBox("Add Torrent")
        add_layout = QVBoxLayout()

        source_layout = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("magnet:?xt=urn:btih:... or path to .torrent")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_torrent)
        source_layout.addWidget(self.source_input)
        source_layout.addWidget(browse_btn)
        add_layout.addLayout(source_layout)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(os.path.expanduser("~/Downloads"))
        path_btn = QPushButton("Browse")
        path_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_btn)
        add_layout.addLayout(path_layout)

        add_btn = QPushButton("Add Torrent")
        add_btn.clicked.connect(self.add_torrent)
        add_layout.addWidget(add_btn)

        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # Torrents list
        torrents_group = QGroupBox("Torrents")
        torrents_layout = QVBoxLayout()

        self.torrent_list = QListWidget()
        self.torrent_list.setMinimumHeight(300)
        torrents_layout.addWidget(self.torrent_list)

        controls = QHBoxLayout()
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self.resume_selected)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_selected)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_selected)

        controls.addWidget(self.resume_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.remove_btn)
        controls.addStretch()
        torrents_layout.addLayout(controls)

        torrents_group.setLayout(torrents_layout)
        layout.addWidget(torrents_group)

        # Global stats
        self.global_speed = QLabel("Total: ↓ 0 KB/s ↑ 0 KB/s | Active: 0 | Peers: 0")
        layout.addWidget(self.global_speed)

    def create_menu(self):
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        # File menu
        file_menu = menubar.addMenu('File')

        add_action = QAction('Add Torrent...', self)
        add_action.setShortcut('Ctrl+O')
        add_action.triggered.connect(self.browse_torrent)
        file_menu.addAction(add_action)

        add_magnet = QAction('Add Magnet Link...', self)
        add_magnet.setShortcut('Ctrl+M')
        add_magnet.triggered.connect(lambda: self.source_input.setFocus())
        file_menu.addAction(add_magnet)

        file_menu.addSeparator()

        remove_action = QAction('Remove Torrent', self)
        remove_action.setShortcut('Delete')
        remove_action.triggered.connect(self.remove_selected)
        file_menu.addAction(remove_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        resume_all = QAction('Resume All', self)
        resume_all.triggered.connect(self.resume_all)
        tools_menu.addAction(resume_all)

        pause_all = QAction('Pause All', self)
        pause_all.triggered.connect(self.pause_all)
        tools_menu.addAction(pause_all)

        tools_menu.addSeparator()

        device_manager = QAction('Device Manager...', self)
        device_manager.triggered.connect(self.show_device_manager)
        tools_menu.addAction(device_manager)

        tools_menu.addSeparator()

        settings_action = QAction('Preferences...', self)
        settings_action.setShortcut('Ctrl+P')
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About Qform', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        version_label = QLabel("Qform v1.0b")
        self.statusbar.addPermanentWidget(version_label)
        self.statusbar.showMessage("Ready")

    def browse_torrent(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Torrent", "", "Torrent Files (*.torrent)"
        )
        if file_path:
            self.source_input.setText(file_path)

    def browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.path_input.setText(folder)

    def add_torrent(self):
        source = self.source_input.text().strip()
        save_path = self.path_input.text().strip()

        if not source or not save_path:
            QMessageBox.warning(self, "Error", "Please provide source and save path")
            return

        torrent_id = str(int(time.time() * 1000))

        if self.torrent_session.add_torrent(torrent_id, source, save_path):
            self.source_input.clear()
            self.statusbar.showMessage("Torrent added successfully", 3000)

    def on_torrent_added(self, torrent_id, name):
        item = QListWidgetItem()
        widget = TorrentWidget(torrent_id, name)
        item.setSizeHint(widget.sizeHint())
        self.torrent_list.addItem(item)
        self.torrent_list.setItemWidget(item, widget)
        self.torrent_widgets[torrent_id] = widget

        self.active_torrents.append({
            'id': torrent_id,
            'name': name,
            'item': item
        })

    def update_torrent_info(self, torrent_id, info):
        if torrent_id in self.torrent_widgets:
            w = self.torrent_widgets[torrent_id]
            w.progress_bar.setValue(int(info['progress']))
            w.status_label.setText(info['state'])
            w.eta_label.setText(f"ETA: {info['eta']}")
            w.speed_label.setText(f"↓ {info['download_rate']:.1f} KB/s ↑ {info['upload_rate']:.1f} KB/s")
            w.peers_label.setText(f"P: {info['peers']} S: {info['seeds']}")
            w.time_label.setText(f"Time: {info['elapsed']}")

            def format_bytes(b):
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if b < 1024:
                        return f"{b:.1f} {unit}"
                    b /= 1024
                return f"{b:.1f} PB"

            w.size_label.setText(f"{format_bytes(info['total_done'])} / {format_bytes(info['total_size'])}")
            w.downloaded_label.setText(f"Downloaded: {format_bytes(info['total_done'])}")
            w.uploaded_label.setText(f"Uploaded: {format_bytes(info['total_uploaded'])}")

            # Color status based on state
            state_colors = {
                "Downloading": "#4caf50",
                "Seeding": "#2196f3",
                "Finished": "#ff9800",
                "Paused": "#9e9e9e",
                "Checking Files": "#ffeb3b",
                "Downloading Metadata": "#9c27b0",
                "Allocating": "#00bcd4",
                "Checking Resume Data": "#ff5722"
            }

            color = state_colors.get(info['state'], "#e0e0e0")
            w.status_label.setStyleSheet(f"font-weight: bold; color: {color};")

        # Update global stats
        total_dl = sum(
            self.torrent_session.torrents[tid]['handle'].status().download_rate / 1024
            for tid in self.torrent_session.torrents
        ) if self.torrent_session else 0

        total_ul = sum(
            self.torrent_session.torrents[tid]['handle'].status().upload_rate / 1024
            for tid in self.torrent_session.torrents
        ) if self.torrent_session else 0

        total_peers = sum(
            self.torrent_session.torrents[tid]['handle'].status().num_peers
            for tid in self.torrent_session.torrents
        ) if self.torrent_session else 0

        self.global_speed.setText(
            f"Total: ↓ {total_dl:.1f} KB/s ↑ {total_ul:.1f} KB/s | "
            f"Active: {len(self.torrent_widgets)} | Peers: {total_peers}"
        )

    def resume_selected(self):
        current = self.torrent_list.currentItem()
        if current:
            row = self.torrent_list.row(current)
            if row < len(self.active_torrents):
                tid = self.active_torrents[row]['id']
                if tid in self.torrent_session.torrents:
                    self.torrent_session.torrents[tid]['handle'].resume()

    def pause_selected(self):
        current = self.torrent_list.currentItem()
        if current:
            if self.confirm_stop:
                reply = QMessageBox.question(
                    self, 'Pause',
                    'Pause this download?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            row = self.torrent_list.row(current)
            if row < len(self.active_torrents):
                tid = self.active_torrents[row]['id']
                if tid in self.torrent_session.torrents:
                    self.torrent_session.torrents[tid]['handle'].pause()

    def resume_all(self):
        for tid in self.torrent_session.torrents:
            self.torrent_session.torrents[tid]['handle'].resume()

    def pause_all(self):
        for tid in self.torrent_session.torrents:
            self.torrent_session.torrents[tid]['handle'].pause()

    def remove_selected(self):
        current = self.torrent_list.currentItem()
        if not current:
            return

        if self.confirm_delete:
            reply = QMessageBox.question(
                self, 'Remove',
                'Remove this torrent?\nYou can also delete downloaded files.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

            delete_files = QMessageBox.question(
                self, 'Delete Files',
                'Delete downloaded files as well?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            should_delete = (delete_files == QMessageBox.StandardButton.Yes)
        else:
            should_delete = False

        row = self.torrent_list.row(current)
        if row < len(self.active_torrents):
            tid = self.active_torrents[row]['id']
            self.torrent_session.remove_torrent(tid, should_delete)
            self.torrent_list.takeItem(row)
            if tid in self.torrent_widgets:
                del self.torrent_widgets[tid]
            del self.active_torrents[row]

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_device_manager(self):
        dialog = DeviceManagerDialog(self)
        dialog.exec()

    def show_about(self):
        QMessageBox.about(
            self, "About Qform",
            "Qform v1.0b\n\n"
            "Advanced torrent client\n"
            "Built with Python, libtorrent, PyQt6\n\n"
            "Features:\n"
            "- Resume downloads after restart\n"
            "- Detailed download statistics\n"
            "- Device manager for file transfers\n"
            "- Automatic progress saving"
        )

    def apply_theme(self, theme):
        themes = {
            "Dark Gray": """
                QMainWindow { background-color: #2b2b2b; color: #e0e0e0; }
                QPushButton { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555; padding: 5px 10px; border-radius: 3px; }
                QPushButton:hover { background-color: #4c5052; }
                QLineEdit { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555; padding: 5px; border-radius: 3px; }
                QProgressBar { background-color: #3c3f41; border: 1px solid #555; border-radius: 3px; text-align: center; color: #e0e0e0; }
                QProgressBar::chunk { background-color: #4caf50; border-radius: 3px; }
                QLabel { color: #e0e0e0; }
                QGroupBox { color: #e0e0e0; border: 1px solid #555; padding-top: 15px; margin-top: 10px; border-radius: 3px; }
                QGroupBox::title { color: #4caf50; }
                QListWidget { background-color: #313335; color: #e0e0e0; border: 1px solid #555; }
                QListWidget::item:selected { background-color: #4caf50; }
                QMenuBar { background-color: #3c3f41; color: #e0e0e0; border-bottom: 1px solid #555; }
                QMenuBar::item:selected { background-color: #4c5052; }
                QMenu { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555; }
                QMenu::item:selected { background-color: #4caf50; }
                QStatusBar { background-color: #3c3f41; color: #e0e0e0; border-top: 1px solid #555; }
                QComboBox { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555; padding: 5px; }
                QCheckBox { color: #e0e0e0; }
                QSpinBox { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555; padding: 5px; }
            """,
            "Dark": """
                QMainWindow { background-color: #1a1a1a; color: #d0d0d0; }
                QPushButton { background-color: #2d2d2d; color: #d0d0d0; border: 1px solid #404040; padding: 5px 10px; border-radius: 3px; }
                QPushButton:hover { background-color: #3d3d3d; }
                QLineEdit { background-color: #2d2d2d; color: #d0d0d0; border: 1px solid #404040; padding: 5px; border-radius: 3px; }
                QProgressBar { background-color: #2d2d2d; border: 1px solid #404040; border-radius: 3px; text-align: center; color: #d0d0d0; }
                QProgressBar::chunk { background-color: #0078d4; border-radius: 3px; }
                QLabel { color: #d0d0d0; }
                QGroupBox { color: #d0d0d0; border: 1px solid #404040; padding-top: 15px; margin-top: 10px; border-radius: 3px; }
                QGroupBox::title { color: #0078d4; }
                QListWidget { background-color: #252525; color: #d0d0d0; border: 1px solid #404040; }
                QListWidget::item:selected { background-color: #0078d4; }
                QMenuBar { background-color: #2d2d2d; color: #d0d0d0; border-bottom: 1px solid #404040; }
                QMenuBar::item:selected { background-color: #3d3d3d; }
                QMenu { background-color: #2d2d2d; color: #d0d0d0; border: 1px solid #404040; }
                QMenu::item:selected { background-color: #0078d4; }
                QStatusBar { background-color: #2d2d2d; color: #d0d0d0; border-top: 1px solid #404040; }
                QComboBox { background-color: #2d2d2d; color: #d0d0d0; border: 1px solid #404040; padding: 5px; }
                QCheckBox { color: #d0d0d0; }
                QSpinBox { background-color: #2d2d2d; color: #d0d0d0; border: 1px solid #404040; padding: 5px; }
            """
        }

        if theme in themes:
            self.setStyleSheet(themes[theme])
            self.current_theme = theme

    def apply_language(self, lang):
        translations = {
            "English": {
                "window_title": "Qform",
                "add_group": "Add Torrent",
                "browse": "Browse",
                "add_torrent": "Add Torrent",
                "torrents_group": "Torrents",
                "resume": "Resume",
                "pause": "Pause",
                "remove": "Remove",
                "file_menu": "File",
                "tools_menu": "Tools",
                "help_menu": "Help"
            },
            "Russian": {
                "window_title": "Qform",
                "add_group": "Добавить торрент",
                "browse": "Обзор",
                "add_torrent": "Добавить",
                "torrents_group": "Торренты",
                "resume": "Продолжить",
                "pause": "Пауза",
                "remove": "Удалить",
                "file_menu": "Файл",
                "tools_menu": "Инструменты",
                "help_menu": "Помощь"
            }
        }

        if lang in translations:
            t = translations[lang]
            self.setWindowTitle(t["window_title"])
            self.resume_btn.setText(t["resume"])
            self.pause_btn.setText(t["pause"])
            self.remove_btn.setText(t["remove"])

            menubar = self.menuBar()
            if menubar.actions():
                menubar.actions()[0].setText(t["file_menu"])
                menubar.actions()[1].setText(t["tools_menu"])
                menubar.actions()[2].setText(t["help_menu"])

    def save_settings(self):
        settings = {
            'theme': self.current_theme,
            'language': self.current_language,
            'confirm_delete': self.confirm_delete,
            'confirm_stop': self.confirm_stop,
            'confirm_exit': self.confirm_exit
        }

        settings_path = os.path.join(os.environ['APPDATA'], 'Qform', 'settings', 'default.json')
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        settings_path = os.path.join(os.environ['APPDATA'], 'Qform', 'settings', 'default.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    self.current_theme = settings.get('theme', 'Dark Gray')
                    self.current_language = settings.get('language', 'English')
                    self.confirm_delete = settings.get('confirm_delete', True)
                    self.confirm_stop = settings.get('confirm_stop', True)
                    self.confirm_exit = settings.get('confirm_exit', True)
            except:
                pass

    def closeEvent(self, event):
        if self.confirm_exit:
            reply = QMessageBox.question(
                self, 'Exit Qform',
                'Exit and save all downloads?\nProgress will be saved automatically.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        if self.torrent_session:
            self.torrent_session.save_all_progress()
            self.torrent_session.stop()
            self.torrent_session.wait()

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("Qform")
    app.setApplicationName("Qform")
    app.setApplicationVersion("1.0b")

    app_data = os.path.join(os.environ['APPDATA'], 'Qform')
    if not os.path.exists(app_data):
        QMessageBox.information(
            None, "Qform Setup",
            "Welcome to Qform!\n\n"
            "Qform will now configure itself for first use.\n"
            "Your downloads and settings will be saved automatically."
        )
        Installer.install()

    window = QformMain()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()