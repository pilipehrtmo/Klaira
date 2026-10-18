"""Analisis resume medis dengan Claude, dengan mesin aturan sebagai cadangan."""
import logging
import os

import anthropic

from .rules import analisis_aturan, samarkan
from .schemas import Analisis, HasilAnalisis

log = logging.getLogger("klaira.analyzer")

SYSTEM_PROMPT = """Kamu adalah auditor koding klinis untuk klaim JKN (BPJS Kesehatan) di rumah sakit dan klinik Indonesia.
Tugasmu membantu tim casemix sebelum klaim dikirim: menyarankan kode dan menemukan kekurangan dokumentasi yang sering membuat klaim pending atau dispute.

Aturan koding:
- Diagnosis memakai ICD-10 (versi WHO 2010 yang dipakai di INA-CBG). Prosedur memakai ICD-9-CM.
- Diagnosis utama adalah kondisi yang menjadi alasan utama perawatan, sesuai yang ditegakkan DPJP di akhir episode.
- Diagnosis sekunder hanya dicantumkan bila didukung bukti di resume: hasil pemeriksaan penunjang, terapi, atau tindakan.
- Jangan mengarang fakta yang tidak tertulis di resume. Bila resume tidak cukup jelas, katakan di temuan, jangan menebak kode yang lebih spesifik.
- Untuk setiap kode, tulis di "alasan" bagian resume yang mendukungnya.

Periksa kelengkapan, terutama:
- Nama DPJP dan tanda tangan, tanggal masuk dan keluar (rawat inap), diagnosis utama yang jelas.
- Bukti penunjang untuk setiap diagnosis (lab, radiologi, terapi).
- Indikasi medis untuk setiap tindakan atau operasi, dan laporan operasinya.
- Ketidaksesuaian, misalnya lama rawat yang tidak wajar untuk diagnosisnya, atau terapi yang tidak cocok dengan diagnosis.

Tingkat temuan: "kritis" bila hampir pasti membuat klaim pending atau ditolak, "peringatan" bila berisiko, "info" untuk catatan kecil.
skor_kelengkapan 0-100 (100 = siap kirim). risiko_pending: rendah, sedang, atau tinggi.
Tulis semua teks dalam bahasa Indonesia yang singkat dan jelas untuk koder. Hasilmu adalah saran; keputusan akhir ada di koder dan DPJP."""


def _rapikan(a: Analisis) -> Analisis:
    a.skor_kelengkapan = max(0, min(100, a.skor_kelengkapan))
    return a


class Analyzer:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str | None = None, effort: str | None = None):
        self.model = model or os.getenv("KLAIRA_MODEL", "claude-opus-5-5")
        self.effort = effort or os.getenv("KLAIRA_EFFORT", "medium")
        if client is not None:
            self.client = client
        elif os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"):
            self.client = anthropic.Anthropic()
        else:
            self.client = None

    @property
    def ai_aktif(self) -> bool:
        return self.client is not None

    def analisis(self, resume: str, jenis_rawat: str = "rawat_inap") -> HasilAnalisis:
        if not self.ai_aktif:
            return HasilAnalisis(analisis=analisis_aturan(resume, jenis_rawat), dianalisis_oleh="aturan",
                                 catatan="AI belum aktif. Isi ANTHROPIC_API_KEY untuk analisis AI.")
        try:
            return self._analisis_ai(resume, jenis_rawat)
        except anthropic.AuthenticationError:
            catatan = "Kunci API Claude tidak valid. Memakai mesin aturan."
        except anthropic.RateLimitError:
            catatan = "Batas pemakaian AI tercapai. Memakai mesin aturan, coba analisis ulang nanti."
        except anthropic.APIStatusError as e:
            log.warning("API error %s: %s", e.status_code, e.message)
            catatan = f"Layanan AI mengembalikan error {e.status_code}. Memakai mesin aturan."
        except anthropic.APIConnectionError:
            catatan = "Tidak bisa terhubung ke layanan AI. Memakai mesin aturan."
        except _AIGagal as e:
            catatan = str(e)
        return HasilAnalisis(analisis=analisis_aturan(resume, jenis_rawat), dianalisis_oleh="aturan", catatan=catatan)

    def _analisis_ai(self, resume: str, jenis_rawat: str) -> HasilAnalisis:
        jenis = "Rawat inap" if jenis_rawat == "rawat_inap" else "Rawat jalan"
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": self.effort},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Jenis layanan: {jenis}\n\n<resume_medis>\n{samarkan(resume)}\n</resume_medis>",
            }],
            output_format=Analisis,
        )
        if response.stop_reason == "refusal":
            raise _AIGagal("AI menolak menganalisis resume ini. Memakai mesin aturan.")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise _AIGagal("Jawaban AI tidak lengkap. Memakai mesin aturan.")
        return HasilAnalisis(analisis=_rapikan(response.parsed_output), dianalisis_oleh="ai", model=response.model)


class _AIGagal(Exception):
    pass
