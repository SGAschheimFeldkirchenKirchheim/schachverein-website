"""
Reiter "Partien" auf den Teamseiten: hochgeladene Partien nachspielen.

Die Partien (PGN) kommen vom Tabellenrechner (nur Ligen aus dem Ligamanager, z. B. U20 I)
im Feld "partien" von mannschaften/<team>.json. liga.py ruft reiter_partien() und partie_id() auf.

Bedienung im Browser:
  Pfeiltasten / Wischen über die Zugliste, Pos1/Ende, Leertaste = automatisch abspielen,
  F = Brett drehen, Klick auf einen Zug springt dorthin, Link teilen springt direkt zur Partie.

Bibliotheken liegen lokal in lib/partien/ (siehe README dort).
"""

import html
import json

# ==========================================
# EINSTELLUNGEN
# ==========================================
LIB = "lib/partien"
AUTOPLAY_SEKUNDEN = 1.5          # Tempo beim automatischen Abspielen
EIGENE_UNTEN = True              # eigener Spieler unten (sonst immer Weiß unten)
NOTATION = "de"                  # "de" = K D T L S (deutsch), "en" = K Q R B N
LICHESS_LINK = True              # Knopf "Auf Lichess analysieren"
# Brettfarben (hell, dunkel) – Vereinsfarben
BRETT_HELL = "#e9eef6"
BRETT_DUNKEL = "#8ca2c0"


def esc(x):
    return html.escape(str(x if x is not None else ""))


def partie_id(d, m, brett):
    """ID der Partie zu einem Brett eines Wettkampfs (oder None) – für den ▶-Link in 'Unsere Spiele'."""
    index = d.get("_partie_index")
    if index is None:
        index = d["_partie_index"] = {(p["r"], p["h"], p["g"], p["brett"]): p["id"] for p in d.get("partien", [])}
    return index.get((m["r"], m["h"], m["g"], brett))


def reiter_partien(d):
    partien = d.get("partien") or []
    if not partien:
        return ""
    daten = [{k: p.get(k) for k in ("id", "r", "brett", "w", "b", "wd", "bd", "erg", "weiss_eigen", "pgn")}
             for p in sorted(partien, key=lambda p: (p["r"], p["brett"]))]
    for p, roh in zip(daten, sorted(partien, key=lambda p: (p["r"], p["brett"]))):
        gegner_team = roh["g"] if roh["h"] == d["eigen"] else roh["h"]
        p["gegner"] = d["teams"].get(str(gegner_team), "")
    einstellungen = {"autoplay": AUTOPLAY_SEKUNDEN, "eigeneUnten": EIGENE_UNTEN, "lichess": LICHESS_LINK,
                     "deutsch": NOTATION == "de"}
    json_text = json.dumps({"partien": daten, "cfg": einstellungen}, ensure_ascii=False,
                           separators=(",", ":")).replace("</", "<\\/")
    return f"""
      <link rel="stylesheet" href="{LIB}/chessground.base.css">
      <link rel="stylesheet" href="{LIB}/chessground.cburnett.css">
      <div class="pv" data-pv>
        <aside class="pv-liste">
          <div class="pv-filter">
            <select data-pv-runde aria-label="Runde"><option value="">Alle Runden</option></select>
            <input type="search" data-pv-suche placeholder="Spieler suchen" aria-label="Spieler suchen">
          </div>
          <ol data-pv-liste></ol>
        </aside>
        <div class="pv-haupt">
          <div class="pv-spieler pv-oben" data-pv-oben></div>
          <div class="pv-brett-rahmen"><div class="pv-brett" data-pv-brett></div></div>
          <div class="pv-spieler pv-unten" data-pv-unten></div>
          <div class="pv-knoepfe" role="toolbar" aria-label="Partie steuern">
            <button type="button" data-pv="anfang" title="Anfang (Pos1)" aria-label="Anfang">⏮</button>
            <button type="button" data-pv="zurueck" title="Zurück (←)" aria-label="Zurück">◀</button>
            <button type="button" data-pv="play" title="Abspielen (Leertaste)" aria-label="Abspielen">▶</button>
            <button type="button" data-pv="vor" title="Vor (→)" aria-label="Vor">▶▶</button>
            <button type="button" data-pv="ende" title="Ende (Ende)" aria-label="Ende">⏭</button>
            <button type="button" data-pv="drehen" title="Brett drehen (F)" aria-label="Brett drehen">⇅</button>
          </div>
        </div>
        <div class="pv-seite">
          <div class="pv-kopf" data-pv-kopf></div>
          <div class="pv-zuege" data-pv-zuege tabindex="0" aria-label="Züge"></div>
          <div class="pv-aktionen">
            <button type="button" data-pv="teilen">Link kopieren</button>
            <a data-pv-download download>PGN herunterladen</a>
            <a data-pv-lichess target="_blank" rel="noopener">Auf Lichess analysieren ↗</a>
          </div>
        </div>
      </div>
      <p class="klein pv-credit">Partien aus dem Ligamanager des Bayerischen Schachbunds.
        Brett: <a href="https://github.com/lichess-org/chessground" target="_blank" rel="noopener">chessground</a> (GPL-3.0),
        Figuren: Colin M.L. Burnett (CC BY-SA 3.0).</p>
      <script type="application/json" id="pv-daten">{json_text}</script>
      {PARTIEN_CSS}
      {PARTIEN_JS}"""


