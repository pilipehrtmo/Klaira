"""Penyimpanan klaim di SQLite."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SKEMA = """
CREATE TABLE IF NOT EXISTS klaim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_klaim TEXT UNIQUE,
    pasien_inisial TEXT NOT NULL,
    jenis_rawat TEXT NOT NULL,
    tgl_masuk TEXT,
    tgl_keluar TEXT,
    nilai_tarif INTEGER,
    resume TEXT NOT NULL,
    status TEXT NOT NULL,
    analisis TEXT,
    dianalisis_oleh TEXT,
    catatan_analisis TEXT,
    dibuat TEXT NOT NULL,
    diubah TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS riwayat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    klaim_id INTEGER NOT NULL REFERENCES klaim(id),
    aksi TEXT NOT NULL,
    catatan TEXT,
    waktu TEXT NOT NULL
);
"""


def sekarang() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DB:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("KLAIRA_DB", "data/klaira.db")
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SKEMA)

    @contextmanager
    def tx(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _baris(self, r: sqlite3.Row | None) -> dict | None:
        if r is None:
            return None
        d = dict(r)
        d["analisis"] = json.loads(d["analisis"]) if d["analisis"] else None
        return d

    def buat(self, data: dict, status: str, hasil: dict) -> dict:
        t = sekarang()
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO klaim (pasien_inisial, jenis_rawat, tgl_masuk, tgl_keluar, nilai_tarif, resume,
                   status, analisis, dianalisis_oleh, catatan_analisis, dibuat, diubah)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (data["pasien_inisial"], data["jenis_rawat"], data.get("tgl_masuk"), data.get("tgl_keluar"),
                 data.get("nilai_tarif"), data["resume"], status, json.dumps(hasil["analisis"]),
                 hasil["dianalisis_oleh"], hasil.get("catatan"), t, t),
            )
            kid = cur.lastrowid
            c.execute("UPDATE klaim SET no_klaim=? WHERE id=?", (f"KLM-{kid:05d}", kid))
            c.execute("INSERT INTO riwayat (klaim_id, aksi, catatan, waktu) VALUES (?,?,?,?)",
                      (kid, "dibuat", f"Dianalisis oleh {hasil['dianalisis_oleh']}", t))
        return self.ambil(kid)

    def ambil(self, kid: int) -> dict | None:
        return self._baris(self._conn.execute("SELECT * FROM klaim WHERE id=?", (kid,)).fetchone())

    def daftar(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self._conn.execute("SELECT * FROM klaim WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM klaim ORDER BY id DESC").fetchall()
        return [self._baris(r) for r in rows]

    def ubah(self, kid: int, fields: dict, aksi: str, catatan: str | None = None) -> dict | None:
        if not fields:
            return self.ambil(kid)
        fields = dict(fields)
        if "analisis" in fields and not isinstance(fields["analisis"], str):
            fields["analisis"] = json.dumps(fields["analisis"])
        fields["diubah"] = sekarang()
        cols = ", ".join(f"{k}=?" for k in fields)
        with self.tx() as c:
            c.execute(f"UPDATE klaim SET {cols} WHERE id=?", (*fields.values(), kid))
            c.execute("INSERT INTO riwayat (klaim_id, aksi, catatan, waktu) VALUES (?,?,?,?)",
                      (kid, aksi, catatan, fields["diubah"]))
        return self.ambil(kid)

    def riwayat(self, kid: int) -> list[dict]:
        rows = self._conn.execute("SELECT aksi, catatan, waktu FROM riwayat WHERE klaim_id=? ORDER BY id", (kid,)).fetchall()
        return [dict(r) for r in rows]

    def kosong(self) -> bool:
        return self._conn.execute("SELECT COUNT(*) FROM klaim").fetchone()[0] == 0
