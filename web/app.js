/* RAIS · Filtro de Dados — lógica do frontend (vanilla JS, sem build). */
"use strict";

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const state = {
  files: [],
  municipios: [],
  subclasses: [],
  current: null,
};

async function api(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function fmtPct(v) {
  const n = Number(v) || 0;
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
}

function fmtInt(v) {
  return Number(v || 0).toLocaleString("pt-BR");
}

/* ---------------------------------------------------------------- boot */
async function boot() {
  try {
    const h = await api("/api/health");
    $("#meta-version").textContent = "v" + h.versao;
    setStatus(true);
  } catch {
    setStatus(false);
  }
  await loadFiles();
  await loadDatalists();
  bindEvents();
}

function setStatus(ok) {
  const chip = $("#meta-status");
  chip.classList.toggle("ok", ok);
  chip.innerHTML = `<span class="dot"></span>${ok ? "servidor ativo" : "offline"}`;
}

async function loadFiles() {
  try {
    const d = await api("/api/files");
    state.files = d.arquivos || [];
  } catch {
    state.files = [];
  }
  const sel = $("#file-select");
  sel.innerHTML = "";
  if (!state.files.length) {
    sel.innerHTML = '<option value="">— nenhum arquivo em dados/ —</option>';
    $("#file-hint").textContent = "adicione arquivos .csv na pasta dados/";
    return;
  }
  // prioriza o arquivo parcial para desenvolvimento/CI
  const order = [...state.files].sort((a, b) => (a.classificacao === b.classificacao ? 0 : a.classificacao === "parcial" ? -1 : 1));
  for (const f of order) {
    const o = el("option", "", `${f.name}  (${f.size_human} · ${f.classificacao})`);
    o.value = f.name;
    sel.appendChild(o);
  }
  await onFileChange();
}

async function loadDatalists() {
  try {
    const m = await api("/api/layouts?tipo=municipio&limit=6000");
    const s = await api("/api/layouts?tipo=subclasse&limit=8000");
    state.municipios = m.itens || [];
    state.subclasses = s.itens || [];
  } catch {
    state.municipios = [];
    state.subclasses = [];
  }
  fillDatalist("#list-municipios", state.municipios);
  fillDatalist("#list-subclasses", state.subclasses);
}

function fillDatalist(sel, itens) {
  const dl = $(sel);
  dl.innerHTML = "";
  for (const i of itens) {
    const o = el("option", "", `${i.codigo} — ${i.rotulo}`);
    o.value = i.codigo;
    dl.appendChild(o);
  }
}

/* ------------------------------------------------------------- eventos */
function bindEvents() {
  $("#file-select").addEventListener("change", onFileChange);
  $("#btn-analyze").addEventListener("click", runAnalyze);
  $("#btn-index").addEventListener("click", buildIndex);
  $("#btn-ref").addEventListener("click", () => {
    $("#municipio").value = "330100";
    $("#subclasse").value = "2342702";
    runAnalyze();
  });
  $("#municipio").addEventListener("input", () => {
    const v = $("#municipio").value.trim();
    const m = state.municipios.find((i) => i.codigo === v);
    $("#municipio-hint").textContent = m ? m.rotulo : "";
  });
  $("#subclasse").addEventListener("input", () => {
    const v = $("#subclasse").value.trim();
    const s = state.subclasses.find((i) => i.codigo === v);
    $("#subclasse-hint").textContent = s ? s.rotulo : "";
  });
}

async function onFileChange() {
  const name = $("#file-select").value;
  const f = state.files.find((x) => x.name === name);
  state.current = f;
  if (!f) return;
  $("#file-hint").textContent = `${f.classificacao} · ${f.size_human}`;
  try {
    const sch = await api(`/api/schema?file=${encodeURIComponent(name)}`);
    const schema = sch.schema || {};
    const avisos = [];
    if (!schema.present || !schema.present.includes("municipio")) avisos.push("sem coluna de município");
    if (!schema.present || !schema.present.includes("escolaridade")) avisos.push("sem coluna de escolaridade");
    if (!schema.present || !schema.present.includes("identificador_estabelecimento")) avisos.push("sem coluna de identificação (contagem de empresas indisponível)");
    if (avisos.length) $("#file-hint").textContent = `${f.size_human} · ${avisos.join(" · ")}`;
  } catch { /* silencioso */ }
  await refreshIndexState();
}

async function refreshIndexState() {
  const name = $("#file-select").value;
  const el = $("#index-state");
  if (!name) { el.textContent = ""; return; }
  try {
    const d = await api(`/api/index?file=${encodeURIComponent(name)}`);
    const st = d.index;
    el.textContent = st && st.exists
      ? `índice ok · ${fmtInt(st.rows)} linhas`
      : "índice não construído";
  } catch {
    el.textContent = "";
  }
}

async function buildIndex() {
  const name = $("#file-select").value;
  if (!name) return;
  const btn = $("#btn-index");
  const el = $("#index-state");
  btn.disabled = true;
  el.textContent = "construindo…";
  try {
    const d = await api("/api/index", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file: name }),
    });
    if (d.error) { el.textContent = "erro: " + d.error; }
    else { el.textContent = `índice pronto · ${fmtInt(d.indexed_rows)} linhas em ${d.elapsed_s}s`; }
  } catch (e) {
    el.textContent = "erro ao construir índice";
  } finally {
    btn.disabled = false;
  }
}