PARTIEN_CSS = """<style>
  .pv { display: grid; grid-template-columns: 16rem minmax(0, 1fr) 16rem; gap: 1rem 1.25rem; align-items: start; margin-top: 1rem; }
  .pv-liste { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
  .pv-filter { display: grid; gap: .4rem; padding: .6rem; border-bottom: 1px solid var(--line); }
  .pv-filter select, .pv-filter input { font: inherit; font-size: .9rem; padding: .4rem .5rem; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--text); }
  .pv-liste ol { list-style: none; margin: 0; padding: 0; max-height: calc(var(--pv-b) - 1rem); overflow-y: auto; }
  .pv-liste li button { all: unset; box-sizing: border-box; display: grid; grid-template-columns: 1fr auto; gap: 0 .5rem; width: 100%; padding: .55rem .7rem; cursor: pointer; border-bottom: 1px solid var(--line); font-size: .88rem; color: var(--text); }
  .pv-liste li button:hover { background: var(--soft); }
  .pv-liste li button[aria-current="true"] { background: var(--accent); color: #fff; }
  .pv-liste li button[aria-current="true"] .pv-meta { color: #dbe6f5; }
  .pv-liste li button:focus-visible { outline: 2px solid var(--hell); outline-offset: -2px; }
  .pv-liste .pv-meta { grid-column: 1 / -1; font-size: .78rem; color: var(--muted); }
  .pv-liste .pv-erg { font-weight: 700; }
  .pv-leer { padding: .8rem; color: var(--muted); font-size: .9rem; }

  .pv-haupt { min-width: 0; --pv-b: min(34rem, calc(100vh - 13rem)); }
  .pv-brett-rahmen { width: 100%; max-width: max(18rem, var(--pv-b)); margin: 0 auto; }
  .pv-brett { width: 100%; aspect-ratio: 1; }
  .pv-brett cg-board { background-color: """ + BRETT_HELL + """;
    background-image: conic-gradient(""" + BRETT_DUNKEL + """ 0 25%, transparent 0 50%, """ + BRETT_DUNKEL + """ 0 75%, transparent 0);
    background-size: 25% 25%; border-radius: 4px; }
  .pv-brett cg-board square.last-move { background-color: rgba(255, 213, 74, .45); }
  .pv-brett coords { font-size: 10px; font-weight: 700; }
  .pv-brett coords.ranks coord:nth-child(odd), .pv-brett coords.files coord:nth-child(even) { color: """ + BRETT_HELL + """; }
  .pv-brett coords.ranks coord:nth-child(even), .pv-brett coords.files coord:nth-child(odd) { color: """ + BRETT_DUNKEL + """; }
  .pv-spieler { display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; max-width: max(18rem, var(--pv-b)); margin: 0 auto; padding: .45rem .2rem; font-weight: 600; }
  .pv-spieler .pv-dwz { color: var(--muted); font-weight: 400; font-size: .9rem; margin-left: .35rem; }
  .pv-spieler .pv-farbe { display: inline-block; width: .8rem; height: .8rem; border-radius: 50%; border: 1px solid var(--muted); margin-right: .45rem; vertical-align: -.05rem; }
  .pv-spieler .pv-farbe.w { background: #fff; } .pv-spieler .pv-farbe.b { background: #1d2333; }
  .pv-spieler .pv-pkt { font-variant-numeric: tabular-nums; }
  .pv-knoepfe { display: flex; justify-content: center; gap: .4rem; margin-top: .6rem; }
  .pv-knoepfe button { font: inherit; min-width: 2.8rem; height: 2.5rem; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--head); cursor: pointer; font-size: 1rem; }
  .pv-knoepfe button:hover { background: var(--soft); }
  .pv-knoepfe button[aria-pressed="true"] { background: var(--accent); color: #fff; border-color: var(--accent); }

  .pv-seite { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); display: flex; flex-direction: column; max-height: calc(var(--pv-b) + 6.5rem); }
  .pv { --pv-b: min(34rem, calc(100vh - 13rem)); }
  .pv-kopf { padding: .8rem 1rem; border-bottom: 1px solid var(--line); font-size: .9rem; }
  .pv-kopf strong { display: block; font-size: 1rem; color: var(--head); }
  .pv-kopf .pv-ergebnis { font-size: 1.4rem; font-weight: 700; color: var(--head); margin-top: .2rem; }
  .pv-zuege { overflow-y: auto; padding: .5rem; display: grid; grid-template-columns: 2.2rem 1fr 1fr; align-content: start; gap: 2px; font-variant-numeric: tabular-nums; min-height: 8rem; flex: 1; }
  .pv-zuege:focus-visible { outline: 2px solid var(--hell); outline-offset: -2px; }
  .pv-zuege .nr { color: var(--muted); text-align: right; padding: .25rem .4rem .25rem 0; font-size: .85rem; }
  .pv-zuege button { all: unset; cursor: pointer; padding: .25rem .45rem; border-radius: 4px; font-weight: 600; color: var(--text); }
  .pv-zuege button:hover { background: var(--soft); }
  .pv-zuege button[aria-current="true"] { background: var(--accent); color: #fff; }
  .pv-zuege .kommentar { grid-column: 1 / -1; font-size: .82rem; color: var(--muted); font-style: italic; padding: .1rem .4rem .35rem 2.6rem; }
  .pv-zuege .ende { grid-column: 1 / -1; text-align: center; font-weight: 700; padding: .5rem; color: var(--head); }
  .pv-aktionen { display: flex; flex-wrap: wrap; gap: .4rem .9rem; padding: .7rem 1rem; border-top: 1px solid var(--line); font-size: .88rem; }
  .pv-aktionen button { all: unset; cursor: pointer; color: var(--link, var(--accent)); text-decoration: underline; }
  .pv-credit { margin-top: 1rem; }

  @media (max-width: 1100px) {
    .pv { grid-template-columns: minmax(0, 1fr) 16rem; }
    .pv-liste { grid-column: 1 / -1; }
    .pv-liste ol { max-height: 12rem; }
  }
  @media (max-width: 720px) {
    .pv { grid-template-columns: 1fr; }
    .pv-seite { max-height: none; }
    .pv-zuege { max-height: 16rem; }
  }
</style>"""


