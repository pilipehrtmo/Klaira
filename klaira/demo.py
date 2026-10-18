"""Data contoh (fiktif) untuk demo. Tidak ada pasien sungguhan di sini."""

CONTOH = [
    dict(pasien_inisial="Tn. A.S.", jenis_rawat="rawat_inap", tgl_masuk="2026-10-05", tgl_keluar="2026-10-09", nilai_tarif=4850000,
         resume="""Keluhan: demam 4 hari, nyeri ulu hati, petekie di lengan.
Diagnosis utama: demam berdarah dengue.
Hasil lab: trombosit 48.000, hematokrit 46%. NS1 positif.
Terapi: infus RL, paracetamol. Masuk 05/10/2026, pulang 09/10/2026 dalam kondisi baik.
DPJP: dr. Hendra, Sp.PD"""),
    dict(pasien_inisial="Ny. R.W.", jenis_rawat="rawat_inap", tgl_masuk="2026-10-06", tgl_keluar="2026-10-09", nilai_tarif=7200000,
         resume="""Pasien G2P1A0 hamil 39 minggu.
Diagnosis utama: persalinan dengan sectio caesarea.
Tindakan: SC, laporan operasi terlampir. Bayi lahir hidup 3.100 g.
Masuk 06/10/2026, pulang 09/10/2026.
DPJP: dr. Maya, Sp.OG"""),
    dict(pasien_inisial="Tn. B.H.", jenis_rawat="rawat_inap", tgl_masuk="2026-10-07", tgl_keluar="2026-10-12", nilai_tarif=6100000,
         resume="""Keluhan: batuk berdahak dan sesak 5 hari, demam.
Diagnosis utama: pneumonia. Diagnosis sekunder: diabetes melitus tipe 2.
Foto thorax: infiltrat lobus kanan bawah. Terapi: ceftriaxone, nebulisasi.
Masuk 07/10/2026, pulang 12/10/2026.
DPJP: dr. Hendra, Sp.PD"""),
    dict(pasien_inisial="Ny. S.L.", jenis_rawat="rawat_jalan", nilai_tarif=215000,
         resume="""Kontrol rutin. TD 150/95 mmHg.
Diagnosis utama: hipertensi esensial.
Terapi: amlodipin 10 mg. Kontrol 1 bulan.
DPJP: dr. Rina"""),
    dict(pasien_inisial="Tn. D.P.", jenis_rawat="rawat_inap", tgl_masuk="2026-10-08", tgl_keluar="2026-10-15", nilai_tarif=9750000,
         resume="""Kelemahan anggota gerak kiri mendadak, bicara pelo.
Diagnosis utama: stroke infark. Diagnosis sekunder: hipertensi.
Terapi: citicoline, aspirin, amlodipin. Fisioterapi.
Masuk 08/10/2026, pulang 15/10/2026.
DPJP: dr. Bayu, Sp.N"""),
    dict(pasien_inisial="Tn. H.K.", jenis_rawat="rawat_jalan", nilai_tarif=1050000,
         resume="""Jadwal hemodialisis rutin 2x seminggu.
Diagnosis utama: penyakit ginjal kronik stadium 5.
Tindakan: hemodialisis 4 jam. Ureum 180, kreatinin 9,2.
DPJP: dr. Sari, Sp.PD-KGH"""),
]

# Status tambahan setelah analisis, supaya dashboard demo terlihat seperti RS sungguhan.
STATUS_LANJUT = {"Tn. H.K.": ("pending_bpjs", "BPJS meminta hasil lab terbaru"),
                 "Ny. S.L.": ("cair", "Dibayar BPJS")}