/* --------------------------------------------------------------- análise */
async function runAnalyze() {
  const name = $("#file-select").value;
  const municipio = $("#municipio").value.trim();
  const subclasse = $("#subclasse").value.trim();
  if (!name) { showBanner("Selecione um arquivo de base primeiro.", "error"); return; }
  if (!municipio && !subclasse) { showBanner("Informe ao menos um filtro (município e/ou subclasse).", "error"); return; }

  const btn = $("#btn-analyze");
  const chip = $("#scan-chip");
  btn.disabled = true;
  chip.textContent = "processando…";
  chip.classList.add("run");

  try {
    const d = await api("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file: name, municipio, subclasse, use_index: $("#use-index").checked }),
    });
    if (d.error) { showBanner("Erro: " + d.error, "error"); return; }
    render(d);
  } catch (e) {
    showBanner("Falha ao processar a consulta: " + e.message, "error");
  } finally {
    btn.disabled = false;
    chip.classList.remove("run");
  }
}

function render(d) {
  $("#empty-state").classList.add("hidden");
  $("#results").classList.remove("hidden");
  $("#scan-chip").textContent = `${d.modo} · ${d.elapsed_s}s`;

  const f = d.file || {};
  $("#footer-meta").textContent =
    `${d.arquivo} · ${d.total_linhas.toLocaleString("pt-BR")} linhas varridas · ${fmtInt(d.vinculos)} vínculos · ${d.elapsed_s}s`;

  // ---- avisos / banners
  const banners = [];
  for (const a of (d.avisos || [])) banners.push(a);
  const est = d.estabelecimentos || {};
  if (est.disponivel === false) {
    banners.push("A contagem de empresas está indisponível: este arquivo não possui a coluna de identificação do estabelecimento (IDENTIFICAD/CNPJ). Use a base RAIS oficial ou gere uma amostra com `python scripts/make_sample.py`.");
  }
  if (banners.length) showBanner(banners.join(" "), est.disponivel === false ? "warn" : "warn");
  else hideBanner();

  // ---- cards
  $("#r-empresas").textContent = est.disponivel ? fmtInt(est.quantidade) : "—";
  $("#r-empresas-sub").textContent = est.disponivel ? `modo: ${est.modo}` : "indisponível (sem coluna de identificação)";
  $("#r-vinculos").textContent = fmtInt(d.vinculos);
  $("#r-vinculos-sub").textContent = `filtros: ${d.filtros.municipio || "*"} · ${d.filtros.subclasse || "*"}`;
  $("#r-considerados").textContent = est.disponivel ? fmtInt(est.total_vinculos_considerados) : "—";

  // ---- tabela de empresas
  const tbody = $("#t-empresas tbody");
  tbody.innerHTML = "";
  if (est.disponivel && (est.por_estabelecimento || []).length) {
    for (const e of est.por_estabelecimento) {
      const tr = el("tr");
      tr.appendChild(el("td", "", e.identificador));
      tr.appendChild(el("td", "", e.tipo_estabelecimento || "—"));
      tr.appendChild(el("td", "num", fmtInt(e.vinculos)));
      tbody.appendChild(tr);
    }
  } else {
    const tr = el("tr");
    tr.appendChild(el("td", "", "—"));
    tr.appendChild(el("td", "", "—"));
    tr.appendChild(el("td", "num", "—"));
    tbody.appendChild(tr);
  }

  // ---- pizza + legenda + tabela de escolaridade
  const escItens = [];
  (d.escolaridade || []).forEach((e, i) => {
    escItens.push({
      codigo: e.codigo, label: e.rotulo, freq: e.frequencia, pct: e.percentual,
      color: ESCOLARIDADE_CORES[i % ESCOLARIDADE_CORES.length],
    });
  });
  const ign = d.ignorados_escolaridade;
  escItens.push({
    codigo: "-1", label: ign.rotulo, freq: ign.frequencia, pct: ign.percentual,
    color: ESCOLARIDADE_CORES[ESCOLARIDADE_CORES.length - 1], isIgnored: true,
  });

  buildLegend(escItens);
  drawPie($("#pie-escolaridade"), escItens);

  const tb2 = $("#t-escolaridade tbody");
  tb2.innerHTML = "";
  for (const it of escItens) {
    tb2.appendChild(escRow(it.codigo, it.label, it.freq, it.pct));
  }

  // ---- rodapé de contexto
  const ctx = [];
  if (d.filtros.municipio) {
    const m = state.municipios.find((i) => i.codigo === d.filtros.municipio);
    if (m) ctx.push(`Município: ${m.rotulo}`);
  }
  if (d.filtros.subclasse) {
    const s = state.subclasses.find((i) => i.codigo === d.filtros.subclasse);
    if (s) ctx.push(`Subclasse: ${s.rotulo}`);
  }
  $("#footnote").textContent = ctx.join(" · ") || "Sem contexto adicional de layout.";
}

