// Klaira web app: tampilan satu halaman tanpa framework.
const view = document.getElementById("view");

const STATUS = {
  perlu_perbaikan: "Perlu perbaikan",
  siap_kirim: "Siap kirim",
  terkirim: "Terkirim",
  pending_bpjs: "Pending BPJS",
  cair: "Cair",
};
const RISIKO = { rendah: "Risiko rendah", sedang: "Risiko sedang", tinggi: "Risiko tinggi" };
const JENIS = { rawat_inap: "Rawat inap", rawat_jalan: "Rawat jalan" };
const TINGKAT = { kritis: "Kritis", peringatan: "Peringatan", info: "Info" };

// Ikon garis 24px (gaya Lucide), digambar dengan stroke currentColor.
const ICON = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10"/>',
  back: '<path d="M15 18l-6-6 6-6"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 8v5M12 16.5h.01"/><circle cx="12" cy="12" r="9"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5h.01"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  inbox: '<path d="M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z"/>',
  send: '<path d="M4 12 20 4l-6 16-3-7z"/>',
};
const icon = (n) => `<i data-icon="${n}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[n]}</svg></i>`;
const hydrateIcons = (root = document) => root.querySelectorAll("i[data-icon]:empty").forEach((el) => (el.outerHTML = icon(el.dataset.icon)));

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const rp = (n) => (n == null ? "–" : "Rp " + Number(n).toLocaleString("id-ID"));
const rpShort = (n) => {
  if (n == null) return "–";
  if (n >= 1e9) return "Rp " + (n / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 1 }) + " M";
  if (n >= 1e6) return "Rp " + (n / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 1 }) + " jt";
  return rp(n);
};
const pill = (cls, text) => `<span class="pill ${cls}">${esc(text)}</span>`;
const inisial = (nama) => esc(String(nama).replace(/^(tn|ny|nn|an|by)\.?\s*/i, "").replace(/[^A-Za-z]/g, "").slice(0, 2).toUpperCase() || "?");
const skorWarna = (s) => (s >= 80 ? "var(--ok)" : s >= 50 ? "var(--kunyit)" : "var(--bad)");
const page = (html) => { view.innerHTML = `<div class="page">${html}</div>`; };

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) {
    let msg = `Permintaan gagal (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail)) msg = "Periksa isian: " + j.detail.map((d) => d.loc.at(-1)).join(", ");
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function toast(msg, ok = true) {
  const t = document.getElementById("toast");
  t.innerHTML = (ok ? icon("check") : icon("alert")) + `<span>${esc(msg)}</span>`;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), 2800);
}

async function refreshBadge() {
  try {
    const s = await api("/api/stats");
    const n = s.per_status.perlu_perbaikan || 0;
    const b = document.getElementById("badge");
    b.textContent = n;
    b.hidden = n === 0;
  } catch (_) {}
}

function busy(btn, on, label) {
  if (on) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.textContent = label || "Menganalisis…"; }
  else { btn.disabled = false; btn.innerHTML = btn.dataset.label; }
}

// ---------- Ringkasan ----------
async function viewRingkasan() {
  const s = await api("/api/stats");
  const max = Math.max(1, ...s.penyebab_teratas.map((p) => p[1]));
  const siap = s.per_status.siap_kirim || 0;
  const perlu = s.per_status.perlu_perbaikan || 0;
  page(`
    <header class="page-head">
      <div><h1>Ringkasan klaim</h1><p>Kondisi klaim JKN sebelum dan sesudah dikirim ke BPJS.</p></div>
      <div class="btns"><a class="btn btn-secondary" href="/api/claims/export.csv">${icon("download")}Unduh CSV</a>
      <a class="btn btn-primary" href="#/baru">${icon("plus")}Klaim baru</a></div>
    </header>
    <section class="stats">
      <div class="stat"><span class="label">Total klaim</span><span class="v num">${s.total}</span><span class="s">${siap} siap kirim</span></div>
      <div class="stat money"><span class="label">Dana tertahan</span><span class="v num">${rpShort(s.nilai_tertahan)}</span><span class="s">Perlu perbaikan dan pending BPJS</span></div>
      <div class="stat"><span class="label">Pending rate</span><span class="v num">${s.pending_rate == null ? "–" : s.pending_rate + "%"}</span><span class="s">Dari klaim yang sudah dikirim</span></div>
      <div class="stat"><span class="label">Skor kelengkapan</span><span class="v num">${s.rata_skor ?? "–"}<small class="muted" style="font-size:.9rem;font-weight:500"> /100</small></span><span class="s">Rata-rata semua klaim</span></div>
    </section>
    <section class="split">
      <div class="card">
        <div class="card-head"><h2>Penyebab temuan kritis</h2><span class="label">${perlu} klaim perlu perbaikan</span></div>
        <div class="card-body">${s.penyebab_teratas.length ? `<div class="bars">${s.penyebab_teratas.map(([k, n]) =>
          `<div class="bar"><span>${esc(k[0].toUpperCase() + k.slice(1))}</span><span class="num muted">${n}</span><span class="track"><span class="fill warn" style="width:${(n / max) * 100}%"></span></span></div>`).join("")}</div>`
          : `<div class="empty">${icon("check")}<span>Semua klaim lolos pengecekan.</span></div>`}
          ${perlu ? `<div><a class="btn btn-secondary" href="#/klaim?status=perlu_perbaikan">Perbaiki ${perlu} klaim</a></div>` : ""}
        </div>
      </div>
      <div class="card">
        <div class="card-head"><h2>Per status</h2></div>
        <div class="card-body"><div class="bars">${Object.keys(STATUS).map((k) => `
          <div class="bar"><span>${pill("s-" + k, STATUS[k])}</span><span class="num muted">${s.per_status[k] || 0}</span>
          <span class="track"><span class="fill f-${k}" style="width:${s.total ? ((s.per_status[k] || 0) / s.total) * 100 : 0}%"></span></span></div>`).join("")}</div>
        </div>
      </div>
    </section>`);
}

// ---------- Antrian ----------
async function viewKlaim(params) {
  const status = params.get("status") || "";
  const rows = await api("/api/claims" + (status ? `?status=${encodeURIComponent(status)}` : ""));
  page(`
    <header class="page-head">
      <div><h1>Antrian klaim</h1><p>Buka klaim untuk melihat saran kode dan temuan.</p></div>
      <a class="btn btn-primary" href="#/baru">${icon("plus")}Klaim baru</a>
    </header>
    <nav class="tabs" aria-label="Filter status">
      <a class="${status ? "" : "on"}" href="#/klaim">Semua</a>
      ${Object.entries(STATUS).map(([k, v]) => `<a class="${status === k ? "on" : ""}" href="#/klaim?status=${k}">${v}</a>`).join("")}
    </nav>
    <div class="card">${rows.length ? `<div class="table-wrap"><table>
      <thead><tr><th>Pasien</th><th class="hide-sm">Diagnosis utama</th><th class="hide-sm">Skor</th><th class="right hide-sm">Nilai</th><th>Status</th></tr></thead>
      <tbody>${rows.map((k) => {
        const a = k.analisis || {};
        const du = a.diagnosis_utama;
        const sk = a.skor_kelengkapan;
        return `<tr class="row" data-id="${k.id}" tabindex="0">
          <td><div class="who"><span class="av">${inisial(k.pasien_inisial)}</span><span><b>${esc(k.pasien_inisial)}</b><small><span class="mono">${esc(k.no_klaim)}</span> · ${JENIS[k.jenis_rawat]}</small>${du ? `<span class="dx-sm"><span class="code-tag">${esc(du.kode)}</span>${esc(du.deskripsi)}</span>` : ""}</span></div></td>
          <td class="hide-sm">${du ? `<span class="code-tag">${esc(du.kode)}</span>${esc(du.deskripsi)}` : '<span class="muted">Belum terkode</span>'}</td>
          <td class="hide-sm">${sk == null ? "–" : `<span class="score-mini"><span class="track"><span class="fill" style="width:${sk}%;background:${skorWarna(sk)}"></span></span><span class="num">${sk}</span></span>`}</td>
          <td class="right num hide-sm">${rp(k.nilai_tarif)}</td>
          <td>${pill("s-" + k.status, STATUS[k.status])}</td></tr>`;
      }).join("")}</tbody></table></div>`
      : `<div class="empty">${icon("inbox")}<span>Belum ada klaim dengan status ini.</span></div>`}</div>`);
  view.querySelectorAll("tr.row").forEach((tr) => {
    const go = () => (location.hash = `#/klaim/${tr.dataset.id}`);
    tr.addEventListener("click", go);
    tr.addEventListener("keydown", (e) => e.key === "Enter" && go());
  });
}

