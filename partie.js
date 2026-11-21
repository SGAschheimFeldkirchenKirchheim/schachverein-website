/* SG AFK – Partie-Viewer in Berichten.
   <figure class="pz" data-partie='{"pgn":"…","ab":45,"sicht":"w"}'></figure>
   ab = Halbzug, bei dem das Brett startet (0 = Grundstellung, -1 = Schlussstellung), sicht = "w" | "b" (diese Farbe unten),
   ergebnis = "ende": Ergebnis erst nach dem letzten Zug zeigen (mit kleinem Effekt), sonst steht es oben neben den Namen.
   Wird auch vom Bericht-Editor benutzt (import("./partie.js") -> viewer, partien, lesen).
   Kommentare {…} und Varianten (…) werden angezeigt; Varianten sind anklickbar. */
import { Chessground } from "./lib/partien/chessground.min.js";
import { Chess } from "./lib/partien/chess.js";

const DEUTSCH = { S: "N", L: "B", T: "R", D: "Q" };
const ANZEIGE = { N: "S", B: "L", R: "T", Q: "D" };
const NAG = { 1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!", 10: "=", 14: "⩲", 15: "⩱", 16: "±", 17: "∓", 18: "+−", 19: "−+" };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const zeigeSan = (san) => san.replace(/[NBRQ]/g, (f) => ANZEIGE[f]);
const ERG = { "1/2-1/2": "½–½", "1-0": "1–0", "0-1": "0–1", "*": "" };

// ---------- PGN -> Baum (Hauptvariante + Varianten + Kommentare) ----------
function kopfDaten(pgn) {
  const k = {};
  pgn.replace(/^\s*\[(\w+)\s+"([^"]*)"\]\s*$/gm, (m, a, b) => (k[a] = b));
  return k;
}
function tokens(text) {
  const t = [], re = /\{([^}]*)\}|;[^\n]*|(\()|(\))|\$(\d+)|(1-0|0-1|1\/2-1\/2|\*)|(\d+\.(?:\.\.)?)|([^\s(){};$]+)/g;
  let m;
  while ((m = re.exec(text))) {
    if (m[1] !== undefined) t.push({ k: "c", v: m[1].trim() });
    else if (m[2]) t.push({ k: "(" });
    else if (m[3]) t.push({ k: ")" });
    else if (m[4]) t.push({ k: "nag", v: +m[4] });
    else if (m[5]) t.push({ k: "erg", v: m[5] });
    else if (m[6]) continue;
    else if (m[7]) {
      let s = m[7].replace(/^\d+\.+/, "");
      const suf = s.match(/[!?]+$/);
      if (suf) s = s.slice(0, -suf[0].length);
      if (s) t.push({ k: "zug", v: s, suf: suf ? suf[0] : "" });
    }
  }
  return t;
}
function baum(pgn, startFen) {
  const koerper = pgn.replace(/^\s*\[[^\]]*\]\s*$/gm, "");
  const tk = tokens(koerper);
  let i = 0, ergebnis = "";
  const vorab = [];
  function linie(fen, eltern) {
    const zuege = [], spiel = new Chess(fen);
    while (i < tk.length) {
      const t = tk[i++];
      if (t.k === ")") break;
      if (t.k === "erg") { ergebnis = t.v; continue; }
      if (t.k === "c") { if (zuege.length) zuege[zuege.length - 1].kommentar = (zuege[zuege.length - 1].kommentar ? zuege[zuege.length - 1].kommentar + " " : "") + t.v; else if (!eltern) vorab.push(t.v); else (eltern.vorKommentar = t.v); continue; }
      if (t.k === "nag") { if (zuege.length) zuege[zuege.length - 1].nag += NAG[t.v] || ""; continue; }
      if (t.k === "(") {
        const letzter = zuege[zuege.length - 1];
        if (!letzter) { tiefe(); continue; }
        const v = { };
        v.zuege = linie(letzter.fenVor, v);
        if (v.zuege.length) { v.zuege.forEach((z) => (z.linie = v.zuege)); letzter.varianten.push(v); }
        continue;
      }
      if (t.k === "zug") {
        let z = null;
        try { z = spiel.move(t.v); } catch (e) {
          try { z = spiel.move(t.v.replace(/^([SLTD])/, (m, f) => DEUTSCH[f]).replace(/=([SLTD])/, (m, f) => "=" + DEUTSCH[f])); } catch (e2) { z = null; }
        }
        if (!z) { while (i < tk.length && tk[i].k !== ")") { if (tk[i].k === "(") { i++; tiefe(); } else i++; } i++; break; }
        zuege.push({ san: z.san, from: z.from, to: z.to, fen: z.after, fenVor: z.before, nag: t.suf, kommentar: "", varianten: [],
          nr: Math.floor(spiel.moveNumber() - (z.color === "b" ? 1 : 0)), farbe: z.color });
      }
    }
    return zuege;
  }
  function tiefe() { let d = 1; while (i < tk.length && d) { if (tk[i].k === "(") d++; else if (tk[i].k === ")") d--; i++; } }
  const haupt = linie(startFen, null);
  haupt.forEach((z) => (z.linie = haupt));
  return { haupt, ergebnis, vorab: vorab.join(" ") };
}

