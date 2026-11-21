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
// Mehrere Partien in einer PGN-Datei trennen
export function partien(text) {
  const t = String(text || "").replace(/\r\n?/g, "\n").replace(/^\uFEFF/, "").trim();
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

export function viewer(el) {
  if (el.__pz) el.__pz();                          // schon gebaut (Editor-Vorschau): alten Beobachter lösen
  let cfg = {};
  try { cfg = JSON.parse(el.getAttribute("data-partie")); } catch (e) { return; }
  const kopf = kopfDaten(cfg.pgn || "");
  const startFen = kopf.FEN || new Chess().fen();
  const { haupt, ergebnis, vorab } = baum(cfg.pgn || "", startFen);
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
  if (kopf.FEN) el.querySelector(".pz-li").hidden = true;

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
  el.addEventListener("keydown", (e) => {
    const k = { ArrowLeft: "zurueck", ArrowRight: "vor", Home: "anfang", End: "ende", f: "drehen" }[e.key];
    if (k) { e.preventDefault(); aktion[k](); }
  });
  let x0 = null;
  brett.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  brett.addEventListener("touchend", (e) => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 40) aktion[dx < 0 ? "vor" : "zurueck"](); });
  const ro = new ResizeObserver(() => cg.redrawAll());
  ro.observe(brett);
  el.__pz = () => { ro.disconnect(); cg.destroy(); };
  const ab = +cfg.ab || 0;
  zeige(ab < 0 ? haupt[haupt.length - 1] || null : ab ? haupt[Math.min(ab, haupt.length) - 1] : null);
}

document.querySelectorAll("[data-partie]").forEach(viewer);
