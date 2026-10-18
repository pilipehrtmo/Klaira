"""Bentuk data Klaira: hasil analisis klaim dan input/output API."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Tingkat = Literal["kritis", "peringatan", "info"]
Risiko = Literal["rendah", "sedang", "tinggi"]
JenisRawat = Literal["rawat_inap", "rawat_jalan"]
StatusKlaim = Literal[
    "perlu_perbaikan",  # ada temuan kritis
    "siap_kirim",  # lolos pengecekan
    "terkirim",  # sudah dikirim ke BPJS
    "pending_bpjs",  # BPJS minta kelengkapan
    "cair",  # sudah dibayar
]


class KodeSaran(BaseModel):
    kode: str = Field(description="Kode ICD-10 (diagnosis) atau ICD-9-CM (prosedur)")
    deskripsi: str
    alasan: str = Field(description="Bukti di resume yang mendukung kode ini")


class Temuan(BaseModel):
    tingkat: Tingkat
    kategori: str = Field(description="Contoh: bukti penunjang, diagnosis sekunder, indikasi tindakan, identitas DPJP")
    pesan: str
    saran: str


class Analisis(BaseModel):
    """Hasil analisis satu resume medis. Dipakai juga sebagai skema output untuk Claude."""

    diagnosis_utama: Optional[KodeSaran]
    diagnosis_sekunder: list[KodeSaran]
    prosedur: list[KodeSaran]
    temuan: list[Temuan]
    skor_kelengkapan: int = Field(description="0 sampai 100")
    risiko_pending: Risiko
    ringkasan: str = Field(description="Satu atau dua kalimat untuk tim casemix")


class HasilAnalisis(BaseModel):
    analisis: Analisis
    dianalisis_oleh: Literal["ai", "aturan"]
    model: Optional[str] = None
    catatan: Optional[str] = None


class KlaimBaru(BaseModel):
    pasien_inisial: str = Field(min_length=1, max_length=40)
    jenis_rawat: JenisRawat
    tgl_masuk: Optional[str] = None
    tgl_keluar: Optional[str] = None
    nilai_tarif: Optional[int] = Field(default=None, ge=0)
    resume: str = Field(min_length=10)


class KlaimUbah(BaseModel):
    pasien_inisial: Optional[str] = Field(default=None, max_length=40)
    jenis_rawat: Optional[JenisRawat] = None
    tgl_masuk: Optional[str] = None
    tgl_keluar: Optional[str] = None
    nilai_tarif: Optional[int] = Field(default=None, ge=0)
    resume: Optional[str] = Field(default=None, min_length=10)


class UbahStatus(BaseModel):
    status: StatusKlaim
    catatan: Optional[str] = Field(default=None, max_length=500)


class CekCepat(BaseModel):
    resume: str = Field(min_length=10)
    jenis_rawat: JenisRawat = "rawat_inap"