// ---------- Viewer ----------
// Nur eine Stellung (FEN) eingefügt -> kleine PGN daraus machen
const FEN_RE = /^(?:[rnbqkpRNBQKP1-8]+\/){7}[rnbqkpRNBQKP1-8]+(?:\s+[wb](?:\s+(?:-|[KQkq]{1,4})(?:\s+(?:-|[a-h][36])(?:\s+\d+\s+\d+)?)?)?)?$/;
export function alsPgn(text) {
  const t = String(text || "").trim();
  if (!FEN_RE.test(t)) return text;
  const teile = t.split(/\s+/);
  const fen = [teile[0], teile[1] || "w", teile[2] || "-", teile[3] || "-", teile[4] || "0", teile[5] || "1"].join(" ");
  return `[SetUp "1"]\n[FEN "${fen}"]\n\n*`;
}

// Mehrere Partien in einer PGN-Datei trennen
export function partien(text) {
  const t = alsPgn(String(text || "").replace(/\r\n?/g, "\n").replace(/^\uFEFF/, "").trim());
  if (!t) return [];
  const teile = t.split(/\n\s*\n(?=\s*\[)/);
  const aus = [];
  let akt = "";
  teile.forEach((x) => {
    const nurKopf = /^\s*(\[[^\]]*\]\s*)+$/.test(x);
    if (akt && !nurKopf && /^\s*\[/.test(x) && /\]\s*$/m.test(akt) && /\d\.|\*|1-0|0-1/.test(akt.replace(/^\s*\[[^\]]*\]\s*$/gm, ""))) { aus.push(akt); akt = x; }
    else akt = akt ? akt + "\n\n" + x : x;
  });
  if (akt) aus.push(akt);
  return aus.map((p) => p.trim()).filter(Boolean);
}

// Kurzinfo zu einer PGN (für den Editor): Namen, Ergebnis, Züge der Hauptvariante, Kommentare, Varianten
export function lesen(pgn) {
  const kopf = kopfDaten(pgn);
  let startFen;
  try { startFen = kopf.FEN || new Chess().fen(); new Chess(startFen); } catch (e) { return null; }
  const b = baum(pgn, startFen);
  let kom = b.vorab ? 1 : 0, vars = 0;
  const zaehle = (l) => l.forEach((z) => { if (z.kommentar) kom++; z.varianten.forEach((v) => { vars++; zaehle(v.zuege); }); });
  zaehle(b.haupt);
  return { kopf, ergebnis: kopf.Result || b.ergebnis, zuege: b.haupt.map((z) => ({ san: z.san, nr: z.nr, farbe: z.farbe })),
    kommentare: kom, varianten: vars, startWeiss: startFen.split(" ")[1] !== "b", startNr: +startFen.split(" ")[5] || 1 };
}