// ---------- Hasil analisis (dipakai detail & cek cepat) ----------
function renderAnalisis(a, oleh, catatan) {
  const kode = (x, label) => `<div class="code"><span class="k">${esc(x.kode)}</span><span class="d">${esc(x.deskripsi)}</span><span class="w">${label} · ${esc(x.alasan)}</span></div>`;
  const kodeList = [
    ...(a.diagnosis_utama ? [kode(a.diagnosis_utama, "Diagnosis utama")] : []),
    ...a.diagnosis_sekunder.map((x) => kode(x, "Diagnosis sekunder")),
    ...a.prosedur.map((x) => kode(x, "Prosedur")),
  ];
  const urut = { kritis: 0, peringatan: 1, info: 2 };
  const ikon = { kritis: "x", peringatan: "alert", info: "info" };
  const temuan = [...a.temuan].sort((x, y) => urut[x.tingkat] - urut[y.tingkat]);
  return `
    <div class="score">
      <div class="ring" style="--p:${a.skor_kelengkapan};--c:${skorWarna(a.skor_kelengkapan)}"><span class="num">${a.skor_kelengkapan}</span></div>
      <div><h3>${esc(a.ringkasan)}</h3><div class="meta">${pill("r-" + a.risiko_pending, RISIKO[a.risiko_pending])}<span>Dianalisis oleh ${oleh === "ai" ? "AI" : "mesin aturan"}</span></div></div>
    </div>
    ${catatan ? `<div class="notice">${icon("info")}<span>${esc(catatan)}</span></div>` : ""}
    <div><div class="section-label">Saran kode</div><div class="codes">${kodeList.join("") || '<span class="muted">Belum ada kode yang bisa disarankan.</span>'}</div></div>
    <div><div class="section-label">Temuan (${temuan.length})</div>
      ${temuan.length ? `<ul class="findings">${temuan.map((t) => `<li class="finding">
        <span class="ic t-${t.tingkat}">${icon(ikon[t.tingkat])}</span>
        <span class="t">${esc(t.kategori[0].toUpperCase() + t.kategori.slice(1))} <span class="muted" style="font-weight:400">· ${TINGKAT[t.tingkat]}</span></span>
        <span class="p">${esc(t.pesan)}</span><span class="s">${esc(t.saran)}</span></li>`).join("")}</ul>`
        : `<div class="notice" style="background:var(--ok-soft);color:var(--ok)">${icon("check")}<span>Tidak ada temuan. Klaim siap dikirim.</span></div>`}</div>
    <p class="disclaimer">Hasil ini saran. Keputusan akhir koding ada di koder dan DPJP.</p>`;
}

