<div align="center">

# QformTorrent

<img src="https://img.shields.io/badge/version-1.1c-blue?style=flat-square" alt="version">
<img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="platform">
<img src="https://img.shields.io/badge/python-3.8+-blue?style=flat-square" alt="python">
<img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="license">

*Fast and minimal torrent client*

</div>

---

## What is this?

Qform is a torrent client built with Python, libtorrent and PyQt6. It allows downloading files via BitTorrent protocol with a simple and clean interface.

## Security & Virus-Free Guarantee 

This project is fully open-source, transparent, and safe to use. Here is how you can verify its security:

1. **Run from Source Code:** If you are skeptical about running the pre-compiled `.exe` file, you can run the client directly via Python. The entire codebase is clean and human-readable.
   ```bash
   pip install -r requirements.txt
   python main.py
   ```
2. **False Positives Note:** The standalone `.exe` release is compiled from Python scripts using packaging tools (like PyInstaller/Nuitka). Some antivirus engines may trigger false positives on packed Python binaries. 
3. **VirusTotal Reports:** You can always upload the latest release to [VirusTotal]([https://virustotal.com](https://www.virustotal.com/gui/file/41a7e52c892bc62cee71975a7751d94215a5f61e0e9c2fe8dbe938181a988146?nocache=1)). The official builds maintain a `1` detection rate.


## Features

- **Download torrents** from magnet links and .torrent files
- **Multiple downloads** support
- **Resume capability** - continue downloads after restart
- **Speed control** with download/upload limits
- **Device manager** for transferring files to external drives
- **Dark theme** with two variants
- **Russian and English** interface
- **Portable** - works from any folder
- **Auto-save** - progress saved every 5 seconds

## Screenshots

<p align="center">
  <img src="screenshots/main.png" width="400" alt="Main window">
  <img src="screenshots/downloading.png" width="400" alt="Downloading">
</p>

## How it works

Qform uses **libtorrent** session with DHT, LSD, UPnP and NAT-PMP enabled for maximum connectivity. It creates resume files in `%APPDATA%/Qform/resume/` to save download progress between sessions.

The application periodically saves torrent state every 5 seconds, ensuring no data loss on unexpected shutdown.

## Installation

## Option 2: Download release
Download the latest `Qform.exe` from [Releases](https://github.com/tourrty-droid/qform/releases) and run it.

## Requirements
```
qform/
├── main.py # Main application
├── uninstall.py # Uninstaller
├── requirements.txt # Dependencies
├── screenshots/ # Screenshots
└── README.md
```
## Usage

1. Launch `Qformtorrent.exe`
2. Paste **magnet link** or select **.torrent file**
3. Choose download directory
4. Click **Add Torrent**
## Configuration

Settings are stored in `%APPDATA%/Qform/settings/default.json`:

```json
{
  "theme": "Dark Gray",
  "language": "English",
  "download_path": "~/Downloads",
  "confirm_delete": true,
  "confirm_exit": true
}
```
## FAQ

**Q: Downloads don't start?**  
A: Check if port 6881 is open. Try adding trackers.

**Q: How to resume downloads?**  
A: Progress saves automatically. Just reopen the app.

**Q: Where are files saved?**  
A: Default is `~/Downloads`. Change in settings.

**Q: Does it work on Linux?**  
A: Currently Windows only. Linux support planned.

<div align="center">
  <sub>Built with Python, libtorrent and PyQt6</sub>
</div>