PARTIEN_JS = """<script type="module">
import { Chessground } from "./""" + LIB + """/chessground.min.js";
import { Chess } from "./""" + LIB + """/chess.js";

const wurzel = document.querySelector("[data-pv]");
const { partien, cfg } = JSON.parse(document.getElementById("pv-daten").textContent);
const $ = (sel) => wurzel.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const DEUTSCH = { S: "N", L: "B", T: "R", D: "Q" };
const ANZEIGE = { N: "S", B: "L", R: "T", Q: "D" };
const zeigeSan = (san) => cfg.deutsch ? san.replace(/[NBRQ]/g, (f) => ANZEIGE[f]) : san;

let aktuell = null, plies = [], index = 0, unten = "white", timer = null;
const cg = Chessground($("[data-pv-brett]"), { viewOnly: true, coordinates: true, animation: { duration: 180 } });

// ---------- PGN einlesen (auch deutsche Notation S/L/T/D) ----------
function lese(pgn) {
  const versuche = [pgn, pgn.replace(/(^|\\s|\\.)([SLTD])(?=[a-h1-8x])/g, (m, a, f) => a + DEUTSCH[f])];
  for (const text of versuche) {
    const spiel = new Chess();
    try { spiel.loadPgn(text); } catch (e) { continue; }
    const kommentare = Object.fromEntries((spiel.getComments?.() || []).map((c) => [c.fen, c.comment]));
    return spiel.history({ verbose: true }).map((z) => ({ san: z.san, from: z.from, to: z.to, fen: z.after, kommentar: kommentare[z.after] }));
  }
  return null;
}

// ---------- Liste ----------
const rundeWahl = $("[data-pv-runde]"), suche = $("[data-pv-suche]"), liste = $("[data-pv-liste]");
[...new Set(partien.map((p) => p.r))].forEach((r) => rundeWahl.insertAdjacentHTML("beforeend", `<option value="${r}">Runde ${r}</option>`));

function zeigeListe() {
  const r = rundeWahl.value, q = suche.value.trim().toLowerCase();
  const treffer = partien.filter((p) => (!r || String(p.r) === r) && (!q || (p.w + " " + p.b).toLowerCase().includes(q)));
  liste.innerHTML = treffer.length ? treffer.map((p) => `
    <li><button type="button" data-id="${p.id}" aria-current="${aktuell && p.id === aktuell.id}">
      <span>${esc(p.w)} – ${esc(p.b)}</span><span class="pv-erg">${esc(erg(p.erg))}</span>
      <span class="pv-meta">Runde ${p.r} · Brett ${p.brett} · gegen ${esc(p.gegner)}</span>
    </button></li>`).join("") : '<li class="pv-leer">Keine Partie gefunden.</li>';
}
liste.addEventListener("click", (e) => { const b = e.target.closest("button[data-id]"); if (b) oeffne(+b.dataset.id, true); });
rundeWahl.addEventListener("change", zeigeListe);
suche.addEventListener("input", zeigeListe);

const erg = (e) => ({ "1/2-1/2": "½–½", "1-0": "1–0", "0-1": "0–1" }[e] || e || "*");
const punkte = (e, weiss) => e === "1/2-1/2" ? "½" : e === "1-0" ? (weiss ? "1" : "0") : e === "0-1" ? (weiss ? "0" : "1") : "";

// ---------- Partie ----------
function oeffne(id, mitHash) {
  const p = partien.find((x) => x.id === id) || partien[0];
  stop();
  aktuell = p;
  plies = lese(p.pgn) || [];
  unten = cfg.eigeneUnten && p.weiss_eigen === false ? "black" : "white";
  const dl = $("[data-pv-download]");
  dl.href = URL.createObjectURL(new Blob([p.pgn], { type: "application/x-chess-pgn" }));
  dl.download = `${p.w} - ${p.b} (Runde ${p.r}).pgn`.replace(/[\\\\/:*?"<>|]/g, "");
  const li = $("[data-pv-lichess]");
  li.hidden = !cfg.lichess;
  li.href = "https://lichess.org/analysis/pgn/" + encodeURIComponent(plies.map((z, i) => (i % 2 ? "" : i / 2 + 1 + ". ") + z.san).join(" "));
  $("[data-pv-kopf]").innerHTML = `Runde ${p.r} · Brett ${p.brett}<strong>gegen ${esc(p.gegner)}</strong>
    <div class="pv-ergebnis">${esc(erg(p.erg))}</div>${plies.length ? "" : "<div>Züge konnten nicht gelesen werden.</div>"}`;
  zeichneZuege();
  zeigeListe();
  gehe(0);
  if (mitHash) history.replaceState(null, "", "#partien/" + p.id);
}

function spielerZeile(weiss) {
  const p = aktuell;
  const name = weiss ? p.w : p.b, dwz = weiss ? p.wd : p.bd;
  return `<span><span class="pv-farbe ${weiss ? "w" : "b"}"></span>${esc(name)}${dwz ? `<span class="pv-dwz">${esc(dwz)}</span>` : ""}</span>
          <span class="pv-pkt">${index === plies.length ? punkte(p.erg, weiss) : ""}</span>`;
}

function zeichneZuege() {
  const teile = [];
  plies.forEach((z, i) => {
    if (i % 2 === 0) teile.push(`<span class="nr">${i / 2 + 1}.</span>`);
    teile.push(`<button type="button" data-ply="${i + 1}">${esc(zeigeSan(z.san))}</button>`);
    if (z.kommentar) {
      if (i % 2 === 0) teile.push("<span></span>");
      teile.push(`<span class="kommentar">${esc(z.kommentar)}</span>`);
      if (i % 2 === 0) teile.push(`<span class="nr">${i / 2 + 1}…</span><span></span>`);
    }
  });
  if (plies.length % 2 === 1) teile.push("<span></span>");
  teile.push(`<span class="ende">${esc(erg(aktuell.erg))}</span>`);
  $("[data-pv-zuege]").innerHTML = teile.join("");
}
$("[data-pv-zuege]").addEventListener("click", (e) => { const b = e.target.closest("button[data-ply]"); if (b) { stop(); gehe(+b.dataset.ply); } });

function gehe(n) {
  index = Math.max(0, Math.min(plies.length, n));
  const z = plies[index - 1];
  cg.set({ fen: z ? z.fen : "start", orientation: unten, lastMove: z ? [z.from, z.to] : undefined,
           check: z && /[+#]$/.test(z.san) ? true : false, turnColor: index % 2 ? "black" : "white" });
  $("[data-pv-oben]").innerHTML = spielerZeile(unten === "black");
  $("[data-pv-unten]").innerHTML = spielerZeile(unten === "white");
  const box = $("[data-pv-zuege]");
  box.querySelectorAll("button[aria-current]").forEach((b) => b.removeAttribute("aria-current"));
  const btn = box.querySelector(`button[data-ply="${index}"]`);
  if (btn) {
    btn.setAttribute("aria-current", "true");
    const oben = btn.offsetTop - box.offsetTop, unten_ = oben + btn.offsetHeight;
    if (oben < box.scrollTop || unten_ > box.scrollTop + box.clientHeight) box.scrollTop = oben - box.clientHeight / 2;
  } else if (index === 0) box.scrollTop = 0;
}

// ---------- Steuerung ----------
function stop() { clearInterval(timer); timer = null; wurzel.querySelector('[data-pv="play"]').setAttribute("aria-pressed", "false"); }
function play() {
  if (timer) return stop();
  if (index >= plies.length) gehe(0);
  wurzel.querySelector('[data-pv="play"]').setAttribute("aria-pressed", "true");
  timer = setInterval(() => { if (index >= plies.length) stop(); else gehe(index + 1); }, cfg.autoplay * 1000);
}
const aktion = {
  anfang: () => { stop(); gehe(0); }, zurueck: () => { stop(); gehe(index - 1); },
  vor: () => { stop(); gehe(index + 1); }, ende: () => { stop(); gehe(plies.length); }, play,
  drehen: () => { unten = unten === "white" ? "black" : "white"; gehe(index); },
  teilen: async (b) => {
    const url = location.href.split("#")[0] + "#partien/" + aktuell.id;
    try { await navigator.clipboard.writeText(url); b.textContent = "Kopiert ✓"; } catch (e) { prompt("Link zur Partie:", url); }
    setTimeout(() => (b.textContent = "Link kopieren"), 1800);
  },
};
wurzel.addEventListener("click", (e) => { const b = e.target.closest("button[data-pv]"); if (b) aktion[b.dataset.pv]?.(b); });

document.addEventListener("keydown", (e) => {
  if (wurzel.closest(".panel")?.hidden || e.target.matches("input, select, textarea") || e.altKey || e.ctrlKey || e.metaKey) return;
  const k = { ArrowLeft: "zurueck", ArrowRight: "vor", Home: "anfang", End: "ende", " ": "play", f: "drehen", F: "drehen" }[e.key];
  if (k) { e.preventDefault(); aktion[k](); }
});

// Wischen auf dem Brett (Handy)
let x0 = null;
$("[data-pv-brett]").addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
$("[data-pv-brett]").addEventListener("touchend", (e) => {
  if (x0 === null) return;
  const dx = e.changedTouches[0].clientX - x0; x0 = null;
  if (Math.abs(dx) > 40) aktion[dx < 0 ? "vor" : "zurueck"]();
});

// Brett neu vermessen, wenn der Reiter sichtbar wird oder sich die Größe ändert
new ResizeObserver(() => cg.redrawAll()).observe($("[data-pv-brett]"));

// Start: #partien/<id> öffnet diese Partie
const ausHash = () => { const m = location.hash.match(/^#partien\\/(\\d+)/); return m ? +m[1] : null; };
oeffne(ausHash() ?? partien[0].id, false);
window.addEventListener("hashchange", () => { const id = ausHash(); if (id && id !== aktuell?.id) oeffne(id, false); });
</script>"""