function escRow(codigo, rotulo, freq, pct) {
  const tr = el("tr");
  tr.appendChild(el("td", "", codigo));
  tr.appendChild(el("td", "", rotulo));
  tr.appendChild(el("td", "num", fmtInt(freq)));
  tr.appendChild(el("td", "num", fmtPct(pct)));
  return tr;
}

/* --------------------------------------------------------- gráfico de pizza */
const ESCOLARIDADE_CORES = [
  "#e4572e", "#58a4b0", "#e6a13a", "#4e9b5f", "#8a6fd0", "#d9709b",
  "#5b8dd9", "#a3a33c", "#c17c3a", "#3a9b8f", "#b4546a", "#8b93a1",
];

let lastPieSlices = null;

function drawPie(canvas, slices) {
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const size = canvas.clientWidth || 280;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);
  lastPieSlices = slices;

  const cx = size / 2, cy = size / 2, radius = size / 2 - 10;
  const theme = document.documentElement.getAttribute("data-theme");
  const stroke = theme === "light" ? "#fffdf6" : "#12171f";
  const total = slices.reduce((s, x) => s + (x.freq || 0), 0);

  ctx.lineWidth = 2;
  if (!total) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(128,128,128,0.12)";
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.stroke();
    return;
  }

  let start = -Math.PI / 2;
  for (const s of slices) {
    const angle = ((s.freq || 0) / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = s.color;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.stroke();
    start += angle;
  }
}

function buildLegend(itens) {
  const leg = $("#legend-escolaridade");
  if (!leg) return;
  leg.innerHTML = "";
  for (const it of itens) {
    const row = el("div", "legend-item");
    const sw = el("span", "legend-swatch");
    sw.style.background = it.color;
    const txt = el("span", "legend-text");
    txt.appendChild(el("span", "legend-label", `${it.codigo} — ${it.label}`));
    txt.appendChild(el("span", "legend-value", `${fmtInt(it.freq)} · ${fmtPct(it.pct)}`));
    row.appendChild(sw);
    row.appendChild(txt);
    leg.appendChild(row);
  }
}

function redrawPie() {
  if (!lastPieSlices) return;
  drawPie($("#pie-escolaridade"), lastPieSlices);
}

function showBanner(msg, kind) {
  const b = $("#banner");
  b.textContent = msg;
  b.classList.remove("hidden", "error");
  if (kind === "error") b.classList.add("error");
}

function hideBanner() {
  const b = $("#banner");
  b.classList.add("hidden");
  b.textContent = "";
}

/* ------------------------------------------------------------- tema claro/escuro */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const btn = $("#theme-toggle");
  if (btn) {
    btn.textContent = theme === "dark" ? "☀️" : "🌙";
    btn.setAttribute("aria-label", theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro");
  }
  redrawPie();
}

function initTheme() {
  const saved = localStorage.getItem("rais-theme");
  applyTheme(saved === "light" ? "light" : "dark");
  const btn = $("#theme-toggle");
  if (btn) {
    btn.addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme");
      const next = cur === "light" ? "dark" : "light";
      applyTheme(next);
      localStorage.setItem("rais-theme", next);
    });
  }
}

initTheme();
boot();
