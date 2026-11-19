from klaira.rules import analisis_aturan, samarkan

DBD = """Diagnosis utama: demam berdarah dengue.
Hasil lab: trombosit 48.000, hematokrit 46%.
Masuk 05/10/2026, pulang 09/10/2026.
DPJP: dr. Hendra"""


def kode_semua(a):
    return [a.diagnosis_utama.kode] + [x.kode for x in a.diagnosis_sekunder + a.prosedur]


def test_dbd_lengkap_siap_kirim():
    a = analisis_aturan(DBD)
    assert a.diagnosis_utama.kode == "A91"
    assert not [t for t in a.temuan if t.tingkat == "kritis"]
    assert a.risiko_pending == "rendah"
    assert a.skor_kelengkapan == 100


def test_diabetes_sekunder_tanpa_bukti_kritis():
    a = analisis_aturan(DBD + "\nDiagnosis sekunder: diabetes melitus tipe 2.")
    assert "E11.9" in kode_semua(a)
    assert any(t.tingkat == "kritis" and "E11.9" in t.pesan for t in a.temuan)
    assert a.risiko_pending == "tinggi"


def test_diabetes_dengan_gds_tidak_kritis():
    a = analisis_aturan(DBD + "\nDiagnosis sekunder: diabetes melitus tipe 2. GDS 280, terapi metformin.")
    assert not any(t.tingkat == "kritis" for t in a.temuan)


def test_sc_tanpa_indikasi():
    a = analisis_aturan("Diagnosis utama: persalinan sectio caesarea. Laporan operasi terlampir. Masuk 1/10, pulang 3/10. DPJP: dr. Maya")
    assert a.diagnosis_utama.kode == "O82"
    assert "74.1" in kode_semua(a)
    assert any(t.kategori == "indikasi tindakan" for t in a.temuan)


def test_tanpa_dpjp_dan_tanggal():
    a = analisis_aturan("Diagnosis utama: hipertensi esensial. Terapi amlodipin.")
    kategori = {t.kategori for t in a.temuan if t.tingkat == "kritis"}
    assert {"identitas DPJP", "tanggal perawatan"} <= kategori


def test_rawat_jalan_tidak_butuh_tanggal():
    a = analisis_aturan("Diagnosis utama: hipertensi esensial. TD 150/95. DPJP: dr. Rina", "rawat_jalan")
    assert not any(t.kategori == "tanggal perawatan" for t in a.temuan)


def test_samarkan_data_pribadi():
    teks = samarkan("NIK 3174012345678901, kartu 0001234567890, HP 081234567890")
    assert "3174012345678901" not in teks and "[NIK]" in teks
    assert "0001234567890" not in teks and "[NO-BPJS]" in teks
    assert "081234567890" not in teks and "[TELP]" in teks
