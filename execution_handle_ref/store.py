from __future__ import annotations
import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
CREATE TABLE IF NOT EXISTS handle_state (
  handle_id TEXT PRIMARY KEY,
  uses INTEGER NOT NULL DEFAULT 0,
  used_digests TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS generations (
  name TEXT PRIMARY KEY,
  value INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS revoked (
  handle_id TEXT PRIMARY KEY,
  revoked INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS effects (
  candidate_act_id TEXT PRIMARY KEY,
  handle_id TEXT NOT NULL,
  act_digest TEXT NOT NULL,
  payload TEXT NOT NULL,
  committed_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
  receipt_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
"""

class StoreUnavailable(RuntimeError):
    pass

class SQLiteStore:
    """Crash-safe reference store.

    Consume state and the reference effect table share one SQLite transaction.  This gives the
    reference harness a real atomic boundary.  An external irreversible effect (wire transfer,
    actuator, packet release) needs an equivalent transactional/reservation/outbox integration;
    SQLite cannot make a remote side effect atomic by itself.
    """
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.available = True
        self._keeper = None
        if self.path == ":memory:":
            # Shared in-memory DB so multiple worker connections see the same state.
            self.path = f"file:ehref-{id(self)}?mode=memory&cache=shared"
            self._uri = True
            self._keeper = sqlite3.connect(self.path, uri=True, check_same_thread=False, isolation_level=None)
            self._keeper.executescript(SCHEMA)
        else:
            self._uri = False
            conn = self._connect(); conn.executescript(SCHEMA); conn.close()
        self._init_default_generations()

    def _connect(self):
        if not self.available:
            raise StoreUnavailable("consume state unavailable")
        c = sqlite3.connect(self.path, uri=getattr(self, "_uri", False), timeout=10, isolation_level=None, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=10000")
        return c

    def _init_default_generations(self):
        with self.atomic() as c:
            for name in ("policy", "revocation", "topology", "context"):
                c.execute("INSERT OR IGNORE INTO generations(name,value) VALUES (?,?)", (name, 1))

    @contextmanager
    def atomic(self) -> Iterator[sqlite3.Connection]:
        c = self._connect()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except Exception:
            try: c.execute("ROLLBACK")
            except Exception: pass
            raise
        finally:
            c.close()

    def generation_vector(self, c: sqlite3.Connection | None = None) -> dict[str, int]:
        if c is None:
            cx = self._connect()
            try: rows = cx.execute("SELECT name,value FROM generations").fetchall()
            finally: cx.close()
        else:
            rows = c.execute("SELECT name,value FROM generations").fetchall()
        return {r["name"]: int(r["value"]) for r in rows}

    def bump_generation(self, name: str) -> int:
        with self.atomic() as c:
            c.execute("UPDATE generations SET value=value+1 WHERE name=?", (name,))
            return int(c.execute("SELECT value FROM generations WHERE name=?", (name,)).fetchone()[0])

    def revoke(self, handle_id: str):
        with self.atomic() as c:
            c.execute("INSERT INTO revoked(handle_id,revoked) VALUES (?,1) ON CONFLICT(handle_id) DO UPDATE SET revoked=1", (handle_id,))
            c.execute("UPDATE generations SET value=value+1 WHERE name='revocation'")

    def is_revoked(self, handle_id: str, c: sqlite3.Connection) -> bool:
        row = c.execute("SELECT revoked FROM revoked WHERE handle_id=?", (handle_id,)).fetchone()
        return bool(row and row[0])

    def get_state(self, handle_id: str, c: sqlite3.Connection) -> tuple[int, set[str]]:
        row = c.execute("SELECT uses, used_digests FROM handle_state WHERE handle_id=?", (handle_id,)).fetchone()
        if not row:
            c.execute("INSERT INTO handle_state(handle_id,uses,used_digests) VALUES (?,0,'[]')", (handle_id,))
            return 0, set()
        return int(row["uses"]), set(json.loads(row["used_digests"]))

    def put_state(self, handle_id: str, uses: int, digests: set[str], c: sqlite3.Connection):
        c.execute("INSERT INTO handle_state(handle_id,uses,used_digests) VALUES (?,?,?) ON CONFLICT(handle_id) DO UPDATE SET uses=excluded.uses, used_digests=excluded.used_digests",
                  (handle_id, uses, json.dumps(sorted(digests))))

    def effect_count(self, handle_id: str | None = None) -> int:
        c = self._connect()
        try:
            if handle_id is None: return int(c.execute("SELECT count(*) FROM effects").fetchone()[0])
            return int(c.execute("SELECT count(*) FROM effects WHERE handle_id=?", (handle_id,)).fetchone()[0])
        finally: c.close()

    def close(self):
        if self._keeper is not None:
            self._keeper.close(); self._keeper = None