// ---------- Detail ----------
async function viewDetail(id) {
  const k = await api(`/api/claims/${id}`);
  const aksi = {
    perlu_perbaikan: [],
    siap_kirim: [["terkirim", "Tandai terkirim", "send", "btn-primary"]],
    terkirim: [["cair", "Tandai cair", "check", "btn-primary"], ["pending_bpjs", "BPJS minta kelengkapan", "alert", "btn-secondary"]],
    pending_bpjs: [["terkirim", "Kirim ulang", "send", "btn-primary"], ["cair", "Tandai cair", "check", "btn-secondary"]],
    cair: [],
  }[k.status];
  page(`
    <header class="page-head">
      <div><a class="crumb" href="#/klaim">${icon("back")}Antrian klaim</a>
        <h1>${esc(k.pasien_inisial)}</h1><p><span class="mono">${esc(k.no_klaim)}</span> · ${JENIS[k.jenis_rawat]}${k.nilai_tarif != null ? ` · ${rp(k.nilai_tarif)}` : ""}</p></div>
      <div class="btns">${pill("s-" + k.status, STATUS[k.status])}${aksi.map(([s, l, ic, cls]) => `<button class="btn ${cls}" data-status="${s}">${icon(ic)}${l}</button>`).join("")}</div>
    </header>
    <section class="split">
      <div class="card">
        <div class="card-head"><h2>Resume medis</h2></div>
        <form class="card-body" id="f">
          <div class="fields">
            <label class="field"><span>Tanggal masuk</span><input type="date" id="tgl_masuk" value="${esc(k.tgl_masuk || "")}"></label>
            <label class="field"><span>Tanggal keluar</span><input type="date" id="tgl_keluar" value="${esc(k.tgl_keluar || "")}"></label>
            <label class="field"><span>Nilai tarif (Rp)</span><input type="number" min="0" id="nilai_tarif" value="${k.nilai_tarif ?? ""}"></label>
          </div>
          <label class="field"><span>Isi resume</span><textarea id="resume">${esc(k.resume)}</textarea></label>
          <div class="btns"><button class="btn btn-primary" type="submit">Simpan dan cek ulang</button>
            <button class="btn btn-ghost" type="button" id="ulang">${icon("refresh")}Cek ulang saja</button></div>
        </form>
        <div class="card-body" style="border-top:1px solid var(--line)"><div class="section-label">Riwayat</div>
          <ul class="timeline">${k.riwayat.slice().reverse().map((r) =>
            `<li><span>${esc(r.aksi[0].toUpperCase() + r.aksi.slice(1))}${r.catatan ? ` · ${esc(r.catatan)}` : ""}<small>${new Date(r.waktu).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })}</small></span></li>`).join("")}</ul></div>
      </div>
      <div class="card sticky">
        <div class="card-head"><h2>Hasil pengecekan</h2></div>
        <div class="card-body">${k.analisis ? renderAnalisis(k.analisis, k.dianalisis_oleh, k.catatan_analisis) : '<span class="muted">Belum dianalisis.</span>'}</div>
      </div>
    </section>`);

  const f = view.querySelector("#f");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = f.querySelector("button[type=submit]");
    busy(btn, true);
    const nilai = f.querySelector("#nilai_tarif").value;
    try {
      await api(`/api/claims/${id}`, { method: "PUT", body: JSON.stringify({
        resume: f.querySelector("#resume").value,
        tgl_masuk: f.querySelector("#tgl_masuk").value || null,
        tgl_keluar: f.querySelector("#tgl_keluar").value || null,
        nilai_tarif: nilai === "" ? null : Number(nilai),
      }) });
      toast("Tersimpan dan dicek ulang");
      route();
    } catch (err) { toast(err.message, false); busy(btn, false); }
  });
  view.querySelector("#ulang").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true);
    try { await api(`/api/claims/${id}/analyze`, { method: "POST" }); toast("Selesai dicek ulang"); route(); }
    catch (err) { toast(err.message, false); busy(btn, false); }
  });
  view.querySelectorAll("[data-status]").forEach((b) => b.addEventListener("click", async () => {
    const catatan = b.dataset.status === "pending_bpjs" ? "BPJS meminta kelengkapan" : null;
    try {
      await api(`/api/claims/${id}/status`, { method: "POST", body: JSON.stringify({ status: b.dataset.status, catatan }) });
      toast("Status: " + STATUS[b.dataset.status]); route();
    } catch (err) { toast(err.message, false); }
  }));
}

