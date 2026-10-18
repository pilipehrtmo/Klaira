"""Server web Klaira. Jalankan: uvicorn klaira.main:app --reload"""
import csv
import io
import os
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import demo
from .analyzer import Analyzer
from .db import DB
from .rules import analisis_aturan
from .schemas import CekCepat, KlaimBaru, KlaimUbah, UbahStatus

STATIC = Path(__file__).parent / "static"
# Status yang ditentukan otomatis oleh hasil analisis. Status lain diatur manual oleh tim casemix.
STATUS_OTOMATIS = {"perlu_perbaikan", "siap_kirim"}


def status_dari(analisis: dict) -> str:
    return "perlu_perbaikan" if any(t["tingkat"] == "kritis" for t in analisis["temuan"]) else "siap_kirim"


def create_app(db: DB | None = None, analyzer: Analyzer | None = None) -> FastAPI:
    db = db or DB()
    analyzer = analyzer or Analyzer()
    app = FastAPI(title="Klaira", version="0.1.0")

    if os.getenv("KLAIRA_SEED_DEMO", "1") == "1" and db.kosong():
        for data in demo.CONTOH:
            a = analisis_aturan(data["resume"], data["jenis_rawat"]).model_dump()
            k = db.buat(data, status_dari(a), {"analisis": a, "dianalisis_oleh": "aturan", "catatan": "Data contoh"})
            if data["pasien_inisial"] in demo.STATUS_LANJUT:
                st, cat = demo.STATUS_LANJUT[data["pasien_inisial"]]
                db.ubah(k["id"], {"status": st}, "status", cat)

    def jalankan_analisis(resume: str, jenis_rawat: str) -> dict:
        return analyzer.analisis(resume, jenis_rawat).model_dump()

    def wajib_ada(kid: int) -> dict:
        k = db.ambil(kid)
        if k is None:
            raise HTTPException(404, "Klaim tidak ditemukan")
        return k

    @app.get("/api/health")
    def health():
        return {"ok": True, "ai_aktif": analyzer.ai_aktif, "model": analyzer.model if analyzer.ai_aktif else None}

    @app.get("/api/claims")
    def daftar(status: str | None = Query(default=None)):
        return db.daftar(status)

    @app.post("/api/claims", status_code=201)
    def buat(body: KlaimBaru):
        hasil = jalankan_analisis(body.resume, body.jenis_rawat)
        return db.buat(body.model_dump(), status_dari(hasil["analisis"]), hasil)

    @app.get("/api/claims/export.csv")
    def ekspor():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["no_klaim", "pasien", "jenis_rawat", "status", "nilai_tarif", "diagnosis_utama", "kode_lain", "skor", "risiko", "temuan_kritis"])
        for k in db.daftar():
            a = k["analisis"] or {}
            du = (a.get("diagnosis_utama") or {}).get("kode", "")
            lain = " ".join(x["kode"] for x in a.get("diagnosis_sekunder", []) + a.get("prosedur", []))
            kritis = sum(t["tingkat"] == "kritis" for t in a.get("temuan", []))
            w.writerow([k["no_klaim"], k["pasien_inisial"], k["jenis_rawat"], k["status"], k["nilai_tarif"] or "",
                        du, lain, a.get("skor_kelengkapan", ""), a.get("risiko_pending", ""), kritis])
        buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=klaira-klaim.csv"})

    @app.get("/api/claims/{kid}")
    def ambil(kid: int):
        k = wajib_ada(kid)
        k["riwayat"] = db.riwayat(kid)
        return k

    @app.put("/api/claims/{kid}")
    def ubah(kid: int, body: KlaimUbah):
        k = wajib_ada(kid)
        fields = body.model_dump(exclude_none=True)
        if "resume" in fields or "jenis_rawat" in fields:
            hasil = jalankan_analisis(fields.get("resume", k["resume"]), fields.get("jenis_rawat", k["jenis_rawat"]))
            fields.update(analisis=hasil["analisis"], dianalisis_oleh=hasil["dianalisis_oleh"], catatan_analisis=hasil.get("catatan"))
            if k["status"] in STATUS_OTOMATIS:
                fields["status"] = status_dari(hasil["analisis"])
        return db.ubah(kid, fields, "diubah", "Resume diperbarui dan dianalisis ulang" if "analisis" in fields else None)

    @app.post("/api/claims/{kid}/analyze")
    def analisis_ulang(kid: int):
        k = wajib_ada(kid)
        hasil = jalankan_analisis(k["resume"], k["jenis_rawat"])
        fields = dict(analisis=hasil["analisis"], dianalisis_oleh=hasil["dianalisis_oleh"], catatan_analisis=hasil.get("catatan"))
        if k["status"] in STATUS_OTOMATIS:
            fields["status"] = status_dari(hasil["analisis"])
        return db.ubah(kid, fields, "dianalisis", f"Dianalisis ulang oleh {hasil['dianalisis_oleh']}")

    @app.post("/api/claims/{kid}/status")
    def ubah_status(kid: int, body: UbahStatus):
        wajib_ada(kid)
        return db.ubah(kid, {"status": body.status}, "status", body.catatan)

    @app.post("/api/analyze")
    def cek_cepat(body: CekCepat):
        return jalankan_analisis(body.resume, body.jenis_rawat)

    @app.get("/api/stats")
    def statistik():
        semua = db.daftar()
        per_status = Counter(k["status"] for k in semua)
        tertahan = sum(k["nilai_tarif"] or 0 for k in semua if k["status"] in ("perlu_perbaikan", "pending_bpjs"))
        skor = [k["analisis"]["skor_kelengkapan"] for k in semua if k["analisis"]]
        kategori = Counter(t["kategori"] for k in semua if k["status"] == "perlu_perbaikan"
                           for t in (k["analisis"] or {}).get("temuan", []) if t["tingkat"] == "kritis")
        dikirim = per_status["terkirim"] + per_status["pending_bpjs"] + per_status["cair"]
        return {
            "total": len(semua),
            "per_status": dict(per_status),
            "nilai_tertahan": tertahan,
            "rata_skor": round(sum(skor) / len(skor)) if skor else None,
            "pending_rate": round(100 * per_status["pending_bpjs"] / dikirim, 1) if dikirim else None,
            "penyebab_teratas": kategori.most_common(5),
        }

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    return app


app = create_app() if os.getenv("KLAIRA_NO_AUTOAPP") != "1" else None