let AKTIV = null;
document.addEventListener("keydown", (e) => {
  if (!AKTIV || !document.contains(AKTIV) || !AKTIV.__taste || e.ctrlKey || e.altKey || e.metaKey) return;
  const t = e.target, tag = t && t.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;   // beim Tippen nicht stören
  if (t && t.closest && t.closest(".ps-tab") && (e.key === "ArrowUp" || e.key === "ArrowDown")) return;
  AKTIV.__taste(e);
});

export function viewer(el) {
  if (el.__pz) el.__pz();                          // schon gebaut (Editor-Vorschau): alten Beobachter lösen
  let cfg = {};
  try { cfg = JSON.parse(el.getAttribute("data-partie")); } catch (e) { return; }
  const kopf = kopfDaten(cfg.pgn || "");
  const startFen = kopf.FEN || new Chess().fen();
  const { haupt, ergebnis, vorab } = baum(cfg.pgn || "", startFen);
  const diagramm = haupt.length === 0;              // nur eine Stellung (FEN) ohne Züge
  const weissZieht = startFen.split(" ")[1] !== "b";
  const erg = ERG[kopf.Result || ergebnis] ?? (kopf.Result || ergebnis || "");
  const spannung = cfg.ergebnis === "ende" && !!erg;
  let verraten = !spannung;
  const offen = (n) => n && n !== "?" && !/^(weiß|weiss|schwarz|white|black)$/i.test(n.trim());
  const kurz = (n) => (n.includes(",") ? n.split(",")[0] : n.trim().split(/\s+/).slice(-1)[0]).trim();
  const sieger = erg === "1–0" ? (offen(kopf.White) ? kurz(kopf.White) + " gewinnt" : "Weiß gewinnt")
    : erg === "0–1" ? (offen(kopf.Black) ? kurz(kopf.Black) + " gewinnt" : "Schwarz gewinnt") : erg === "½–½" ? "Remis" : "";
  let unten = cfg.sicht === "b" ? "black" : "white";
  let akt = null;                                   // aktueller Zug (Objekt) oder null = Start
  const name = (n, elo) => esc(n || "?") + (elo && elo !== "?" ? ` <span class="pz-elo">${esc(elo)}</span>` : "");
  const info = [kopf.Event, kopf.Round && kopf.Round !== "?" ? "Runde " + kopf.Round : "", kopf.Date && !/\?/.test(kopf.Date) ? kopf.Date.split(".").reverse().join(".") : ""]
    .filter((x) => x && x !== "?").join(" · ");
  const mitNamen = offen(kopf.White) || offen(kopf.Black);
  el.classList.toggle("pz-diagramm", diagramm);
  if (diagramm) {
    el.innerHTML = `
    ${mitNamen || info ? `<div class="pz-kopf">${mitNamen ? `<div class="pz-namen"><span class="pz-sp"><span class="pz-f w"></span>${name(kopf.White, kopf.WhiteElo)}</span>
      <span class="pz-gegen">–</span><span class="pz-sp"><span class="pz-f b"></span>${name(kopf.Black, kopf.BlackElo)}</span></div>` : ""}${info ? `<div class="pz-info">${esc(info)}</div>` : ""}</div>` : ""}
    <div class="pz-brettrahmen"><div class="pz-brett"></div></div>
    <div class="pz-diag-fuss"><span><span class="pz-f ${weissZieht ? "w" : "b"}"></span>${weissZieht ? "Weiß" : "Schwarz"} am Zug</span>
      <span><a class="pz-li" target="_blank" rel="noopener">Auf Lichess analysieren ↗</a>
      <button type="button" data-a="drehen" title="Brett drehen" aria-label="Brett drehen">⇅</button></span></div>`;
    const brett = el.querySelector(".pz-brett");
    const cg = Chessground(brett, { viewOnly: true, coordinates: true, fen: startFen, orientation: unten,
      turnColor: weissZieht ? "white" : "black", check: (() => { try { return new Chess(startFen).inCheck(); } catch (e) { return false; } })() });
    el.querySelector(".pz-li").href = "https://lichess.org/analysis/standard/" + startFen.replace(/ /g, "_");
    el.querySelector("[data-a=drehen]").addEventListener("click", () => { unten = unten === "white" ? "black" : "white"; cg.set({ orientation: unten }); });
    const ro = new ResizeObserver(() => cg.redrawAll());
    ro.observe(brett);
    el.__pz = () => { ro.disconnect(); cg.destroy(); };
    return;
  }
  el.innerHTML = `
    <div class="pz-kopf"><div class="pz-namen"><span class="pz-sp"><span class="pz-f w"></span>${name(kopf.White, kopf.WhiteElo)}</span>
      <span class="pz-gegen">–</span><span class="pz-sp"><span class="pz-f b"></span>${name(kopf.Black, kopf.BlackElo)}</span></div>
      ${erg ? `<b class="pz-erg"${spannung ? " hidden" : ""}>${esc(erg)}</b>` : ""}${info ? `<div class="pz-info">${esc(info)}</div>` : ""}</div>
    <div class="pz-rumpf">
      <div class="pz-links"><div class="pz-brettrahmen"><div class="pz-brett"></div>
        ${spannung ? `<div class="pz-auf" hidden><b>${esc(erg)}</b><span>${esc(sieger)}</span></div>` : ""}</div>
        <div class="pz-knoepfe" role="toolbar" aria-label="Partie steuern">
          <button type="button" data-a="anfang" title="Anfang" aria-label="Anfang">⏮</button>
          <button type="button" data-a="zurueck" title="Zurück (←)" aria-label="Zurück">◀</button>
          <button type="button" data-a="vor" title="Vor (→)" aria-label="Vor">▶</button>
          <button type="button" data-a="ende" title="Ende" aria-label="Ende">⏭</button>
          <button type="button" data-a="drehen" title="Brett drehen" aria-label="Brett drehen">⇅</button>
        </div></div>
      <div class="pz-rechts"><div class="pz-zuege" tabindex="0" aria-label="Züge"></div>
        <div class="pz-aktionen"><a class="pz-dl" download>PGN herunterladen</a><a class="pz-li" target="_blank" rel="noopener">Auf Lichess analysieren ↗</a></div></div>
    </div>`;
  const brett = el.querySelector(".pz-brett"), liste = el.querySelector(".pz-zuege");
  const cg = Chessground(brett, { viewOnly: true, coordinates: true, animation: { duration: 160 } });
  const dl = el.querySelector(".pz-dl");
  dl.href = "data:application/x-chess-pgn;charset=utf-8," + encodeURIComponent(cfg.pgn || "");
  dl.download = ((kopf.White || "Weiss") + " - " + (kopf.Black || "Schwarz")).replace(/[\\/:*?"<>|]/g, "") + ".pgn";
  el.querySelector(".pz-li").href = "https://lichess.org/analysis/pgn/" +
    encodeURIComponent(haupt.map((z, i) => (z.farbe === "w" ? z.nr + ". " : i === 0 ? z.nr + "... " : "") + z.san).join(" "));
  if (kopf.FEN) el.querySelector(".pz-li").href = "https://lichess.org/analysis/standard/" + startFen.replace(/ /g, "_");

  // Zugliste: Hauptvariante fett, Varianten in Klammern darunter
  const alle = [];
  function zugHtml(z, mitNr) {
    alle.push(z); const id = alle.length - 1;
    const nr = z.farbe === "w" ? `${z.nr}. ` : mitNr ? `${z.nr}… ` : "";
    return `<button type="button" data-z="${id}">${nr}${esc(zeigeSan(z.san))}${esc(z.nag)}</button>`;
  }
  function linieHtml(zuege, haupt_) {
    let h = "", nrNoetig = true;
    zuege.forEach((z) => {
      h += zugHtml(z, nrNoetig) + " ";
      nrNoetig = false;
      if (z.kommentar) { h += `<span class="pz-kom">${esc(z.kommentar)}</span> `; nrNoetig = true; }
      z.varianten.forEach((v) => { h += `<span class="pz-var">(${linieHtml(v.zuege, false).trim()})</span> `; nrNoetig = true; });
    });
    return h;
  }
  liste.innerHTML = (vorab ? `<p class="pz-kom">${esc(vorab)}</p>` : "") + `<div class="pz-haupt">${linieHtml(haupt, true)}</div>` +
    (erg ? `<div class="pz-ende"${spannung ? " hidden" : ""}>${esc(erg)}</div>` : "");

  function zeige(z) {
    akt = z;
    const anzahl = z ? z.linie.indexOf(z) : -1;
    cg.set({ fen: z ? z.fen : startFen, orientation: unten, lastMove: z ? [z.from, z.to] : undefined,
      check: !!(z && /[+#]$/.test(z.san)), turnColor: z ? (z.farbe === "w" ? "black" : "white") : (startFen.split(" ")[1] === "b" ? "black" : "white") });
    liste.querySelectorAll("[aria-current]").forEach((b) => b.removeAttribute("aria-current"));
    if (spannung) {                               // Ergebnis-Auflösung beim letzten Zug
      const amEnde = !!z && z === haupt[haupt.length - 1];
      const auf = el.querySelector(".pz-auf");
      auf.hidden = !amEnde;
      if (amEnde) { auf.classList.remove("an"); void auf.offsetWidth; auf.classList.add("an"); }
      if (amEnde) el.dispatchEvent(new CustomEvent("pz-ende"));
      if (amEnde && !verraten) {
        verraten = true;
        el.querySelectorAll(".pz-erg, .pz-ende").forEach((x) => { x.hidden = false; x.classList.add("pz-neu"); });
      }
    }
    if (z) {
      const b = liste.querySelector(`[data-z="${alle.indexOf(z)}"]`);
      if (b) {
        b.setAttribute("aria-current", "true");
        const o = b.offsetTop - liste.offsetTop;
        if (o < liste.scrollTop || o > liste.scrollTop + liste.clientHeight - 30) liste.scrollTop = o - liste.clientHeight / 2;
      }
    }
  }
  // Variante verlassen: "zurück" am Anfang einer Variante springt zum Zug davor in der Elternlinie
  function vorher(z) {
    if (!z) return null;
    const i = z.linie.indexOf(z);
    if (i > 0) return z.linie[i - 1];
    if (z.linie === haupt) return null;
    for (const x of alle) for (const v of x.varianten) if (v.zuege === z.linie) return x.linie[x.linie.indexOf(x) - 1] || null;
    return null;
  }
  const aktion = {
    anfang: () => zeige(null),
    zurueck: () => zeige(vorher(akt)),
    vor: () => { const l = akt ? akt.linie : haupt, i = akt ? l.indexOf(akt) : -1; if (l[i + 1]) zeige(l[i + 1]); },
    ende: () => { const l = akt ? akt.linie : haupt; zeige(l[l.length - 1] || null); },
    drehen: () => { unten = unten === "white" ? "black" : "white"; zeige(akt); },
  };
  el.addEventListener("click", (e) => {
    if (e.target.closest(".pz-auf")) { e.target.closest(".pz-auf").hidden = true; return; }
    const b = e.target.closest("[data-a]"); if (b) return aktion[b.dataset.a]();
    const z = e.target.closest("[data-z]"); if (z) zeige(alle[+z.dataset.z]);
  });
  el.tabIndex = 0;
  // Pfeiltasten: steuern das Brett, mit dem man zuletzt etwas gemacht hat (oder das einzige auf der Seite)
  el.__taste = (e) => {
    const k = { ArrowLeft: "zurueck", ArrowRight: "vor", Home: "anfang", End: "ende", f: "drehen" }[e.key];
    if (k) { e.preventDefault(); aktion[k](); }
  };
  ["pointerdown", "focusin", "mouseenter"].forEach((n) => el.addEventListener(n, () => { AKTIV = el; }));
  if (!AKTIV || !document.contains(AKTIV) || el.closest(".be-dlg")) AKTIV = el;
  let x0 = null;
  brett.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  brett.addEventListener("touchend", (e) => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 40) aktion[dx < 0 ? "vor" : "zurueck"](); });
  const ro = new ResizeObserver(() => cg.redrawAll());
  ro.observe(brett);
  el.__pz = () => { ro.disconnect(); cg.destroy(); };
  const ab = +cfg.ab || 0;
  zeige(ab < 0 ? haupt[haupt.length - 1] || null : ab ? haupt[Math.min(ab, haupt.length) - 1] : null);
}

// ---------- Sammlung: mehrere Partien, eine Tabelle, ein Brett ----------
// <div class="ps" data-sammlung='{"pgn":"…mehrere Partien…","ergebnis":"ende"}'></div>
const EIGEN = /afk|aschheim|feldkirchen|kirchheim/i;          // unser Verein (für "unser Spieler unten")
export function sammlung(box) {
  let cfg = {};
  try { cfg = JSON.parse(box.getAttribute("data-sammlung")); } catch (e) { return; }
  const pgns = partien(cfg.pgn).filter((p) => { const i = lesen(p); return i && (i.zuege.length || i.kopf.FEN); });
  if (!pgns.length) return;
  const infos = pgns.map(lesen), spannung = cfg.ergebnis === "ende";
  const teams = new Set();
  infos.forEach((i) => { if (i.kopf.WhiteTeam) teams.add(i.kopf.WhiteTeam); if (i.kopf.BlackTeam) teams.add(i.kopf.BlackTeam); });
  const tl = [...teams];
  const wir = tl.length === 2 ? (tl.find((t) => EIGEN.test(t)) || infos[0].kopf.WhiteTeam) : "";
  const die = wir ? tl.find((t) => t !== wir) : "";
  const PUNKTE = { "1-0": [1, 0], "0-1": [0, 1], "1/2-1/2": [.5, .5] };
  let stand = wir ? [0, 0] : null, offen = false;
  infos.forEach((i) => {
    const p = PUNKTE[i.kopf.Result || i.ergebnis];
    if (!p) { offen = true; return; }
    if (stand) { const w = i.kopf.WhiteTeam === wir; stand[0] += w ? p[0] : p[1]; stand[1] += w ? p[1] : p[0]; }
  });
  const zahl = (x) => (x === .5 ? "½" : String(x).replace(".5", "½"));
  const ergText = (i) => ERG[i.kopf.Result || i.ergebnis] || "–";
  const gesehen = new Set();
  const kurzName = (n) => { n = String(n || "?"); if (n.includes(",")) { const [a, b] = n.split(","); return a.trim() + (b && b.trim() ? ", " + b.trim()[0] + "." : ""); }
    const t = n.trim().split(/\s+/); return t.length > 1 ? t[t.length - 1] + ", " + t[0][0] + "." : n; };
  const k0 = infos[0].kopf;
  const titel = wir ? esc(wir) + " – " + esc(die) : esc(k0.Event && k0.Event !== "?" ? k0.Event : "Partien");
  const unter = [wir && k0.Event && k0.Event !== "?" ? k0.Event : "", k0.Round && k0.Round !== "?" ? "Runde " + k0.Round : ""].filter(Boolean).join(" · ");
  let aktiv = 0;
  const m = location.hash.match(/^#brett-(\d+)$/);
  if (m && !document.querySelector(".ps[data-brett-ziel]")) { box.dataset.brettZiel = "1"; aktiv = Math.min(+m[1] - 1, pgns.length - 1); }

  function standHtml() {
    if (!stand) return "";
    if (spannung && gesehen.size < pgns.length) return '<span class="ps-stand zu">? : ?</span>';
    return `<span class="ps-stand${spannung ? " pz-neu" : ""}">${zahl(stand[0])} : ${zahl(stand[1])}${offen ? ' <small>(läuft)</small>' : ""}</span>`;
  }
  function zeile(i, j) {
    const k = i.kopf, wert = (e) => (e && e !== "?" && e !== "0" ? `<span class="ps-elo">${esc(e)}</span>` : "");
    const name = (n, t) => `<span class="ps-name${wir && t === wir ? " eigen" : ""}"><span class="ps-lang">${esc(n || "?")}</span><span class="ps-kurz">${esc(kurzName(n))}</span></span>`;
    const erg = spannung && !gesehen.has(j) ? '<td class="ps-erg zu">?</td>' : `<td class="ps-erg">${esc(ergText(i))}</td>`;
    return `<tr data-j="${j}"${j === aktiv ? ' class="an" aria-current="true"' : ""} tabindex="0"><td class="ps-nr">${esc(k.Board || j + 1)}</td>
      <td><span class="pz-f w"></span>${name(k.White, k.WhiteTeam)}${wert(k.WhiteElo)}</td>
      <td><span class="pz-f b"></span>${name(k.Black, k.BlackTeam)}${wert(k.BlackElo)}</td>${erg}</tr>`;
  }
  function zeichnen() {
    box.innerHTML = `<div class="ps-kopf"><div><h3>${titel}</h3>${unter ? `<span class="klein">${esc(unter)}</span>` : ""}</div><div class="ps-standplatz">${standHtml()}</div></div>
      <div class="ps-tabrahmen"><table class="ps-tab">${infos.map(zeile).join("")}</table></div>
      <div class="ps-brett"></div>
      <div class="ps-nav"><button type="button" data-n="${aktiv - 1}"${aktiv ? "" : " hidden"}>← Brett ${esc(infos[aktiv - 1] ? infos[aktiv - 1].kopf.Board || aktiv : "")}</button>
        <button type="button" data-n="${aktiv + 1}"${aktiv < pgns.length - 1 ? "" : " hidden"}>Brett ${esc(infos[aktiv + 1] ? infos[aktiv + 1].kopf.Board || aktiv + 2 : "")} →</button></div>`;
    const k = infos[aktiv].kopf;
    const sicht = wir && k.BlackTeam === wir ? "b" : "w";
    const fig = document.createElement("figure");
    fig.className = "pz";
    fig.setAttribute("data-partie", JSON.stringify({ pgn: pgns[aktiv], ab: 0, sicht, ergebnis: spannung ? "ende" : "" }));
    box.querySelector(".ps-brett").appendChild(fig);
    if (spannung) fig.addEventListener("pz-ende", () => {     // Partie zu Ende geklickt -> Ergebnis in der Tabelle aufdecken
      if (gesehen.has(aktiv)) return;
      gesehen.add(aktiv);
      const td = box.querySelector(`tr[data-j="${aktiv}"] .ps-erg`);
      td.outerHTML = `<td class="ps-erg"><span class="pz-neu">${esc(ergText(infos[aktiv]))}</span></td>`;
      box.querySelector(".ps-standplatz").innerHTML = standHtml();
    });
    viewer(fig);
  }
  function waehle(j) { if (j < 0 || j >= pgns.length) return; aktiv = j; zeichnen(); box.querySelector("tr.an").focus({ preventScroll: true }); }
  box.addEventListener("click", (e) => {
    const r = e.target.closest("tr[data-j]"); if (r) return waehle(+r.dataset.j);
    const n = e.target.closest("[data-n]"); if (n) { waehle(+n.dataset.n); box.scrollIntoView({ behavior: "smooth", block: "start" }); }
  });
  box.addEventListener("keydown", (e) => {
    const r = e.target.closest("tr[data-j]");
    if (r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); waehle(+r.dataset.j); }
    if (r && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); waehle(+r.dataset.j + (e.key === "ArrowDown" ? 1 : -1)); }
  });
  zeichnen();
  if (box.dataset.brettZiel) box.scrollIntoView({ block: "start" });
}

document.querySelectorAll("[data-partie]").forEach(viewer);
document.querySelectorAll("[data-sammlung]").forEach(sammlung);