// ---------- Klaim baru ----------
function viewBaru() {
  page(`
    <header class="page-head"><div><h1>Klaim baru</h1><p>Tempel resume medis dari SIMRS. Klaira langsung mengeceknya.</p></div></header>
    <div class="card"><form class="card-body" id="f">
      <div class="fields">
        <label class="field"><span>Inisial pasien</span><input id="pasien_inisial" required maxlength="40" placeholder="Tn. A.B."></label>
        <label class="field"><span>Jenis layanan</span><select id="jenis_rawat"><option value="rawat_inap">Rawat inap</option><option value="rawat_jalan">Rawat jalan</option></select></label>
        <label class="field"><span>Tanggal masuk</span><input type="date" id="tgl_masuk"></label>
        <label class="field"><span>Tanggal keluar</span><input type="date" id="tgl_keluar"></label>
        <label class="field"><span>Nilai tarif INA-CBG (Rp)</span><input type="number" min="0" id="nilai_tarif" placeholder="Opsional"></label>
      </div>
      <label class="field"><span>Resume medis</span><textarea id="resume" required minlength="10" placeholder="Keluhan, diagnosis utama dan sekunder, hasil penunjang, terapi, tindakan, tanggal, DPJP…"></textarea>
        <small>Tulis inisial saja. NIK, nomor BPJS dan nomor HP disamarkan otomatis sebelum dianalisis AI.</small></label>
      <div class="btns"><button class="btn btn-primary" type="submit">Simpan dan cek</button><a class="btn btn-ghost" href="#/klaim">Batal</a></div>
    </form></div>`);
  const f = view.querySelector("#f");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = f.querySelector("button");
    busy(btn, true);
    const v = (id) => f.querySelector("#" + id).value;
    try {
      const k = await api("/api/claims", { method: "POST", body: JSON.stringify({
        pasien_inisial: v("pasien_inisial"), jenis_rawat: v("jenis_rawat"),
        tgl_masuk: v("tgl_masuk") || null, tgl_keluar: v("tgl_keluar") || null,
        nilai_tarif: v("nilai_tarif") === "" ? null : Number(v("nilai_tarif")), resume: v("resume"),
      }) });
      toast("Klaim tersimpan");
      location.hash = `#/klaim/${k.id}`;
    } catch (err) { toast(err.message, false); busy(btn, false); }
  });
}

