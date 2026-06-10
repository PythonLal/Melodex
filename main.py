import os
import sqlite3
import webview
from config import DB_FILE, STATUS_WAITING, STATUS_DOWNLOADING, STATUS_PAUSED
from downloader import DownloaderAPI

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    api = DownloaderAPI()

    # Reset any items that were stuck in mid-download when the app last closed
    with sqlite3.connect(DB_FILE) as _conn:
        _conn.execute(
            f"UPDATE queue SET status='{STATUS_WAITING}' "
            f"WHERE status IN ('{STATUS_DOWNLOADING}', '{STATUS_PAUSED}')"
        )

    ui_dir = os.path.join(os.path.dirname(__file__), 'ui')
    os.makedirs(ui_dir, exist_ok=True)

    webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False

    window = webview.create_window(
        'Melodex',
        'ui/index.html',
        js_api=api,
        width=1000,
        height=800,
        min_size=(800, 600),
        background_color='#0a0a14',
    )
    api.set_window(window)
    webview.start(debug=False)
