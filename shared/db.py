import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

from shared.logging import get_logger
from shared.settings import settings

log = get_logger("db")

_local = threading.local()
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
_DB_PATH: Optional[str] = None


def configure(path: Optional[str] = None) -> None:
    global _DB_PATH
    _DB_PATH = path or os.path.join(settings.data_dir, "vilaw.db")


def _get_db() -> sqlite3.Connection:
    path = _DB_PATH or os.path.join(settings.data_dir, "vilaw.db")
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Get a thread-local connection (caller manages commit/rollback)."""
    yield _get_db()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Context manager that commits on success, rolls back on error."""
    conn = _get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def migrate() -> None:
    """Run all .sql files in MIGRATIONS_DIR in order."""
    conn = _get_db()
    cursor = conn.execute("PRAGMA user_version")
    current_version = cursor.fetchone()[0] or 0

    if not os.path.isdir(MIGRATIONS_DIR):
        log.info("no_migrations_dir", path=MIGRATIONS_DIR)
        return

    sql_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    for i, fname in enumerate(sql_files, start=1):
        if i <= current_version:
            continue
        path = os.path.join(MIGRATIONS_DIR, fname)
        log.info("running_migration", file=fname)
        sql = open(path, encoding="utf-8").read()
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version={i}")
        conn.commit()
        log.info("migration_done", file=fname)


# ── Document store ──

def upsert_document(doc: dict) -> None:
    with transaction() as conn:
        conn.execute(
            """INSERT INTO documents (id, chu_de, de_muc, so_dieu, tieu_de_dieu, noi_dung, nguon, path_goc, updated_at)
               VALUES (:id, :chu_de, :de_muc, :so_dieu, :tieu_de_dieu, :noi_dung, :nguon, :path_goc, datetime('now'))
               ON CONFLICT(id) DO UPDATE SET
                   chu_de=excluded.chu_de, de_muc=excluded.de_muc,
                   so_dieu=excluded.so_dieu, tieu_de_dieu=excluded.tieu_de_dieu,
                   noi_dung=excluded.noi_dung, updated_at=datetime('now')""",
            doc,
        )


def get_chunks_by_doc_id(doc_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, doc_id, chunk_index, text, faiss_id, chunk_hash FROM chunks WHERE doc_id=? ORDER BY chunk_index",
            (doc_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_chunks() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, doc_id, chunk_index, text, faiss_id, chunk_hash FROM chunks ORDER BY doc_id, chunk_index"
        ).fetchall()
        return [dict(r) for r in rows]


def insert_chunks(chunks: list[dict]) -> None:
    with transaction() as conn:
        conn.executemany(
            """INSERT INTO chunks (doc_id, chunk_index, text, chunk_hash)
               VALUES (:doc_id, :chunk_index, :text, :chunk_hash)""",
            chunks,
        )


def update_faiss_id(chunk_db_id: int, faiss_id: int) -> None:
    with transaction() as conn:
        conn.execute("UPDATE chunks SET faiss_id=? WHERE id=?", (faiss_id, chunk_db_id))


def delete_chunks_by_doc_id(doc_id: str) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))


def get_all_document_ids() -> list[str]:
    with get_conn() as conn:
        return [r[0] for r in conn.execute("SELECT id FROM documents").fetchall()]


# ── Conversation store ──

def get_all_conversations() -> list[dict]:
    with get_conn() as conn:
        convs = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        result = []
        for c in convs:
            d = dict(c)
            msgs = conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at",
                (d["id"],),
            ).fetchall()
            d["messages"] = [
                {
                    **dict(m),
                    "citations": json.loads(m["citations"]) if m.get("citations") else [],
                }
                for m in msgs
            ]
            result.append(d)
        return result


def save_conversations(convs: list[dict]) -> None:
    with transaction() as conn:
        for c in convs:
            conn.execute(
                """INSERT OR REPLACE INTO conversations (id, title, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (c["id"], c.get("title", "New chat"), c.get("createdAt", 0), c.get("updatedAt", 0)),
            )
            conn.execute("DELETE FROM messages WHERE conversation_id=?", (c["id"],))
            for m in c.get("messages", []):
                conn.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, citations, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        m["id"],
                        c["id"],
                        m["role"],
                        m["content"],
                        json.dumps(m.get("citations", []), ensure_ascii=False),
                        m.get("createdAt", 0),
                    ),
                )
