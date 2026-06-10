import sqlite3
from typing import List, Dict
from config import DB_FILE, STATUS_DONE, STATUS_ERROR, STATUS_CANCELLED

# ── Database ───────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent reads during writes
    conn.execute("PRAGMA synchronous=NORMAL") # faster writes, still safe
    conn.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            id            TEXT PRIMARY KEY,
            url           TEXT,
            folder        TEXT,
            quality       TEXT,
            embed_thumb   INTEGER,
            title         TEXT,
            playlist_id   TEXT,
            playlist_title TEXT,
            status        TEXT,
            progress      REAL,
            download_type TEXT DEFAULT 'audio',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        conn.execute("ALTER TABLE queue ADD COLUMN download_type TEXT DEFAULT 'audio'")
    except sqlite3.OperationalError:
        pass # column already exists
    conn.commit()
    conn.close()

class Database:
    """Thin SQLite helper.  Each call opens a short-lived connection so that the
    background download thread never blocks the main thread on a shared lock."""

    @staticmethod
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def get_all() -> List[Dict]:
        with Database._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM queue ORDER BY created_at ASC'
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def insert(item: Dict):
        with Database._connect() as conn:
            conn.execute('''
                INSERT INTO queue
                    (id, url, folder, quality, embed_thumb, title,
                     playlist_id, playlist_title, status, progress, download_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['id'], item['url'], item['folder'], item['quality'],
                int(item['embed_thumb']), item['title'],
                item.get('playlist_id'), item.get('playlist_title'),
                item['status'], item['progress'], item.get('download_type', 'audio')
            ))

    @staticmethod
    def insert_many(items: List[Dict]):
        """Bulk-insert in a single transaction — much faster for playlists."""
        with Database._connect() as conn:
            conn.executemany('''
                INSERT INTO queue
                    (id, url, folder, quality, embed_thumb, title,
                     playlist_id, playlist_title, status, progress, download_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                (
                    it['id'], it['url'], it['folder'], it['quality'],
                    int(it['embed_thumb']), it['title'],
                    it.get('playlist_id'), it.get('playlist_title'),
                    it['status'], it['progress'], it.get('download_type', 'audio')
                )
                for it in items
            ])

    @staticmethod
    def update_status(id: str, status: str, progress: float = None):
        with Database._connect() as conn:
            if progress is not None:
                conn.execute(
                    'UPDATE queue SET status=?, progress=? WHERE id=?',
                    (status, progress, id)
                )
            else:
                conn.execute(
                    'UPDATE queue SET status=? WHERE id=?',
                    (status, id)
                )

    @staticmethod
    def update_title(id: str, title: str):
        with Database._connect() as conn:
            conn.execute(
                'UPDATE queue SET title=? WHERE id=?',
                (title, id)
            )

    @staticmethod
    def delete(id: str):
        with Database._connect() as conn:
            conn.execute('DELETE FROM queue WHERE id=?', (id,))

    @staticmethod
    def clear_done():
        with Database._connect() as conn:
            conn.execute(
                'DELETE FROM queue WHERE status IN (?, ?, ?)',
                (STATUS_DONE, STATUS_ERROR, STATUS_CANCELLED)
            )