// ---------- Cek cepat ----------
const CONTOH = `Keluhan: demam 4 hari, nyeri ulu hati, bintik merah di lengan.
Diagnosis utama: demam berdarah dengue.
Diagnosis sekunder: diabetes melitus tipe 2.
Hasil lab: trombosit 62.000, hematokrit 44%.
Terapi: infus RL, paracetamol.
Masuk 12/10/2026, pulang 16/10/2026.
DPJP: dr. A, Sp.PD`;

function viewCek() {
  page(`
    <header class="page-head"><div><h1>Cek cepat</h1><p>Cek satu resume tanpa menyimpannya.</p></div></header>
    <section class="split">
      <div class="card"><form class="card-body" id="f">
        <label class="field" style="max-width:240px"><span>Jenis layanan</span><select id="jenis_rawat"><option value="rawat_inap">Rawat inap</option><option value="rawat_jalan">Rawat jalan</option></select></label>
        <label class="field"><span>Resume medis</span><textarea id="resume">${esc(CONTOH)}</textarea></label>
        <div class="btns"><button class="btn btn-primary" type="submit">${icon("scan")}Cek sekarang</button></div>
      </form></div>
      <div class="card sticky"><div class="card-head"><h2>Hasil pengecekan</h2></div>
        <div class="card-body" id="out"><div class="empty">${icon("scan")}<span>Hasil muncul di sini setelah kamu menekan "Cek sekarang".</span></div></div></div>
    </section>`);
  const f = view.querySelector("#f");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = f.querySelector("button");
    busy(btn, true);
    try {
      const h = await api("/api/analyze", { method: "POST", body: JSON.stringify({ resume: f.querySelector("#resume").value, jenis_rawat: f.querySelector("#jenis_rawat").value }) });
      view.querySelector("#out").innerHTML = renderAnalisis(h.analisis, h.dianalisis_oleh, h.catatan);
    } catch (err) { toast(err.message, false); }
    busy(btn, false);
  });
}

// ---------- Router ----------
async function route() {
  const [path, query] = (location.hash.slice(1) || "/ringkasan").split("?");
  const parts = path.split("/").filter(Boolean);
  const params = new URLSearchParams(query || "");
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === (parts[0] || "ringkasan")));
  try {
    if (parts[0] === "klaim" && parts[1]) await viewDetail(parts[1]);
    else if (parts[0] === "klaim") await viewKlaim(params);
    else if (parts[0] === "baru") viewBaru();
    else if (parts[0] === "cek") viewCek();
    else await viewRingkasan();
  } catch (err) {
    page(`<div class="card"><div class="empty">${icon("alert")}<b>Halaman tidak bisa dimuat</b><span>${esc(err.message)}</span><a class="btn btn-secondary" href="#/ringkasan">Kembali ke ringkasan</a></div></div>`);
  }
  window.scrollTo(0, 0);
  refreshBadge();
}

hydrateIcons();
window.addEventListener("hashchange", route);
api("/api/health").then((h) => {
  const el = document.getElementById("engine");
  el.className = "engine " + (h.ai_aktif ? "ai" : "rule");
  el.innerHTML = `<span class="dot"></span><span>${h.ai_aktif ? "AI aktif" : "Mode aturan (tanpa AI)"}</span>`;
  el.title = h.ai_aktif ? h.model : "Isi ANTHROPIC_API_KEY untuk mengaktifkan AI";
}).catch(() => {});
route();
