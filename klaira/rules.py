"""Mesin aturan sederhana. Dipakai saat AI tidak tersedia, dan untuk menyamarkan data pribadi.

Daftar kata kunci di sini sengaja kecil. Versi produksi perlu kamus ICD-10 lengkap
dan aturan dari koder berpengalaman.
"""
import re

from .schemas import Analisis, KodeSaran, Temuan

# (pola, kode ICD-10, deskripsi)
DIAGNOSIS = [
    (r"demam berdarah|\bdbd\b|dengue", "A91", "Demam berdarah dengue"),
    (r"demam tifoid|tifoid|typhoid", "A01.0", "Demam tifoid"),
    (r"gastroenteritis|diare", "A09", "Diare dan gastroenteritis"),
    (r"tuberkulosis|\btb paru\b|\bkp\b", "A15.0", "Tuberkulosis paru, terkonfirmasi"),
    (r"pneumonia", "J18.9", "Pneumonia, tidak spesifik"),
    (r"asma|asthma", "J45.9", "Asma, tidak spesifik"),
    (r"\bppok\b|\bcopd\b", "J44.9", "PPOK, tidak spesifik"),
    (r"diabetes|\bdm tipe 2\b|\bdm2\b", "E11.9", "DM tipe 2 tanpa komplikasi"),
    (r"hipertensi", "I10", "Hipertensi esensial (primer)"),
    (r"gagal jantung|\bchf\b", "I50.9", "Gagal jantung, tidak spesifik"),
    (r"stroke|infark serebr", "I63.9", "Infark serebral, tidak spesifik"),
    (r"ginjal kronik|\bckd\b|gagal ginjal", "N18.9", "Penyakit ginjal kronik, tidak spesifik"),
    (r"infeksi saluran kemih|\bisk\b", "N39.0", "Infeksi saluran kemih"),
    (r"apendisitis|appendicitis", "K35.8", "Apendisitis akut"),
    (r"anemia", "D64.9", "Anemia, tidak spesifik"),
    (r"sectio|caesar|\bsc\b", "O82", "Persalinan tunggal dengan sectio caesarea"),
]

# (pola, kode ICD-9-CM, deskripsi)
PROSEDUR = [
    (r"sectio|caesar|\bsc\b", "74.1", "Sectio caesarea segmen bawah"),
    (r"hemodialisis|\bhd\b", "39.95", "Hemodialisis"),
    (r"apendektomi|appendectomy", "47.09", "Apendektomi"),
    (r"transfusi", "99.04", "Transfusi packed red cells"),
]

# Diagnosis sekunder yang sering dihapus verifikator bila tidak didukung bukti.
BUKTI_DIAGNOSIS = {
    "E11.9": (r"gula darah|\bgds\b|\bgdp\b|hba1c|insulin|metformin|glimepirid|\boad\b", "hasil gula darah atau terapi diabetes"),
    "D64.9": (r"\bhb\b|hemoglobin|transfusi", "hasil Hb atau terapi anemia"),
    "N18.9": (r"ureum|kreatinin|\begfr\b|hemodialisis|\bhd\b", "hasil ureum/kreatinin"),
    "I63.9": (r"ct scan|ct-scan|\bmri\b", "hasil CT scan atau MRI kepala"),
    "J18.9": (r"thorax|toraks|rontgen|\bro\b", "hasil foto toraks"),
    "A91": (r"trombosit|hematokrit|\bns1\b|igg|igm", "hasil trombosit/hematokrit atau serologi dengue"),
}

RE_NIK = re.compile(r"\b\d{16}\b")
RE_BPJS = re.compile(r"\b\d{13}\b")
RE_TELP = re.compile(r"(\+62|\b0)8\d{7,11}\b")


def samarkan(teks: str) -> str:
    """Ganti NIK, nomor kartu BPJS dan nomor HP sebelum teks dikirim ke layanan AI."""
    teks = RE_NIK.sub("[NIK]", teks)
    teks = RE_BPJS.sub("[NO-BPJS]", teks)
    return RE_TELP.sub("[TELP]", teks)


def _cocok(pola: str, teks: str) -> bool:
    return re.search(pola, teks, re.IGNORECASE) is not None


