import os

# ── Constants ──────────────────────────────────────────────────────────────────

DB_FILE = os.path.join(os.path.dirname(__file__), 'queue.db')

STATUS_WAITING    = "waiting"
STATUS_DOWNLOADING = "downloading"
STATUS_PAUSED     = "paused"
STATUS_DONE       = "done"
STATUS_ERROR      = "error"
STATUS_CANCELLED  = "cancelled"

# ── Resolve yt-dlp path once at startup ────────────────────────────────────────

def _find_ytdlp() -> str:
    for path in ["/usr/local/bin/yt-dlp", "/usr/bin/yt-dlp", "/bin/yt-dlp"]:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return "yt-dlp"

YTDLP = _find_ytdlp()

# ── Build the custom environment once (adds deno to PATH) ──────────────────────

def _build_env() -> dict:
    env = os.environ.copy()
    deno_bin = os.path.expanduser("~/.deno/bin")
    if deno_bin not in env.get("PATH", ""):
        env["PATH"] = deno_bin + os.pathsep + env.get("PATH", "")
    return env

DOWNLOAD_ENV = _build_env()

# ── Optional external downloader (aria2c) ────────────────────────────────────────

def _find_aria2c() -> str | None:
    for path in ["/usr/local/bin/aria2c", "/usr/bin/aria2c", "/bin/aria2c"]:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None

ARIA2C_PATH = _find_aria2c()
ENABLE_ARIA2 = ARIA2C_PATH is not None
ARIA2_ARGS = "-x 16 -k 1M"

FRAGMENT_COUNT = 16  # Number of concurrent fragments for yt-dlp (stable improvement)

