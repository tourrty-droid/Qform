import sys
import os
import time
import json
import pickle
import shutil
import requests
from datetime import datetime, timedelta
from collections import deque
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QLabel,
                             QProgressBar, QLineEdit, QTextEdit, QMessageBox,
                             QDialog, QComboBox, QCheckBox, QDialogButtonBox,
                             QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
                             QFrame, QStatusBar, QSplitter, QSystemTrayIcon, QMenu,
                             QSpinBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QAction, QPainter, QColor, QPen, QBrush, QKeySequence
import libtorrent as lt


# ============== RESUME DATA ==============
class ResumeData:
    def __init__(self):
        self.dir = os.path.join(os.environ['APPDATA'], 'Qform', 'resume')
        os.makedirs(self.dir, exist_ok=True)

    def save(self, tid, data):
        path = os.path.join(self.dir, f"{tid}.resume")
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    def load(self, tid):
        path = os.path.join(self.dir, f"{tid}.resume")
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return pickle.load(f)
        return None

    def delete(self, tid):
        path = os.path.join(self.dir, f"{tid}.resume")
        if os.path.exists(path):
            os.remove(path)

    def load_all(self):
        resumes = []
        if os.path.exists(self.dir):
            for fn in os.listdir(self.dir):
                if fn.endswith('.resume'):
                    tid = fn.replace('.resume', '')
                    data = self.load(tid)
                    if data:
                        data['id'] = tid
                        resumes.append(data)
        return resumes


