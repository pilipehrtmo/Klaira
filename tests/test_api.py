from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from klaira.analyzer import Analyzer
from klaira.db import DB
from klaira.main import create_app
from klaira.schemas import Analisis, KodeSaran

RESUME = """Diagnosis utama: pneumonia. Diagnosis sekunder: diabetes melitus tipe 2.
Foto thorax: infiltrat. Masuk 07/10/2026, pulang 12/10/2026. DPJP: dr. Hendra"""


@pytest.fixture
def client():
    return TestClient(create_app(DB(":memory:"), Analyzer(client=None)))


def test_demo_terisi_dan_statistik(client):
    rows = client.get("/api/claims").json()
    assert len(rows) == 6
    s = client.get("/api/stats").json()
    assert s["total"] == 6
    assert s["per_status"]["cair"] == 1 and s["per_status"]["pending_bpjs"] == 1
    assert s["nilai_tertahan"] > 0
    assert client.get("/api/health").json()["ai_aktif"] is False


def test_alur_klaim(client):
    r = client.post("/api/claims", json={"pasien_inisial": "Tn. X", "jenis_rawat": "rawat_inap", "nilai_tarif": 6000000, "resume": RESUME})
    assert r.status_code == 201
    k = r.json()
    assert k["no_klaim"].startswith("KLM-")
    assert k["status"] == "perlu_perbaikan"
    assert k["dianalisis_oleh"] == "aturan"

    # Perbaiki resume: tambah GDS, status otomatis jadi siap kirim
    k = client.put(f"/api/claims/{k['id']}", json={"resume": RESUME + "\nGDS 260, terapi metformin."}).json()
    assert k["status"] == "siap_kirim"

    k = client.post(f"/api/claims/{k['id']}/status", json={"status": "terkirim"}).json()
    assert k["status"] == "terkirim"
    # Analisis ulang tidak mengubah status yang diatur manual
    k = client.post(f"/api/claims/{k['id']}/analyze").json()
    assert k["status"] == "terkirim"

    detail = client.get(f"/api/claims/{k['id']}").json()
    assert [r["aksi"] for r in detail["riwayat"]] == ["dibuat", "diubah", "status", "dianalisis"]


def test_validasi_dan_404(client):
    assert client.post("/api/claims", json={"pasien_inisial": "", "jenis_rawat": "rawat_inap", "resume": "x"}).status_code == 422
    assert client.get("/api/claims/999").status_code == 404
    assert client.post("/api/claims/1/status", json={"status": "hilang"}).status_code == 422


def test_filter_dan_ekspor(client):
    rows = client.get("/api/claims?status=cair").json()
    assert len(rows) == 1 and rows[0]["status"] == "cair"
    csv = client.get("/api/claims/export.csv")
    assert csv.status_code == 200
    assert csv.text.splitlines()[0].startswith("no_klaim,")
    assert len(csv.text.strip().splitlines()) == 7


def test_halaman_web(client):
    assert "klaira" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


# ----- Jalur AI dengan klien palsu (tanpa memanggil API sungguhan) -----

class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_client(response):
    msgs = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


def contoh_analisis(skor=120):
    return Analisis(
        diagnosis_utama=KodeSaran(kode="J18.9", deskripsi="Pneumonia", alasan="Diagnosis utama: pneumonia"),
        diagnosis_sekunder=[], prosedur=[], temuan=[], skor_kelengkapan=skor,
        risiko_pending="rendah", ringkasan="Siap kirim.",
    )


def test_ai_dipakai_dan_data_pribadi_disamarkan():
    resp = SimpleNamespace(stop_reason="end_turn", parsed_output=contoh_analisis(), model="claude-opus-5-5")
    fc, msgs = fake_client(resp)
    hasil = Analyzer(client=fc).analisis("Pasien NIK 3174012345678901. " + RESUME)
    assert hasil.dianalisis_oleh == "ai"
    assert hasil.analisis.skor_kelengkapan == 100  # dipotong ke 0-100
    kirim = msgs.calls[0]
    assert "3174012345678901" not in kirim["messages"][0]["content"]
    assert kirim["model"] == "claude-opus-5-5"
    assert kirim["fallbacks"] == "default"
    assert kirim["output_format"] is Analisis


def test_ai_menolak_jatuh_ke_aturan():
    fc, _ = fake_client(SimpleNamespace(stop_reason="refusal", parsed_output=None, model="claude-opus-5-5"))
    hasil = Analyzer(client=fc).analisis(RESUME)
    assert hasil.dianalisis_oleh == "aturan"
    assert "menolak" in hasil.catatan
