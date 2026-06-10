import os
import re
import json
import time
import uuid
import signal
import threading
import subprocess
import webview
from typing import List, Dict

from db import Database, init_db
from config import (
    YTDLP,
    DOWNLOAD_ENV,
    STATUS_WAITING,
    STATUS_DOWNLOADING,
    STATUS_PAUSED,
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_CANCELLED,
    FRAGMENT_COUNT,
    ENABLE_ARIA2,
    ARIA2_ARGS,
)

# ── Compiled regexes (module-level, compiled once) ─────────────────────────────

_PROG_RE = re.compile(r'\[download\]\s+([\d.]+)%')
_DEST_RE = re.compile(r'Destination:\s+(.+)')

# ── Downloader API ──────────────────────────────────────────────────────────────

class DownloaderAPI:
    def __init__(self):
        self.window = None
        self.is_downloading = False
        self.current_process: subprocess.Popen = None
        self.current_item_id: str = None
        self.is_paused = False
        init_db()

    def set_window(self, window):
        self.window = window

    def js_ready(self):
        self._sync_frontend()

    def _sync_frontend(self):
        if self.window:
            items = Database.get_all()
            self.window.evaluate_js(f"window.syncQueue({json.dumps(items)})")

    def get_queue(self) -> List[Dict]:
        return Database.get_all()

    def ask_folder(self):
        if not self.window:
            return None
        folder = self.window.create_file_dialog(webview.FileDialog.FOLDER)
        if folder and len(folder) > 0:
            return folder[0]
        return None

    def add_single(self, url: str, folder: str, quality: str,
                   embed_thumb: bool, title: str = "",
                   playlist_id: str = None, playlist_title: str = None):
        item = {
            'id':             str(uuid.uuid4())[:8],
            'url':            url,
            'folder':         folder,
            'quality':        quality,
            'embed_thumb':    embed_thumb,
            'title':          title,
            'playlist_id':    playlist_id,
            'playlist_title': playlist_title,
            'status':         STATUS_WAITING,
            'progress':       0.0,
        }
        Database.insert(item)
        self._sync_frontend()
        return item['id']

    # ── Playlist fetching ──────────────────────────────────────────────────────

    def fetch_playlist(self, url: str):
        """Fetch playlist metadata in a background thread; notifies the frontend."""
        def _fetch():
            MAX_RETRIES = 8
            best_entries: List[Dict] = []
            playlist_count = None

            for attempt in range(1, MAX_RETRIES + 1):
                if self.window:
                    self.window.evaluate_js(
                        f"window.onPlaylistProgress({len(best_entries)})"
                    )

                proc = subprocess.Popen(
                    [
                        YTDLP,
                        "--flat-playlist", "--yes-playlist",
                        "-j", "--no-warnings", "--ignore-errors",
                        url,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )

                entries: List[Dict] = []
                next_progress_at = 10  # report progress every 10 tracks

                for raw in proc.stdout:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if playlist_count is None and entry.get("playlist_count") is not None:
                            playlist_count = int(entry["playlist_count"])
                        entries.append({
                            "id":             entry.get("id"),
                            "title":          entry.get("title"),
                            "duration":       entry.get("duration"),
                            "playlist_title": entry.get("playlist_title"),
                            "playlist_id":    entry.get("playlist_id"),
                            "url":            entry.get("url") or entry.get("webpage_url") or "",
                        })
                        if self.window and len(entries) >= next_progress_at:
                            self.window.evaluate_js(
                                f"window.onPlaylistProgress({max(len(entries), len(best_entries))})"
                            )
                            next_progress_at += 10
                    except json.JSONDecodeError:
                        pass

                proc.wait()

                if len(entries) > len(best_entries):
                    best_entries = entries

                # Success: got everything
                if playlist_count is not None and len(best_entries) >= playlist_count:
                    break

                # Single video or non-truncated result — no need to retry
                if playlist_count is None and best_entries and len(best_entries) % 100 != 0:
                    break

                # Wait before retrying to let YouTube's rate-limit cool down
                if attempt < MAX_RETRIES:
                    time.sleep(2)

            if len(best_entries) == 1:
                # Query exact formats for a single video
                single_url = best_entries[0].get("url") or url
                try:
                    fp = subprocess.run([YTDLP, "-j", "--no-warnings", single_url],
                                        capture_output=True, text=True, timeout=15)
                    if fp.returncode == 0:
                        f_data = json.loads(fp.stdout.strip())
                        formats = f_data.get("formats", [])
                        v_heights = set()
                        a_abrs = set()
                        for f in formats:
                            h = f.get("height")
                            vc = f.get("vcodec")
                            if h and vc != "none":
                                v_heights.add(int(h))
                            abr = f.get("abr")
                            ac = f.get("acodec")
                            if abr and ac != "none":
                                a_abrs.add(int(float(abr)))
                        
                        best_entries[0]["available_heights"] = sorted(list(v_heights), reverse=True)
                        best_entries[0]["available_abrs"] = sorted(list(a_abrs), reverse=True)
                except Exception as e:
                    pass

            if self.window:
                self.window.evaluate_js(
                    f"window.onPlaylistLoaded({json.dumps(best_entries)})"
                )

        threading.Thread(target=_fetch, daemon=True).start()

    # ── Add confirmed playlist items ───────────────────────────────────────────

    def add_playlist_items(self, entries: List[Dict], folder: str,
                           quality: str, embed_thumb: bool,
                           playlist_title: str = "Playlist",
                           download_type: str = "audio"):
        is_playlist = len(entries) > 1 or (
            len(entries) == 1 and (
                entries[0].get("playlist_id") or entries[0].get("playlist_title")
            )
        )
        playlist_id = str(uuid.uuid4())[:8] if is_playlist else None
        pl_title    = playlist_title         if is_playlist else None

        rows = []
        for entry in entries:
            url = entry.get("url") or entry.get("webpage_url") or ""
            if not url.startswith("http"):
                vid_id = entry.get("id", "")
                url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""
            if not url:
                continue
            rows.append({
                'id':             str(uuid.uuid4())[:8],
                'url':            url,
                'folder':         folder,
                'quality':        quality,
                'embed_thumb':    embed_thumb,
                'title':          entry.get("title", ""),
                'playlist_id':    playlist_id,
                'playlist_title': pl_title,
                'status':         STATUS_WAITING,
                'progress':       0.0,
                'download_type':  download_type,
            })

        if rows:
            Database.insert_many(rows)   # single transaction
            self._sync_frontend()
            self.start_queue()

    # ── Queue management ───────────────────────────────────────────────────────

    def remove_item(self, id: str):
        if self.current_item_id == id and self.is_downloading:
            self.cancel_current()
        Database.delete(id)
        self._sync_frontend()

    def clear_done(self):
        Database.clear_done()
        self._sync_frontend()

    def start_queue(self):
        if self.is_downloading:
            return
        items = Database.get_all()
        waiting = [i for i in items if i['status'] == STATUS_WAITING]
        if waiting:
            self._start_download(waiting[0])

    def cancel_current(self):
        if self.current_process and self.is_downloading:
            if self.is_paused:
                os.kill(self.current_process.pid, signal.SIGCONT)
            self.is_downloading = False
            self.is_paused = False
            self.current_process.terminate()

    def pause_resume(self):
        if not self.current_process or not self.is_downloading:
            return
        if not self.is_paused:
            os.kill(self.current_process.pid, signal.SIGSTOP)
            self.is_paused = True
            Database.update_status(self.current_item_id, STATUS_PAUSED)
        else:
            os.kill(self.current_process.pid, signal.SIGCONT)
            self.is_paused = False
            Database.update_status(self.current_item_id, STATUS_DOWNLOADING)
        self._sync_frontend()

    def playlist_action(self, playlist_id: str, action: str):
        items    = Database.get_all()
        pl_items = [i for i in items if i.get('playlist_id') == playlist_id]

        if action == "cancel":
            for item in pl_items:
                if item['id'] == self.current_item_id and self.is_downloading:
                    self.cancel_current()
                Database.delete(item['id'])
        elif action == "pause":
            for item in pl_items:
                if item['id'] == self.current_item_id and self.is_downloading and not self.is_paused:
                    self.pause_resume()
                elif item['status'] == STATUS_WAITING:
                    Database.update_status(item['id'], STATUS_PAUSED)
        elif action == "resume":
            for item in pl_items:
                if item['id'] == self.current_item_id and self.is_downloading and self.is_paused:
                    self.pause_resume()
                elif item['status'] == STATUS_PAUSED:
                    Database.update_status(item['id'], STATUS_WAITING)
            self.start_queue()

        self._sync_frontend()

    # ── Logging ────────────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "info"):
        if self.window:
            escaped = msg.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '<br>')
            self.window.evaluate_js(f'window.addLog("{escaped}", "{tag}")')

    # ── Download worker ────────────────────────────────────────────────────────

    def _start_download(self, item: Dict):
        self.is_downloading = True
        self.is_paused = False
        self.current_item_id = item['id']
        Database.update_status(item['id'], STATUS_DOWNLOADING, 0)
        self._sync_frontend()
        threading.Thread(
            target=self._download_worker, args=(item,), daemon=True
        ).start()

    def _download_worker(self, item: Dict):
        template = os.path.join(item['folder'], "%(title)s.%(ext)s")
        cmd = [
            YTDLP,
            "--no-overwrites",
            "--add-metadata",
            "--concurrent-fragments", str(FRAGMENT_COUNT),
            "--output",             template,
            "--newline",
            "--cookies-from-browser", "firefox",
        ]
        # Add external downloader if enabled
        if ENABLE_ARIA2:
            cmd.extend([
                "--external-downloader", "aria2c",
                "--external-downloader-args", ARIA2_ARGS,
            ])
        
        dl_type = item.get('download_type', 'audio')
        if dl_type == 'video':
            cmd.extend([
                "-f", item['quality'],
                "--merge-output-format", "mp4"
            ])
            if item['embed_thumb']:
                cmd.append("--embed-thumbnail")
        else:
            cmd.extend([
                "-f", "bestaudio/best",
                "--extract-audio",
                "--audio-format",       "mp3",
                "--audio-quality",      f"{item['quality']}K",
            ])
            if item['embed_thumb']:
                cmd.append("--embed-thumbnail")

        cmd.append(item['url'])

        self._log(f"Starting: {item.get('title') or item['url']}", "head")

        last_update_time = 0.0
        last_update_pct  = -1.0

        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=DOWNLOAD_ENV,
            )

            for raw in self.current_process.stdout:
                line = raw.rstrip()
                if not line:
                    continue

                m_prog = _PROG_RE.search(line)
                if m_prog:
                    pct = float(m_prog.group(1))
                    now = time.monotonic()
                    # Throttle UI updates: max once per 0.5 s, min 0.5 % change
                    if pct == 100.0 or (
                        now - last_update_time > 0.5
                        and pct - last_update_pct >= 0.5
                    ):
                        last_update_time = now
                        last_update_pct  = pct
                        Database.update_status(item['id'], STATUS_DOWNLOADING, pct)
                        if self.window:
                            self.window.evaluate_js(
                                f"window.updateProgress('{item['id']}', {pct})"
                            )
                    continue

                m_dest = _DEST_RE.search(line)
                if m_dest:
                    fname = os.path.basename(m_dest.group(1).strip())
                    if not item.get('title'):
                        title = fname.rsplit(".", 1)[0]
                        Database.update_title(item['id'], title)
                        item['title'] = title   # update local copy so we don't re-fetch
                        self._sync_frontend()
                    self._log(f"Saving to: {fname}", "ok")
                    continue

                if "ERROR" in line or "error:" in line.lower():
                    self._log(line, "err")

            self.current_process.wait()
            rc = self.current_process.returncode

            if rc == 0:
                Database.update_status(item['id'], STATUS_DONE, 100)
                self._log("Download finished successfully.", "ok")
            elif not self.is_downloading:
                Database.update_status(item['id'], STATUS_CANCELLED)
                self._log("Download cancelled.", "warn")
            else:
                Database.update_status(item['id'], STATUS_ERROR)
                self._log(f"Download failed (exit code {rc}).", "err")

        except Exception as exc:
            Database.update_status(item['id'], STATUS_ERROR)
            self._log(f"Error: {exc}", "err")
        finally:
            self.is_downloading    = False
            self.is_paused         = False
            self.current_process   = None
            self.current_item_id   = None
            self._sync_frontend()
            self.start_queue()   # advance to next item