def _ambil_diagnosis_utama(teks: str) -> str:
    m = re.search(r"diagnosis utama\s*:?\s*(.+)", teks, re.IGNORECASE)
    return m.group(1) if m else ""


def analisis_aturan(resume: str, jenis_rawat: str = "rawat_inap") -> Analisis:
    utama_teks = _ambil_diagnosis_utama(resume)
    diagnosis = [(k, d) for p, k, d in DIAGNOSIS if _cocok(p, resume)]
    # Diagnosis utama: yang tertulis di baris "Diagnosis utama", kalau tidak ada pakai temuan pertama.
    utama = next(((k, d) for p, k, d in DIAGNOSIS if utama_teks and _cocok(p, utama_teks)), None)
    if utama is None and diagnosis:
        utama = diagnosis[0]
    sekunder = [x for x in diagnosis if x != utama]
    prosedur = [(k, d) for p, k, d in PROSEDUR if _cocok(p, resume)]

    temuan: list[Temuan] = []

    def tambah(tingkat, kategori, pesan, saran):
        temuan.append(Temuan(tingkat=tingkat, kategori=kategori, pesan=pesan, saran=saran))

    if not _cocok(r"\bdpjp\b|\bdr\.", resume):
        tambah("kritis", "identitas DPJP", "Nama DPJP tidak ditemukan di resume.", "Tambahkan nama dan tanda tangan elektronik DPJP.")
    if jenis_rawat == "rawat_inap" and not (_cocok(r"masuk", resume) and _cocok(r"keluar|pulang", resume)):
        tambah("kritis", "tanggal perawatan", "Tanggal masuk atau keluar tidak ditemukan.", "Lengkapi tanggal masuk dan tanggal pulang.")
    if not utama_teks:
        tambah("peringatan", "diagnosis utama", "Diagnosis utama tidak ditandai dengan jelas.", 'Tulis baris "Diagnosis utama:" di resume.')
    if utama is None:
        tambah("peringatan", "koding", "Belum ada diagnosis yang dikenali mesin aturan.", "Periksa manual oleh koder, atau aktifkan analisis AI.")

    for kode, desk in [x for x in [utama] if x] + sekunder:
        bukti = BUKTI_DIAGNOSIS.get(kode)
        if bukti and not _cocok(bukti[0], resume):
            peran = "Diagnosis utama" if (kode, desk) == utama else "Diagnosis sekunder"
            tingkat = "peringatan" if peran == "Diagnosis utama" else "kritis"
            tambah(tingkat, "bukti penunjang", f"{peran} {kode} ({desk}) belum didukung {bukti[1]}.",
                   f"Lampirkan {bukti[1]}, atau hapus diagnosis bila tidak terbukti.")

    if _cocok(r"sectio|caesar|\bsc\b", resume) and not _cocok(r"indikasi", resume):
        tambah("kritis", "indikasi tindakan", "Indikasi medis sectio caesarea tidak tertulis.", "Minta DPJP menuliskan indikasi SC.")
    if prosedur and not _cocok(r"laporan operasi|lapor(an)? tindakan|operasi", resume) and any(k in ("74.1", "47.09") for k, _ in prosedur):
        tambah("peringatan", "laporan operasi", "Laporan operasi tidak disebut di resume.", "Pastikan laporan operasi terlampir di RME.")

    kritis = sum(t.tingkat == "kritis" for t in temuan)
    peringatan = sum(t.tingkat == "peringatan" for t in temuan)
    skor = max(0, 100 - 25 * kritis - 10 * peringatan)
    risiko = "tinggi" if kritis else ("sedang" if peringatan else "rendah")
    ringkasan = (
        f"{kritis} temuan kritis dan {peringatan} peringatan. Perbaiki sebelum dikirim ke BPJS."
        if temuan else "Tidak ada temuan. Klaim siap dikirim."
    )

    def ks(k, d, alasan="Kata kunci ditemukan di resume"):
        return KodeSaran(kode=k, deskripsi=d, alasan=alasan)

    return Analisis(
        diagnosis_utama=ks(*utama) if utama else None,
        diagnosis_sekunder=[ks(k, d) for k, d in sekunder],
        prosedur=[ks(k, d) for k, d in prosedur],
        temuan=temuan,
        skor_kelengkapan=skor,
        risiko_pending=risiko,
        ringkasan=ringkasan,
    )
