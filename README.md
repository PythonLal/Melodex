# Melodex

Melodex is a modern, high-performance desktop application for downloading audio and video from YouTube and other supported platforms. Built with Python, PyWebView, and powered by `yt-dlp` and `aria2c`, it features a stunning Neon Glassmorphism UI and lightning-fast download speeds.

## Features
- **Beautiful UI:** A modern, responsive Neon Glassmorphism interface.
- **High Performance:** Multi-threaded downloading with concurrent fragments and `aria2c` integration for maximum speeds.
- **Versatile:** Download single videos or entire playlists.
- **Flexible Formats:** Choose your preferred video resolution or audio bitrate.
- **Thumbnail Embedding:** Automatically embed video thumbnails into your downloaded audio files.

## Prerequisites
Before running Melodex, ensure you have the following installed on your system:

1. **Python 3.8+**
2. **yt-dlp:** The core downloading engine.
3. **aria2c:** (Optional but recommended) For significantly faster, multi-connection downloads.

### Installing Dependencies (Linux/Debian)
```bash
# Install aria2c
sudo apt-get update && sudo apt-get install -y aria2

# Install Python requirements
pip install -r requirements.txt
```

## Running the App
Since Melodex is a native desktop application using `pywebview`, you run it directly from your terminal:

```bash
python3 main.py
```

## Project Structure
- `main.py` - Entry point that initializes the desktop window.
- `downloader.py` - The core backend logic handling `yt-dlp` subprocesses and queue management.
- `config.py` - Application configuration and system dependency paths.
- `db.py` - SQLite database wrapper for maintaining the download queue state.
- `ui/` - Contains the frontend HTML, CSS (Neon Glassmorphism), and modular Javascript.

## License
MIT License