# ============== SPEED CHART ==============
class SpeedChart(QWidget):
    def __init__(self):
        super().__init__()
        self.dl = deque(maxlen=300)
        self.ul = deque(maxlen=300)
        for _ in range(300):
            self.dl.append(0)
            self.ul.append(0)
        self.setMinimumHeight(100)

    def add_point(self, d, u):
        self.dl.append(d)
        self.ul.append(u)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor('#1a1a1a'))
        p.setPen(QPen(QColor('#333'), 0.5))
        for i in range(4):
            p.drawLine(0, h * i // 4, w, h * i // 4)
        mx = max(max(self.dl), max(self.ul), 1)
        p.setPen(QPen(QColor('#4caf50'), 2))
        for i in range(1, len(self.dl)):
            p.drawLine(int((i - 1) * w / 300), int(h - self.dl[i - 1] / mx * (h - 10)),
                       int(i * w / 300), int(h - self.dl[i] / mx * (h - 10)))
        p.setPen(QPen(QColor('#2196f3'), 2))
        for i in range(1, len(self.ul)):
            p.drawLine(int((i - 1) * w / 300), int(h - self.ul[i - 1] / mx * (h - 10)),
                       int(i * w / 300), int(h - self.ul[i] / mx * (h - 10)))


# ============== TORRENT WIDGET ==============
class TorrentWidget(QFrame):
    def __init__(self, tid, name):
        super().__init__()
        self.tid = tid
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setMaximumHeight(140)
        l = QVBoxLayout(self)
        l.setSpacing(2)
        self.name_label = QLabel(name[:55] + "..." if len(name) > 55 else name)
        self.name_label.setStyleSheet("font-weight:bold;font-size:11px;")
        l.addWidget(self.name_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        l.addWidget(self.progress_bar)
        r1 = QHBoxLayout()
        self.status_label = QLabel("...")
        self.eta_label = QLabel("ETA: --")
        r1.addWidget(self.status_label)
        r1.addStretch()
        r1.addWidget(self.eta_label)
        l.addLayout(r1)
        r2 = QHBoxLayout()
        self.speed_label = QLabel("DL:0 UL:0")
        self.peers_label = QLabel("P:0 S:0")
        self.size_label = QLabel("0/0")
        r2.addWidget(self.speed_label)
        r2.addWidget(self.peers_label)
        r2.addWidget(self.size_label)
        r2.addStretch()
        l.addLayout(r2)
        r3 = QHBoxLayout()
        self.downloaded_label = QLabel("DL:0")
        self.uploaded_label = QLabel("UL:0")
        self.time_label = QLabel("00:00")
        r3.addWidget(self.downloaded_label)
        r3.addWidget(self.uploaded_label)
        r3.addStretch()
        r3.addWidget(self.time_label)
        l.addLayout(r3)


# ============== SETTINGS DIALOG ==============
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p = parent
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setModal(True)
        l = QVBoxLayout(self)
        l.setSpacing(10)

        g1 = QGroupBox("Theme")
        l1 = QVBoxLayout()
        self.theme = QComboBox()
        self.theme.addItems(["Dark Gray", "Dark"])
        self.theme.currentTextChanged.connect(lambda t: self.p.apply_theme(t) if self.p else None)
        l1.addWidget(self.theme)
        g1.setLayout(l1)
        l.addWidget(g1)

        g2 = QGroupBox("Language")
        l2 = QVBoxLayout()
        self.lang = QComboBox()
        self.lang.addItems(["English", "Russian"])
        l2.addWidget(self.lang)
        g2.setLayout(l2)
        l.addWidget(g2)

        g4 = QGroupBox("Confirmations")
        l4 = QVBoxLayout()
        self.cd = QCheckBox("Confirm delete")
        self.cs = QCheckBox("Confirm stop")
        self.ce = QCheckBox("Confirm exit")
        l4.addWidget(self.cd)
        l4.addWidget(self.cs)
        l4.addWidget(self.ce)
        g4.setLayout(l4)
        l.addWidget(g4)

        if self.p:
            self.theme.setCurrentText(self.p.current_theme)
            self.lang.setCurrentText(self.p.current_language)
            self.cd.setChecked(self.p.confirm_delete)
            self.cs.setChecked(self.p.confirm_stop)
            self.ce.setChecked(self.p.confirm_exit)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        l.addWidget(bb)

    def save(self):
        if self.p:
            self.p.current_theme = self.theme.currentText()
            self.p.current_language = self.lang.currentText()
            self.p.confirm_delete = self.cd.isChecked()
            self.p.confirm_stop = self.cs.isChecked()
            self.p.confirm_exit = self.ce.isChecked()
            self.p.apply_language(self.lang.currentText())
            self.p.apply_theme(self.theme.currentText())
            self.p.save_settings()
        self.accept()


# ============== DEVICE MANAGER ==============
class DeviceManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Manager")
        self.setMinimumSize(500, 350)
        l = QVBoxLayout(self)
        l.addWidget(QLabel("Connected Devices"))
        self.devices = QListWidget()
        self.detect()
        l.addWidget(self.devices)
        btn = QPushButton("Transfer Files")
        btn.clicked.connect(self.transfer)
        l.addWidget(btn)

    def detect(self):
        self.devices.clear()
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            if os.path.exists(f"{letter}:\\"):
                self.devices.addItem(f"Drive: {letter}:\\")

    def transfer(self):
        if not self.devices.selectedItems():
            QMessageBox.warning(self, "Error", "Select device")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if files:
            dest = self.devices.selectedItems()[0].text().split(": ")[1] if ": " in self.devices.selectedItems()[
                0].text() else self.devices.selectedItems()[0].text()
            try:
                for f in files:
                    shutil.copy2(f, os.path.join(dest, os.path.basename(f)))
                QMessageBox.information(self, "Done", f"Transferred {len(files)} files")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


# ============== TRACKER DIALOG ==============
class TrackerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trackers")
        self.setMinimumSize(550, 450)
        l = QVBoxLayout(self)
        g = QGroupBox("Options")
        gl = QVBoxLayout()
        self.auto_add = QCheckBox("Add trackers to torrent automatically")
        self.auto_add.setChecked(True)
        gl.addWidget(self.auto_add)
        self.auto_upd = QCheckBox("Update trackers list everyday")
        self.auto_upd.toggled.connect(lambda c: [self.url.setEnabled(c), self.upd_btn.setEnabled(c)])
        gl.addWidget(self.auto_upd)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://cf.trackerslist.com/best.txt")
        self.url.setEnabled(False)
        self.upd_btn = QPushButton("Update Now")
        self.upd_btn.setEnabled(False)
        self.upd_btn.clicked.connect(self.update_list)
        hl = QHBoxLayout()
        hl.addWidget(self.url)
        hl.addWidget(self.upd_btn)
        gl.addLayout(hl)
        g.setLayout(gl)
        l.addWidget(g)
        l.addWidget(QLabel("Tracker List:"))
        self.list = QTextEdit()
        self.load_trackers()
        l.addWidget(self.list)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        l.addWidget(bb)

    def load_trackers(self):
        p = os.path.join(os.environ['APPDATA'], 'Qform', 'trackers', 'list.json')
        if os.path.exists(p):
            with open(p) as f:
                self.list.setText('\n'.join(json.load(f)))

    def update_list(self):
        try:
            r = requests.get(self.url.text().strip(), timeout=10)
            if r.status_code == 200:
                trackers = [l.strip() for l in r.text.split('\n') if l.strip() and not l.startswith('#')]
                self.list.setText('\n'.join(trackers))
                QMessageBox.information(self, "Done", f"Loaded {len(trackers)} trackers")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def save(self):
        trackers = [t.strip() for t in self.list.toPlainText().split('\n') if t.strip()]
        p = os.path.join(os.environ['APPDATA'], 'Qform', 'trackers', 'list.json')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            json.dump(trackers, f, indent=4)
        self.accept()


# ============== TORRENT SESSION ==============
class TorrentSession(QThread):
    progress_update = pyqtSignal(str, dict)
    torrent_added = pyqtSignal(str, str)
    download_complete = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.session = None
        self.torrents = {}
        self.is_running = True
        self.resume = ResumeData()

    def run(self):
        self.session = lt.session({
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True
        })
        self.load_saved()

        while self.is_running:
            try:
                if self.session:
                    self.session.post_torrent_updates()

                    for tid, data in list(self.torrents.items()):
                        if data['handle'].is_valid():
                            s = data['handle'].status()

                            if s.download_rate > 0 and s.total_wanted > 0:
                                remaining = s.total_wanted - s.total_wanted_done
                                eta_seconds = remaining / s.download_rate
                                eta = str(timedelta(seconds=int(eta_seconds)))
                            else:
                                eta = "inf"

                            elapsed = str(timedelta(seconds=s.active_time))
                            state_int = int(s.state)
                            sm = {0: "Queued", 1: "Checking", 2: "Metadata", 3: "Downloading",
                                  4: "Finished", 5: "Seeding", 6: "Allocating", 7: "Resume check"}
                            st = sm.get(state_int, f"State {state_int}")

                            if data.get('user_paused', False):
                                st = "Paused"

                            info = {
                                'progress': s.progress * 100,
                                'download_rate': s.download_rate / 1024,
                                'upload_rate': s.upload_rate / 1024,
                                'peers': s.num_peers,
                                'seeds': s.num_seeds,
                                'state': st,
                                'total_size': s.total_wanted,
                                'total_done': s.total_done,
                                'total_uploaded': s.total_upload,
                                'name': data['name'],
                                'eta': eta,
                                'elapsed': elapsed,
                                'paused': data.get('user_paused', False)
                            }
                            self.progress_update.emit(tid, info)

                            if s.is_seeding and not data.get('completed'):
                                self.torrents[tid]['completed'] = True
                                self.download_complete.emit(tid, data['name'])

                time.sleep(1)
            except Exception as e:
                print(f"Session error: {e}")

    def add_torrent(self, tid, source, save_path):
        try:
            params = {
                'save_path': save_path,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse
            }

            resume_data = self.resume.load(tid)

            if source.startswith('magnet:'):
                h = lt.add_magnet_uri(self.session, source, params)
                timeout = 0
                while not h.has_metadata():
                    time.sleep(1)
                    timeout += 1
                    if timeout > 120:
                        raise Exception("Metadata timeout")
            else:
                info = lt.torrent_info(source)
                h = self.session.add_torrent({'ti': info, 'save_path': save_path})

            if resume_data and 'resume_bytes' in resume_data:
                try:
                    h.apply_resume_data(resume_data['resume_bytes'])
                except:
                    pass

            name = h.status().name or os.path.basename(source)
            self.torrents[tid] = {
                'handle': h,
                'source': source,
                'save_path': save_path,
                'name': name,
                'added_date': datetime.now().isoformat(),
                'completed': False,
                'user_paused': False
            }
            self.torrent_added.emit(tid, name)
            self.save_progress(tid)
            return True
        except Exception as e:
            print(f"Add error: {e}")
            return False

    def remove_torrent(self, tid, delete_files=False):
        if tid in self.torrents:
            if delete_files:
                try:
                    h = self.torrents[tid]['handle']
                    if h.is_valid():
                        info = h.torrent_file()
                        if info:
                            for f in info.files():
                                fp = os.path.join(self.torrents[tid]['save_path'], f.path)
                                if os.path.exists(fp):
                                    os.remove(fp)
                except:
                    pass
            self.session.remove_torrent(self.torrents[tid]['handle'])
            self.resume.delete(tid)
            del self.torrents[tid]

    def pause_torrent(self, tid):
        if tid in self.torrents:
            h = self.torrents[tid]['handle']
            h.auto_managed(False)
            h.pause()
            self.torrents[tid]['user_paused'] = True
            self.save_progress(tid)

    def resume_torrent(self, tid):
        if tid in self.torrents:
            h = self.torrents[tid]['handle']
            h.auto_managed(True)
            h.resume()
            self.torrents[tid]['user_paused'] = False

    def save_progress(self, tid):
        if tid in self.torrents:
            d = self.torrents[tid]
            if d['handle'].is_valid():
                try:
                    self.resume.save(tid, {
                        'source': d['source'],
                        'save_path': d['save_path'],
                        'name': d['name'],
                        'added_date': d['added_date'],
                        'resume_bytes': d['handle'].save_resume_data()
                    })
                except:
                    pass

    def save_all_progress(self):
        for tid in self.torrents:
            self.save_progress(tid)

    def load_saved(self):
        for d in self.resume.load_all():
            if d and 'source' in d and 'save_path' in d:
                self.add_torrent(d['id'], d['source'], d['save_path'])

    def stop(self):
        self.is_running = False
        self.save_all_progress()
        if self.session:
            self.session.pause()


# ============== MAIN WINDOW ==============
class QformMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.torrent_widgets = {}
        self.active_torrents = []
        self.current_theme = "Dark Gray"
        self.current_language = "English"
        self.confirm_delete = True
        self.confirm_stop = True
        self.confirm_exit = True

        self.load_settings()
        self.setup_tray()
        self.initUI()
        self.create_menu()
        self.create_statusbar()
        self.apply_theme(self.current_theme)
        self.apply_language(self.current_language)

        self.torrent_session = TorrentSession()
        self.torrent_session.progress_update.connect(self.update_torrent_info)
        self.torrent_session.torrent_added.connect(self.on_torrent_added)
        self.torrent_session.download_complete.connect(self.on_download_complete)
        self.torrent_session.start()

        self.chart_timer = QTimer()
        self.chart_timer.timeout.connect(self.update_chart)
        self.chart_timer.start(1000)

        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.auto_save)
        self.save_timer.start(5000)

    def auto_save(self):
        if self.torrent_session:
            self.torrent_session.save_all_progress()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Qform")
        m = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        m.addAction(show_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        m.addAction(exit_action)
        self.tray.setContextMenu(m)
        self.tray.show()

    def initUI(self):
        self.setWindowTitle("Qform")
        self.setMinimumSize(900, 650)

        c = QWidget()
        self.setCentralWidget(c)
        l = QVBoxLayout(c)
        l.setSpacing(8)
        l.setContentsMargins(10, 10, 10, 10)

        ag = QGroupBox("Add Torrent")
        al = QVBoxLayout()
        sl = QHBoxLayout()
        self.src = QLineEdit()
        self.src.setPlaceholderText("magnet link or .torrent path")
        browse_t_btn = QPushButton("Browse")
        browse_t_btn.clicked.connect(self.browse_torrent)
        sl.addWidget(self.src)
        sl.addWidget(browse_t_btn)
        al.addLayout(sl)
        pl = QHBoxLayout()
        self.path = QLineEdit(os.path.expanduser("~/Downloads"))
        browse_p_btn = QPushButton("Browse")
        browse_p_btn.clicked.connect(self.browse_path)
        pl.addWidget(self.path)
        pl.addWidget(browse_p_btn)
        al.addLayout(pl)
        add_btn = QPushButton("Add Torrent")
        add_btn.clicked.connect(self.add_torrent)
        al.addWidget(add_btn)
        ag.setLayout(al)
        l.addWidget(ag)

        sp = QSplitter(Qt.Orientation.Vertical)
        tg = QGroupBox("Torrents")
        tl = QVBoxLayout()
        self.tlist = QListWidget()
        self.tlist.setMinimumHeight(200)
        tl.addWidget(self.tlist)
        cl = QHBoxLayout()
        self.rbtn = QPushButton("Resume")
        self.rbtn.clicked.connect(self.resume_selected)
        self.pbtn = QPushButton("Pause")
        self.pbtn.clicked.connect(self.pause_selected)
        self.dbtn = QPushButton("Remove")
        self.dbtn.clicked.connect(self.remove_selected)
        cl.addWidget(self.rbtn)
        cl.addWidget(self.pbtn)
        cl.addWidget(self.dbtn)
        cl.addStretch()
        tl.addLayout(cl)
        tg.setLayout(tl)
        sp.addWidget(tg)
        self.chart = SpeedChart()
        sp.addWidget(self.chart)
        l.addWidget(sp)

        self.gspeed = QLabel("Total: DL 0 KB/s UL 0 KB/s | Active: 0 | Peers: 0")
        l.addWidget(self.gspeed)

    def create_menu(self):
        mb = self.menuBar()
        mb.setNativeMenuBar(False)

        f = mb.addMenu('File')

        add_t = QAction('Add Torrent...', self)
        add_t.setShortcut(QKeySequence('Ctrl+O'))
        add_t.triggered.connect(self.browse_torrent)
        f.addAction(add_t)

        add_m = QAction('Add Magnet...', self)
        add_m.setShortcut(QKeySequence('Ctrl+M'))
        add_m.triggered.connect(lambda: self.src.setFocus())
        f.addAction(add_m)

        f.addSeparator()

        rem = QAction('Remove', self)
        rem.setShortcut(QKeySequence('Delete'))
        rem.triggered.connect(self.remove_selected)
        f.addAction(rem)

        f.addSeparator()

        ex = QAction('Exit', self)
        ex.setShortcut(QKeySequence('Alt+F4'))
        ex.triggered.connect(self.close)
        f.addAction(ex)

        t = mb.addMenu('Tools')

        tm = t.addMenu('Task')

        qf = QAction('Qform Files', self)
        qf.triggered.connect(lambda: os.startfile(os.path.join(os.environ['APPDATA'], 'Qform')))
        tm.addAction(qf)

        tr = QAction('Trackers...', self)
        tr.triggered.connect(lambda: TrackerDialog(self).exec())
        tm.addAction(tr)

        tm.addSeparator()

        dm = QAction('Device Manager...', self)
        dm.triggered.connect(lambda: DeviceManagerDialog(self).exec())
        t.addAction(dm)

        t.addSeparator()

        pr = QAction('Preferences...', self)
        pr.setShortcut(QKeySequence('Ctrl+P'))
        pr.triggered.connect(lambda: SettingsDialog(self).exec())
        t.addAction(pr)

        h = mb.addMenu('Help')

        ab = QAction('About', self)
        ab.triggered.connect(
            lambda: QMessageBox.about(self, "Qform", "Qform v1.2\n\nTorrent Client\nPython + libtorrent + PyQt6"))
        h.addAction(ab)

    def create_statusbar(self):
        self.sb = QStatusBar()
        self.setStatusBar(self.sb)
        self.sb.addPermanentWidget(QLabel("Qform v1.2"))
        self.sb.showMessage("Ready")

    def browse_torrent(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Torrent", "", "Torrent Files (*.torrent)")
        if f:
            self.src.setText(f)

    def browse_path(self):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d:
            self.path.setText(d)

    def add_torrent(self):
        s, p = self.src.text().strip(), self.path.text().strip()
        if not s or not p:
            QMessageBox.warning(self, "Error", "Provide source and path")
            return
        tid = str(int(time.time() * 1000))
        if self.torrent_session.add_torrent(tid, s, p):
            self.src.clear()
            self.sb.showMessage("Torrent added", 3000)

    def on_torrent_added(self, tid, name):
        item = QListWidgetItem()
        w = TorrentWidget(tid, name)
        item.setSizeHint(w.sizeHint())
        self.tlist.addItem(item)
        self.tlist.setItemWidget(item, w)
        self.torrent_widgets[tid] = w
        self.active_torrents.append({'id': tid, 'name': name, 'item': item})

    def on_download_complete(self, tid, name):
        self.tray.showMessage("Download Complete", f"{name} finished", QSystemTrayIcon.MessageIcon.Information, 5000)

    def update_torrent_info(self, tid, info):
        if tid in self.torrent_widgets:
            w = self.torrent_widgets[tid]
            w.progress_bar.setValue(int(info['progress']))
            w.status_label.setText(info['state'])
            w.eta_label.setText(f"ETA: {info['eta']}")
            w.speed_label.setText(f"DL:{info['download_rate']:.1f} UL:{info['upload_rate']:.1f}")
            w.peers_label.setText(f"P:{info['peers']} S:{info['seeds']}")
            w.time_label.setText(f"Time: {info['elapsed']}")

            def fb(b):
                for u in ['B', 'KB', 'MB', 'GB']:
                    if b < 1024:
                        return f"{b:.1f}{u}"
                    b /= 1024
                return f"{b:.1f}TB"

            w.size_label.setText(f"{fb(info['total_done'])}/{fb(info['total_size'])}")
            w.downloaded_label.setText(f"DL:{fb(info['total_done'])}")
            w.uploaded_label.setText(f"UL:{fb(info['total_uploaded'])}")

            colors = {
                "Downloading": "#4caf50",
                "Seeding": "#2196f3",
                "Finished": "#ff9800",
                "Paused": "#9e9e9e",
                "Checking": "#ffeb3b"
            }
            w.status_label.setStyleSheet(f"font-weight:bold;color:{colors.get(info['state'], '#e0e0e0')}")

        ts = self.torrent_session
        tdl = sum(ts.torrents[t]['handle'].status().download_rate / 1024 for t in ts.torrents) if ts else 0
        tul = sum(ts.torrents[t]['handle'].status().upload_rate / 1024 for t in ts.torrents) if ts else 0
        tp = sum(ts.torrents[t]['handle'].status().num_peers for t in ts.torrents) if ts else 0
        self.gspeed.setText(
            f"Total: DL {tdl:.1f} KB/s UL {tul:.1f} KB/s | Active: {len(self.torrent_widgets)} | Peers: {tp}")

    def update_chart(self):
        if self.torrent_session:
            dl = sum(self.torrent_session.torrents[t]['handle'].status().download_rate / 1024 for t in
                     self.torrent_session.torrents)
            ul = sum(self.torrent_session.torrents[t]['handle'].status().upload_rate / 1024 for t in
                     self.torrent_session.torrents)
            self.chart.add_point(dl, ul)

    def pause_selected(self):
        c = self.tlist.currentItem()
        if c:
            r = self.tlist.row(c)
            if r < len(self.active_torrents):
                tid = self.active_torrents[r]['id']
                self.torrent_session.pause_torrent(tid)

    def resume_selected(self):
        c = self.tlist.currentItem()
        if c:
            r = self.tlist.row(c)
            if r < len(self.active_torrents):
                tid = self.active_torrents[r]['id']
                self.torrent_session.resume_torrent(tid)

    def remove_selected(self):
        c = self.tlist.currentItem()
        if not c:
            return
        if self.confirm_delete:
            r = QMessageBox.question(self, 'Remove', 'Remove this torrent?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.No:
                return
            df = QMessageBox.question(self, 'Delete Files', 'Delete downloaded files?',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
            sd = df == QMessageBox.StandardButton.Yes
        else:
            sd = False

        row = self.tlist.row(c)
        if row < len(self.active_torrents):
            tid = self.active_torrents[row]['id']
            self.torrent_session.remove_torrent(tid, sd)
            self.tlist.takeItem(row)
            if tid in self.torrent_widgets:
                del self.torrent_widgets[tid]
            del self.active_torrents[row]

    def apply_theme(self, theme):
        themes = {
            "Dark Gray": """
                QMainWindow{background:#2b2b2b;color:#e0e0e0}
                QPushButton{background:#3c3f41;color:#e0e0e0;border:1px solid #555;padding:5px 10px;border-radius:3px}
                QPushButton:hover{background:#4c5052}
                QLineEdit{background:#3c3f41;color:#e0e0e0;border:1px solid #555;padding:5px;border-radius:3px}
                QProgressBar{background:#3c3f41;border:1px solid #555;border-radius:3px;text-align:center;color:#e0e0e0}
                QProgressBar::chunk{background:#4caf50;border-radius:3px}
                QLabel{color:#e0e0e0}
                QGroupBox{color:#e0e0e0;border:1px solid #555;padding-top:15px;margin-top:10px;border-radius:3px}
                QGroupBox::title{color:#4caf50}
                QListWidget{background:#313335;color:#e0e0e0;border:1px solid #555}
                QListWidget::item:selected{background:#4caf50}
                QMenuBar{background:#3c3f41;color:#e0e0e0;border-bottom:1px solid #555}
                QMenuBar::item:selected{background:#4c5052}
                QMenu{background:#3c3f41;color:#e0e0e0;border:1px solid #555}
                QMenu::item:selected{background:#4caf50}
                QStatusBar{background:#3c3f41;color:#e0e0e0;border-top:1px solid #555}
                QTextEdit{background:#313335;color:#e0e0e0;border:1px solid #555}
                QCheckBox{color:#e0e0e0}
                QComboBox{background:#3c3f41;color:#e0e0e0;border:1px solid #555;padding:5px}
                QSpinBox{background:#3c3f41;color:#e0e0e0;border:1px solid #555;padding:5px}
            """,
            "Dark": """
                QMainWindow{background:#1a1a1a;color:#d0d0d0}
                QPushButton{background:#2d2d2d;color:#d0d0d0;border:1px solid #404040;padding:5px 10px;border-radius:3px}
                QPushButton:hover{background:#3d3d3d}
                QLineEdit{background:#2d2d2d;color:#d0d0d0;border:1px solid #404040;padding:5px;border-radius:3px}
                QProgressBar{background:#2d2d2d;border:1px solid #404040;border-radius:3px;text-align:center;color:#d0d0d0}
                QProgressBar::chunk{background:#0078d4;border-radius:3px}
                QLabel{color:#d0d0d0}
                QGroupBox{color:#d0d0d0;border:1px solid #404040;padding-top:15px;margin-top:10px;border-radius:3px}
                QGroupBox::title{color:#0078d4}
                QListWidget{background:#252525;color:#d0d0d0;border:1px solid #404040}
                QListWidget::item:selected{background:#0078d4}
                QMenuBar{background:#2d2d2d;color:#d0d0d0;border-bottom:1px solid #404040}
                QMenuBar::item:selected{background:#3d3d3d}
                QMenu{background:#2d2d2d;color:#d0d0d0;border:1px solid #404040}
                QMenu::item:selected{background:#0078d4}
                QStatusBar{background:#2d2d2d;color:#d0d0d0;border-top:1px solid #404040}
                QTextEdit{background:#252525;color:#d0d0d0;border:1px solid #404040}
                QCheckBox{color:#d0d0d0}
                QComboBox{background:#2d2d2d;color:#d0d0d0;border:1px solid #404040;padding:5px}
                QSpinBox{background:#2d2d2d;color:#d0d0d0;border:1px solid #404040;padding:5px}
            """
        }
        if theme in themes:
            self.setStyleSheet(themes[theme])
            self.current_theme = theme

    def apply_language(self, lang):
        t = {
            "English": {"title": "Qform", "resume": "Resume", "pause": "Pause", "remove": "Remove",
                        "file": "File", "tools": "Tools", "help": "Help"},
            "Russian": {"title": "Qform", "resume": "Prodolzhit", "pause": "Pauza", "remove": "Udalit",
                        "file": "Fail", "tools": "Instrumenty", "help": "Pomoshch"}
        }
        if lang in t:
            self.setWindowTitle(t[lang]["title"])
            self.rbtn.setText(t[lang]["resume"])
            self.pbtn.setText(t[lang]["pause"])
            self.dbtn.setText(t[lang]["remove"])
            mb = self.menuBar()
            if mb.actions():
                mb.actions()[0].setText(t[lang]["file"])
                mb.actions()[1].setText(t[lang]["tools"])
                mb.actions()[2].setText(t[lang]["help"])
        self.current_language = lang

    def save_settings(self):
        s = {
            'theme': self.current_theme,
            'language': self.current_language,
            'confirm_delete': self.confirm_delete,
            'confirm_stop': self.confirm_stop,
            'confirm_exit': self.confirm_exit
        }
        p = os.path.join(os.environ['APPDATA'], 'Qform', 'settings', 'default.json')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            json.dump(s, f, indent=4)

    def load_settings(self):
        p = os.path.join(os.environ['APPDATA'], 'Qform', 'settings', 'default.json')
        if os.path.exists(p):
            try:
                with open(p) as f:
                    s = json.load(f)
                    self.current_theme = s.get('theme', 'Dark Gray')
                    self.current_language = s.get('language', 'English')
                    self.confirm_delete = s.get('confirm_delete', True)
                    self.confirm_stop = s.get('confirm_stop', True)
                    self.confirm_exit = s.get('confirm_exit', True)
            except:
                pass

    def closeEvent(self, e):
        if self.confirm_exit:
            r = QMessageBox.question(self, 'Exit', 'Save and exit?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.Yes)
            if r == QMessageBox.StandardButton.No:
                e.ignore()
                return
        if self.torrent_session:
            self.torrent_session.save_all_progress()
            self.torrent_session.stop()
            self.torrent_session.wait()
        e.accept()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("Qform")
    app.setApplicationName("Qform")
    app.setApplicationVersion("1.2")

    app_data = os.path.join(os.environ['APPDATA'], 'Qform')
    os.makedirs(app_data, exist_ok=True)
    for d in ['torrents', 'resume', 'settings', 'trackers']:
        os.makedirs(os.path.join(app_data, d), exist_ok=True)

    window = QformMain()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
