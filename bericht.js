/* SG AFK – Bericht-Editor auf berichte.html (Backend: AppsScript/Berichte.gs)
   Editor-Schreibweise: *fett*, _kursiv_, "= Überschrift", "- Punkt", [Text](https://...), [Bild 2] als eigene Zeile. */
(function () {
  "use strict";
  var APP = document.getElementById("be-app");
  if (!APP) return;
  var DETAILS = document.getElementById("einreichen");
  var SKRIPT = APP.getAttribute("data-skript"), MAX = +APP.getAttribute("data-max") || 20000;
  var KATEGORIEN = JSON.parse(APP.getAttribute("data-kat") || "[]");
  var SPEICHER = "afk-bericht-entwurf2", MAX_BILDER = 12, BILD_PX = 1600;
  var ICH = null;                              // angemeldetes Mitglied (aus konto.js) oder null
  var Z = { id: null, bilder: [], titelbild: 0, kat: [], partien: [], eintrag: null };
  var MAX_PARTIEN = 10;
  var BASIS = (document.currentScript && document.currentScript.src || "").replace(/[^\/]*$/, "");
  var MODUL = null;
  function partieModul() {                      // partie.js + Brett-Bibliothek erst laden, wenn sie gebraucht werden
    if (!MODUL) {
      ["chessground.base.css", "chessground.cburnett.css"].forEach(function (f) {
        var l = document.createElement("link"); l.rel = "stylesheet"; l.href = BASIS + "lib/partien/" + f; document.head.appendChild(l);
      });
      MODUL = import(BASIS + "partie.js");
    }
    return MODUL;
  }

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function $(sel) { return APP.querySelector(sel); }
  function token() { try { return localStorage.getItem("afk-sitzung") || ""; } catch (e) { return ""; } }
  function api(typ, d) {
    d = d || {}; d.typ = typ;
    if (token()) d.sitzung = token();
    return fetch(SKRIPT, { method: "POST", body: JSON.stringify(d) }).then(function (r) { return r.json(); })
      .catch(function () { return { ok: false, fehler: "Keine Verbindung – bitte später nochmal" }; });
  }
  function heute() { var d = new Date(); return ("0" + d.getDate()).slice(-2) + "." + ("0" + (d.getMonth() + 1)).slice(-2) + "." + d.getFullYear(); }
  function isoDatum(s) { var m = String(s).trim().match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/); return m ? m[3] + "-" + ("0" + m[2]).slice(-2) + "-" + ("0" + m[1]).slice(-2) : ""; }
  function deDatum(iso) { var m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[3] + "." + m[2] + "." + m[1] : iso; }
  // Ziffern -> TT.MM.JJJJ (Punkte kommen von selbst, z. B. für Handy-Tastaturen ohne Punkt)
  function datumFormat(el) {
    el.addEventListener("input", function () {
      var z = el.value.replace(/\D/g, "").slice(0, 8), t = z;
      if (/^\d{1,2}\.\d{1,2}\.\d{0,4}$/.test(el.value)) return;
      if (z.length > 4) t = z.slice(0, 2) + "." + z.slice(2, 4) + "." + z.slice(4);
      else if (z.length > 2) t = z.slice(0, 2) + "." + z.slice(2);
      el.value = t;
    });
  }

  // ---------- Vorschau: Editor-Schreibweise -> HTML ----------
  function inline(s) {
    s = esc(s);
    s = s.replace(/\[([^\]\n]{1,200})\]\((https?:\/\/[^)\s]+|mailto:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    s = s.replace(/\*([^*\n]+)\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^\w])_([^_\n]+)_(?!\w)/g, "$1<em>$2</em>");
    return s;
  }
  function vorschauHtml(text) {
    var out = [], para = [], items = [], tag = null;
    function flush() {
      if (para.length) { out.push("<p>" + para.map(inline).join("<br>") + "</p>"); para = []; }
      if (items.length) { out.push("<" + tag + ">" + items.map(function (i) { return "<li>" + inline(i) + "</li>"; }).join("") + "</" + tag + ">"); items = []; tag = null; }
    }
    String(text).split("\n").forEach(function (z) {
      var l = z.trim(), m;
      if (!l) return flush();
      if ((m = l.match(/^\[Bild (\d+)\]$/))) {
        flush(); var b = Z.bilder[+m[1] - 1];
        if (b) out.push('<figure><img src="' + esc(b.daten || b.url) + '" alt="">' + (b.unterschrift ? "<figcaption>" + esc(b.unterschrift) + "</figcaption>" : "") + "</figure>");
        return;
      }
      if ((m = l.match(/^\[Partie (\d+)\]$/))) {
        flush(); var p = Z.partien[+m[1] - 1];
        if (p) out.push('<figure class="pz" data-partie="' + esc(JSON.stringify(p)) + '"></figure>');
        return;
      }
      if ((m = l.match(/^\[Tabelle (\S+)\]$/))) {
        flush(); out.push('<p class="cr-platzhalter">Tabelle von chess-results – wird beim nächsten Build geladen.<br><a href="' + esc(m[1]) + '" target="_blank" rel="noopener">' + esc(m[1]) + "</a></p>");
        return;
      }
      if ((m = l.match(/^(={1,3})\s+(.*)$/))) { flush(); var h = m[1].length + 1; out.push("<h" + h + ">" + inline(m[2]) + "</h" + h + ">"); return; }
      if ((m = l.match(/^(?:(\d+\.)|([-+]))\s+(.*)$/))) { var t = m[2] ? "ul" : "ol"; if (para.length || (tag && tag !== t)) flush(); tag = t; items.push(m[3]); return; }
      if (items.length) flush();
      para.push(l);
    });
    flush();
    return out.join("");
  }

  // ---------- Typst (vorhandener Bericht) -> Editor-Schreibweise ----------
  function ausTypst(typ, dateien, pgnDateien) {
    var partien = [];
    function meta(n) { var m = typ.match(new RegExp("#" + n + "\\[(.*?)\\]")); return m ? m[1].trim() : ""; }
    var tb = (typ.match(/^\/\/\s*titelbild:\s*(\S+)/m) || [])[1] || "";
    var bilder = [], namen = {};
    function bildNr(name, alt) {
      if (!(name in namen)) {
        var d = dateien.filter(function (x) { return x.name === name; })[0];
        if (!d) return null;
        bilder.push({ name: name, url: d.url, unterschrift: alt || "" }); namen[name] = bilder.length;
      }
      return namen[name];
    }
    var zeilen = [], fehlt = false;
    typ.split("\n").forEach(function (z) {
      var l = z.replace(/​/g, "");
      if (/^\s*#(import|title|date|author|kategorie|set|show|let)\b/.test(l) || /^\s*\/\//.test(l)) return;
      var im = l.trim().match(/^#image\(\s*"([^"]+)"\s*(?:,\s*alt:\s*"([^"]*)")?[^)]*\)\s*$/);
      if (im) { var n = bildNr(im[1], im[2]); if (n) zeilen.push("[Bild " + n + "]"); else fehlt = true; return; }
      var pm = l.trim().match(/^#partie\(\s*"([^"]+)"(.*)\)\s*$/);
      if (pm) {
        var datei = (pgnDateien || []).filter(function (x) { return x.name === pm[1]; })[0];
        if (!datei) { fehlt = true; return; }
        var abm = pm[2].match(/ab:\s*(-?\d+)/), sm = pm[2].match(/sicht:\s*"(\w)"/);
        partien.push({ pgn: datei.pgn.trim(), ab: abm ? +abm[1] : 0, sicht: sm && sm[1] === "b" ? "b" : "w" });
        zeilen.push("[Partie " + partien.length + "]"); return;
      }
      var tm = l.trim().match(/^#tabelle\(\s*"([^"]+)"\s*\)\s*$/);
      if (tm) { zeilen.push("[Tabelle " + tm[1] + "]"); return; }
      l = l.replace(/\s*\\$/, "");
      l = l.replace(/#link\("([^"]+)"\)\[([^\]]*)\]/g, "[$2]($1)").replace(/#strong\[([^\]]*)\]/g, "*$1*").replace(/#emph\[([^\]]*)\]/g, "_$1_");
      if (/(^|[^\\])#[a-z]/i.test(l)) fehlt = true;
      zeilen.push(l.replace(/\\(.)/g, "$1"));
    });
    dateien.forEach(function (d) { bildNr(d.name, ""); });          // Bilder im Ordner, die (noch) nicht im Text stehen
    var kat = meta("kategorie");
    return {
      ok: !fehlt, titel: meta("title"), datum: meta("date"), autor: meta("author"),
      kat: kat ? kat.split(",").map(function (k) { return k.trim().toLowerCase(); }) : [],
      text: zeilen.join("\n").replace(/^\n+|\n+$/g, "").replace(/\n{3,}/g, "\n\n"),
      bilder: bilder, titelbild: Math.max(0, tb ? bilder.map(function (b) { return b.name; }).indexOf(tb) : 0), partien: partien
    };
  }

  // ---------- Bilder ----------
  function verkleinern(datei) {
    function zeichnen(q, w, h) {
      var s = Math.min(1, BILD_PX / Math.max(w, h)), c = document.createElement("canvas");
      c.width = Math.round(w * s); c.height = Math.round(h * s);
      c.getContext("2d").drawImage(q, 0, 0, c.width, c.height);
      return c.toDataURL("image/jpeg", 0.84);
    }
    if (window.createImageBitmap) return createImageBitmap(datei, { imageOrientation: "from-image" }).then(function (b) { return zeichnen(b, b.width, b.height); });
    return new Promise(function (ok, nein) {
      var img = new Image(); img.onload = function () { ok(zeichnen(img, img.naturalWidth, img.naturalHeight)); }; img.onerror = nein;
      img.src = URL.createObjectURL(datei);
    });
  }
  function bilderDazu(dateien) {
    var liste = [].slice.call(dateien || []).filter(function (f) { return /^image\//.test(f.type); });
    if (!liste.length) return;
    meldung("Fotos werden vorbereitet …", "");
    var kette = Promise.resolve();
    liste.forEach(function (f) {
      kette = kette.then(function () {
        if (Z.bilder.length >= MAX_BILDER) return;
        return verkleinern(f).then(function (url) { Z.bilder.push({ daten: url, unterschrift: "" }); });
      });
    });
    kette.then(function () { bilderZeichnen(); merken(); meldung(Z.bilder.length >= MAX_BILDER ? "Höchstens " + MAX_BILDER + " Fotos." : "", ""); })
      .catch(function () { meldung("Ein Foto konnte nicht gelesen werden.", "fehler"); });
  }
  function nummernAnpassen(weg) {                  // [Bild n] im Text nachziehen, wenn ein Bild entfernt wird
    var t = $(".be-text");
    t.value = t.value.split("\n").filter(function (z) { return z.trim() !== "[Bild " + (weg + 1) + "]"; }).join("\n")
      .replace(/\[Bild (\d+)\]/g, function (a, n) { return +n > weg + 1 ? "[Bild " + (n - 1) + "]" : a; });
  }
  function einfuegen(text) {
    var t = $(".be-text"), a = t.selectionStart, vor = t.value.slice(0, a), nach = t.value.slice(t.selectionEnd);
    var davor = vor && !/\n\n$/.test(vor) ? (/\n$/.test(vor) ? "\n" : "\n\n") : "";
    var danach = nach && !/^\n/.test(nach) ? "\n\n" : "\n";
    t.value = vor + davor + text + danach + nach;
    t.selectionStart = t.selectionEnd = (vor + davor + text + danach).length;
    t.focus(); merken();
  }
  function bilderZeichnen() {
    var box = $(".be-bilder");
    box.innerHTML = Z.bilder.map(function (b, i) {
      return '<div class="be-bild" data-i="' + i + '"><img src="' + esc(b.daten || b.url) + '" alt="">' +
        (i === Z.titelbild ? '<span class="be-titel">Titelbild</span>' : "") + '<span class="be-nr">' + (i + 1) + "</span>" +
        '<input type="text" placeholder="Bildunterschrift" maxlength="200" value="' + esc(b.unterschrift) + '">' +
        '<div class="be-akt">' + (i === Z.titelbild ? "" : '<button type="button" data-b="titel">Titelbild</button>') +
        '<button type="button" data-b="ein">Einfügen</button><button type="button" class="rot" data-b="weg" title="Entfernen">Weg</button></div></div>';
    }).join("") + (Z.bilder.length < MAX_BILDER ? '<label class="be-drop">Fotos hierher ziehen<br>oder antippen zum Auswählen<input type="file" accept="image/*" multiple hidden></label>' : "");
    [].forEach.call(box.querySelectorAll(".be-bild"), function (el) {
      var i = +el.getAttribute("data-i");
      el.querySelector("input").addEventListener("input", function (ev) { Z.bilder[i].unterschrift = ev.target.value; merken(); });
      [].forEach.call(el.querySelectorAll("[data-b]"), function (k) {
        k.addEventListener("click", function () {
          var was = k.getAttribute("data-b");
          if (was === "titel") Z.titelbild = i;
          if (was === "ein") return einfuegen("[Bild " + (i + 1) + "]");
          if (was === "weg") {
            nummernAnpassen(i); Z.bilder.splice(i, 1);
            if (Z.titelbild >= Z.bilder.length || Z.titelbild === i) Z.titelbild = 0; else if (Z.titelbild > i) Z.titelbild--;
          }
          bilderZeichnen(); merken();
        });
      });
    });
    var drop = box.querySelector(".be-drop");
    if (drop) {
      drop.querySelector("input").addEventListener("change", function (ev) { bilderDazu(ev.target.files); ev.target.value = ""; });
      ["dragenter", "dragover"].forEach(function (n) { drop.addEventListener(n, function (ev) { ev.preventDefault(); drop.classList.add("ueber"); }); });
      ["dragleave", "drop"].forEach(function (n) { drop.addEventListener(n, function () { drop.classList.remove("ueber"); }); });
      drop.addEventListener("drop", function (ev) { ev.preventDefault(); bilderDazu(ev.dataTransfer.files); });
    }
  }


  // ---------- Partien ----------
  function partieText(p, info) {
    if (!info) return "Partie";
    var k = info.kopf;
    return (k.White || "?") + " – " + (k.Black || "?") + (info.ergebnis && info.ergebnis !== "*" ? " " + info.ergebnis.replace("1/2-1/2", "½–½").replace("-", "–") : "");
  }
  function startText(p, info) {
    if (!p.ab) return "Grundstellung";
    if (p.ab < 0 || !info || p.ab >= info.zuege.length) return "Schlussstellung";
    var z = info.zuege[p.ab];
    return "ab " + z.nr + ". Zug, " + (z.farbe === "w" ? "Weiß" : "Schwarz") + " am Zug";
  }
  function partienZeichnen() {
    var box = $(".be-partien");
    if (!box) return;
    if (!Z.partien.length) { box.innerHTML = ""; return; }
    box.innerHTML = "<h4>Partien</h4>" + Z.partien.map(function (p, i) {
      return '<div class="be-partie" data-i="' + i + '"><span class="be-nr">' + (i + 1) + '</span><span class="be-p-text">Partie ' + (i + 1) + "</span>" +
        '<span class="be-p-akt"><button type="button" data-p="ein">Einfügen</button><button type="button" data-p="bearb">Bearbeiten</button>' +
        '<button type="button" class="rot" data-p="weg">Weg</button></span></div>';
    }).join("");
    partieModul().then(function (P) {
      [].forEach.call(box.querySelectorAll(".be-partie"), function (el) {
        var p = Z.partien[+el.getAttribute("data-i")], info = P.lesen(p.pgn);
        el.querySelector(".be-p-text").innerHTML = "<b>" + esc(partieText(p, info)) + '</b> <span class="klein">' + esc(startText(p, info)) + "</span>";
      });
    });
    [].forEach.call(box.querySelectorAll("[data-p]"), function (k) {
      k.addEventListener("click", function () {
        var i = +k.closest(".be-partie").getAttribute("data-i"), was = k.getAttribute("data-p");
        if (was === "ein") return einfuegen("[Partie " + (i + 1) + "]");
        if (was === "bearb") return partieDialog(i);
        if (!confirm("Partie " + (i + 1) + " entfernen?")) return;
        var t = $(".be-text");
        t.value = t.value.split("\n").filter(function (z) { return z.trim() !== "[Partie " + (i + 1) + "]"; }).join("\n")
          .replace(/\[Partie (\d+)\]/g, function (a, n) { return +n > i + 1 ? "[Partie " + (n - 1) + "]" : a; });
        Z.partien.splice(i, 1); partienZeichnen(); merken();
      });
    });
  }

  function dialog(html) {
    var hg = document.createElement("div");
    hg.className = "be-dlg-hg";
    hg.innerHTML = '<div class="be-dlg" role="dialog" aria-modal="true">' + html + "</div>";
    document.body.appendChild(hg);
    document.body.classList.add("be-dlg-offen");
    function zu() { hg.remove(); document.body.classList.remove("be-dlg-offen"); document.removeEventListener("keydown", taste); }
    function taste(ev) { if (ev.key === "Escape") zu(); }
    document.addEventListener("keydown", taste);
    hg.addEventListener("mousedown", function (ev) { if (ev.target === hg) zu(); });
    [].forEach.call(hg.querySelectorAll("[data-zu]"), function (b) { b.addEventListener("click", zu); });
    return { el: hg.firstChild, zu: zu };
  }

  function namensgleich(a, b) {               // "Ruff, Korbinian" == "Korbinian Ruff"
    function n(x) { return String(x || "").toLowerCase().replace(/[^a-zäöüß ,]/g, "").split(/[ ,]+/).filter(Boolean).sort().join(" "); }
    return !!a && !!b && n(a) === n(b);
  }

  function partieDialog(index) {
    if (index === null && Z.partien.length >= MAX_PARTIEN) return meldung("Höchstens " + MAX_PARTIEN + " Partien pro Bericht.", "fehler");
    var alt = index === null ? null : Z.partien[index];
    var nummer = index === null ? Z.partien.length + 1 : index + 1;
    var d = dialog('<h3>' + (alt ? "Partie " + nummer + " bearbeiten" : "Partie einfügen") + '</h3>' +
      '<label>PGN hier einfügen (aus Lichess, ChessBase, chess.com …)<textarea class="be-pgn" spellcheck="false" placeholder="[White &quot;…&quot;]&#10;[Black &quot;…&quot;]&#10;&#10;1. e4 e5 2. Sf3 …"></textarea></label>' +
      '<p class="be-dlg-zeile"><label class="be-datei">oder .pgn-Datei wählen<input type="file" accept=".pgn,text/plain,application/x-chess-pgn" hidden></label></p>' +
      '<div class="be-auswahl" hidden></div><p class="be-erkannt klein"></p>' +
      '<div class="be-optionen" hidden><label>Brett startet bei</label><div class="be-kat be-start">' +
      '<button type="button" data-s="grund">Grundstellung</button><button type="button" data-s="zug">ab Zug …</button><button type="button" data-s="ende">Schlussstellung</button></div>' +
      '<div class="be-ab" hidden>Zug <input type="number" min="1" class="be-zugnr" inputmode="numeric"> <div class="be-kat be-farbe"><button type="button" data-f="w">Weiß am Zug</button><button type="button" data-f="b">Schwarz am Zug</button></div></div>' +
      '<label>Diese Farbe steht unten</label><div class="be-kat be-sicht"><button type="button" data-v="w">Weiß</button><button type="button" data-v="b">Schwarz</button></div>' +
      '<div class="be-dlg-vorschau"></div></div>' +
      '<div class="be-dlg-fuss"><button type="button" class="btn leise" data-zu>Abbrechen</button><button type="button" class="btn be-ok" disabled>' +
      (alt ? "Übernehmen" : "Als [Partie " + nummer + "] einfügen") + "</button></div>");
    var el = d.el, ta = el.querySelector(".be-pgn");
    var S = { spiele: [], wahl: [], start: "grund", zug: 1, farbe: "w", sicht: "w", info: null };
    if (alt) { ta.value = alt.pgn; S.sicht = alt.sicht; }

    partieModul().then(function (P) {
      function ab() {                              // Einstellungen -> Halbzug
        if (S.start === "grund" || !S.info) return 0;
        if (S.start === "ende") return -1;
        var z = S.info.zuege, i;
        for (i = 0; i < z.length; i++) if (z[i].nr > S.zug || (z[i].nr === S.zug && (S.farbe === "w" || z[i].farbe === "b"))) break;
        return Math.min(i, z.length);
      }
      function knoepfe(sel, attr, wert) { [].forEach.call(el.querySelectorAll(sel + " button"), function (b) { b.classList.toggle("an", b.getAttribute(attr) === wert); }); }
      function zeichnen() {
        var gewaehlt = S.spiele.filter(function (x, i) { return S.wahl[i]; });
        var info = S.info = gewaehlt.length ? P.lesen(gewaehlt[0]) : null;
        var ok = !!(info && info.zuege.length);
        var e = el.querySelector(".be-erkannt");
        if (!ta.value.trim()) e.textContent = "";
        else if (!S.spiele.length || !ok) { e.textContent = "Keine Züge erkannt – ist das eine PGN?"; e.className = "be-erkannt klein fehler"; }
        else {
          e.className = "be-erkannt klein gut";
          e.textContent = gewaehlt.length > 1 ? gewaehlt.length + " Partien ausgewählt – sie werden einzeln eingefügt, die Einstellungen gelten für alle."
            : "Erkannt: " + partieText(null, info) + ", " + Math.ceil(info.zuege.length / 2) + " Züge" +
              (info.kommentare ? ", " + info.kommentare + " Kommentar" + (info.kommentare > 1 ? "e" : "") : "") +
              (info.varianten ? ", " + info.varianten + " Variante" + (info.varianten > 1 ? "n" : "") : "");
        }
        el.querySelector(".be-optionen").hidden = !ok;
        el.querySelector(".be-ok").disabled = !ok;
        knoepfe(".be-start", "data-s", S.start); knoepfe(".be-farbe", "data-f", S.farbe); knoepfe(".be-sicht", "data-v", S.sicht);
        el.querySelector(".be-ab").hidden = S.start !== "zug";
        el.querySelector(".be-zugnr").value = S.zug;
        var v = el.querySelector(".be-dlg-vorschau");
        if (ok) {
          v.innerHTML = '<figure class="pz" data-partie="' + esc(JSON.stringify({ pgn: gewaehlt[0], ab: ab(), sicht: S.sicht })) + '"></figure>';
          P.viewer(v.firstChild);
        } else v.innerHTML = "";
      }
      function seiteRaten() {                         // eigene Partie mit Schwarz -> Schwarz unten
        var g = S.spiele.filter(function (x, i) { return S.wahl[i]; });
        var inf = g.length === 1 && ICH ? P.lesen(g[0]) : null;
        if (!inf) return;
        if (namensgleich(inf.kopf.Black, ICH.ich.name)) S.sicht = "b";
        else if (namensgleich(inf.kopf.White, ICH.ich.name)) S.sicht = "w";
      }
      function einlesen(neuGelesen) {
        S.spiele = P.partien(ta.value).filter(function (x) { var i = P.lesen(x); return i && i.zuege.length; });
        if (!S.spiele.length && ta.value.trim()) S.spiele = [ta.value.trim()];
        S.wahl = S.spiele.map(function (x, i) { return i === 0; });
        var aw = el.querySelector(".be-auswahl");
        aw.hidden = S.spiele.length < 2;
        aw.innerHTML = S.spiele.length < 2 ? "" : "<label>Die Datei enthält " + S.spiele.length + " Partien – welche sollen rein?</label>" +
          S.spiele.map(function (x, i) {
            var inf = P.lesen(x);
            return '<label class="be-wahl"><input type="checkbox" data-w="' + i + '"' + (i === 0 ? " checked" : "") + "> " + esc(partieText(null, inf)) +
              (inf.kopf.Round && inf.kopf.Round !== "?" ? ' <span class="klein">Runde ' + esc(inf.kopf.Round) + "</span>" : "") + "</label>";
          }).join("");
        [].forEach.call(aw.querySelectorAll("[data-w]"), function (c) {
          c.addEventListener("change", function () { S.wahl[+c.getAttribute("data-w")] = c.checked; seiteRaten(); zeichnen(); });
        });
        if (neuGelesen) seiteRaten();
        zeichnen();
      }
      if (alt) {                                    // Einstellungen der vorhandenen Partie übernehmen
        einlesen(false);
        var inf = S.info;
        if (alt.ab < 0) S.start = "ende";
        else if (alt.ab > 0 && inf) {
          S.start = "zug";
          var z = inf.zuege[Math.min(alt.ab, inf.zuege.length - 1)];
          if (alt.ab >= inf.zuege.length) S.start = "ende"; else { S.zug = z.nr; S.farbe = z.farbe; }
        }
        zeichnen();
      }
      var timer = null;
      ta.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(function () { einlesen(true); }, 300); });
      el.querySelector(".be-datei input").addEventListener("change", function (ev) {
        var f = ev.target.files[0]; if (!f) return;
        var r = new FileReader();
        r.onload = function () { ta.value = String(r.result).slice(0, 2000000); einlesen(true); };
        r.readAsText(f);
      });
      el.addEventListener("click", function (ev) {
        var b = ev.target.closest("button"); if (!b) return;
        if (b.hasAttribute("data-s")) { S.start = b.getAttribute("data-s"); if (S.start === "zug" && S.info && S.zug === 1) { var mitte = S.info.zuege[Math.floor(S.info.zuege.length / 2)]; S.zug = mitte.nr; S.farbe = mitte.farbe; } zeichnen(); }
        if (b.hasAttribute("data-f")) { S.farbe = b.getAttribute("data-f"); zeichnen(); }
        if (b.hasAttribute("data-v")) { S.sicht = b.getAttribute("data-v"); zeichnen(); }
      });
      el.querySelector(".be-zugnr").addEventListener("change", function (ev) { S.zug = Math.max(1, parseInt(ev.target.value, 10) || 1); zeichnen(); });
      el.querySelector(".be-ok").addEventListener("click", function () {
        var gewaehlt = S.spiele.filter(function (x, i) { return S.wahl[i]; });
        if (alt) {
          Z.partien[index] = { pgn: gewaehlt[0], ab: ab(), sicht: S.sicht };
        } else {
          var platz = MAX_PARTIEN - Z.partien.length;
          if (gewaehlt.length > platz) { meldung("Höchstens " + MAX_PARTIEN + " Partien – " + (gewaehlt.length - platz) + " weggelassen.", "fehler"); gewaehlt = gewaehlt.slice(0, platz); }
          var marken = [];
          gewaehlt.forEach(function (pgn) {
            S.info = P.lesen(pgn);
            Z.partien.push({ pgn: pgn, ab: ab(), sicht: S.sicht });
            marken.push("[Partie " + Z.partien.length + "]");
          });
          einfuegen(marken.join("\n\n"));
        }
        d.zu(); partienZeichnen(); merken();
      });
      if (!alt) ta.focus();
    }).catch(function () { el.querySelector(".be-erkannt").textContent = "Das Schachbrett konnte nicht geladen werden."; });
  }

  function tabelleDialog() {
    var d = dialog('<h3>Tabelle von chess-results einfügen</h3>' +
      '<label>Link zum Turnier<input type="url" class="be-crurl" placeholder="https://chess-results.com/tnr1171232.aspx"></label>' +
      '<p class="klein">Gezeigt wird die Endtabelle bzw. der aktuelle Stand, unsere Spieler hervorgehoben. Bei Turnieren mit mehreren Gruppen den Link der Gruppe nehmen, die gezeigt werden soll. ' +
      'In den ersten 30 Tagen nach dem Berichtsdatum aktualisiert sich die Tabelle jede Nacht.</p><p class="be-erkannt klein"></p>' +
      '<div class="be-dlg-fuss"><button type="button" class="btn leise" data-zu>Abbrechen</button><button type="button" class="btn be-ok">Einfügen</button></div>');
    var inp = d.el.querySelector(".be-crurl");
    inp.focus();
    function ok() {
      var m = inp.value.trim().match(/^https?:\/\/(?:[\w-]+\.)?chess-results\.com\/(?:\w+\/)?tnr(\d+)\.aspx/i);
      if (!m) { var e = d.el.querySelector(".be-erkannt"); e.textContent = "Das ist kein chess-results-Link (er enthält „tnr“ und eine Nummer)."; e.className = "be-erkannt klein fehler"; return; }
      einfuegen("[Tabelle https://chess-results.com/tnr" + m[1] + ".aspx]");
      d.zu();
    }
    d.el.querySelector(".be-ok").addEventListener("click", ok);
    inp.addEventListener("keydown", function (ev) { if (ev.key === "Enter") { ev.preventDefault(); ok(); } });
  }

  // ---------- Werkzeugleiste ----------
  function umschliessen(links, rechts, platzhalter) {
    var t = $(".be-text"), a = t.selectionStart, e = t.selectionEnd, sel = t.value.slice(a, e) || platzhalter;
    t.value = t.value.slice(0, a) + links + sel + rechts + t.value.slice(e);
    t.selectionStart = a + links.length; t.selectionEnd = a + links.length + sel.length; t.focus(); merken();
  }
  function zeilenAnfang(praefix) {
    var t = $(".be-text"), a = t.value.lastIndexOf("\n", t.selectionStart - 1) + 1;
    if (t.value.slice(a, a + praefix.length) === praefix) t.value = t.value.slice(0, a) + t.value.slice(a + praefix.length);
    else t.value = t.value.slice(0, a) + praefix + t.value.slice(a);
    t.focus(); merken();
  }
  function leiste(was) {
    if (was === "fett") umschliessen("*", "*", "fett");
    if (was === "kursiv") umschliessen("_", "_", "kursiv");
    if (was === "ueber") zeilenAnfang("= ");
    if (was === "liste") zeilenAnfang("- ");
    if (was === "link") {
      var url = prompt("Adresse des Links (https://…):", "https://");
      if (url && /^https?:\/\/\S+$/.test(url)) umschliessen("[", "](" + url + ")", "Linktext");
    }
    if (was === "partie") return partieDialog(null);
    if (was === "tabelle") return tabelleDialog();
    if (was === "bild") {
      var genutzt = ($(".be-text").value.match(/\[Bild (\d+)\]/g) || []).map(function (x) { return +x.match(/\d+/)[0]; });
      for (var i = 0; i < Z.bilder.length; i++) if (genutzt.indexOf(i + 1) < 0) return einfuegen("[Bild " + (i + 1) + "]");
      var f = APP.querySelector(".be-drop input"); if (f) f.click();
    }
  }

  // ---------- Entwurf im Browser ----------
  function felder() {
    return { titel: $("[name=titel]").value, autor: $("[name=autor]").value, datum: $("[name=datum]").value,
      text: $(".be-text").value, mail: ($("[name=mail]") || {}).value || "", kat: Z.kat };
  }
  var merkTimer = null;
  function merken() {
    if (Z.id) return;                                // beim Bearbeiten nichts im Browser speichern
    clearTimeout(merkTimer);
    merkTimer = setTimeout(function () {
      var w = felder(); w.bilder = Z.bilder; w.titelbild = Z.titelbild; w.partien = Z.partien;
      try { localStorage.setItem(SPEICHER, JSON.stringify(w)); }
      catch (e) { try { w.bilder = []; localStorage.setItem(SPEICHER, JSON.stringify(w)); } catch (e2) {} }
      var s = $(".be-gespeichert"); if (s) { var d = new Date(); s.textContent = "Entwurf im Browser gespeichert · " + d.getHours() + ":" + ("0" + d.getMinutes()).slice(-2); }
    }, 600);
  }

  // ---------- Formular ----------
  function meldung(text, art) {
    var m = $(".be-meldung"); if (!m) return;
    m.textContent = text || ""; m.className = "be-meldung " + (art || ""); m.hidden = !text;
  }
  function darfDirekt() { return !!(ICH && ICH.ich.darf.berichte); }
  function eigenerName() { return ICH && $("[name=autor]").value.trim().toLowerCase() === ICH.ich.name.toLowerCase(); }
  function knopfText() {
    var k = $(".be-senden"); if (!k) return;
    if (Z.id) k.textContent = "Änderungen speichern";
    else k.textContent = darfDirekt() && eigenerName() ? "Veröffentlichen" : "Einreichen";
  }
  function formular() {
    var hinweis = ICH ? (darfDirekt()
      ? '<div class="be-hinweis gruen">Angemeldet als <b>' + esc(ICH.ich.benutzer) + "</b> · Du darfst direkt veröffentlichen – dein Bericht ist nach dem nächsten Build online.</div>"
      : '<div class="be-hinweis">Angemeldet als <b>' + esc(ICH.ich.benutzer) + "</b> · Dein Bericht wird von einem Admin kurz angeschaut und dann freigegeben.</div>")
      : '<div class="be-hinweis">Dein Bericht wird von einem Admin kurz angeschaut und dann freigegeben.</div>';
    APP.innerHTML = '<div class="be-kopf"></div>' + hinweis +
      '<div class="be-reihe"><label>Titel<input type="text" name="titel" maxlength="120" placeholder="z. B. AFK 2 gewinnt das Derby"></label>' +
      '<label>Autor<input type="text" name="autor" maxlength="80" placeholder="Vor- und Nachname" autocomplete="name"></label>' +
      '<label>Datum<input type="text" name="datum" maxlength="10" inputmode="numeric" placeholder="TT.MM.JJJJ"></label></div>' +
      (ICH ? "" : '<label style="margin-bottom:.8rem">E-Mail für Rückfragen (optional, wird nicht veröffentlicht)<input type="email" name="mail" maxlength="120" autocomplete="email"></label>') +
      '<label>Kategorien</label><div class="be-kat">' + KATEGORIEN.map(function (k) { return '<button type="button" data-kat="' + esc(k[0]) + '">' + esc(k[1]) + "</button>"; }).join("") + "</div>" +
      '<div class="be-tabs"><button type="button" class="an" data-tab="schreiben">Schreiben</button><button type="button" data-tab="vorschau">Vorschau</button></div>' +
      '<div class="be-schreiben"><div class="be-leiste"><button type="button" data-l="fett" title="Fett"><b>B</b></button><button type="button" data-l="kursiv" title="Kursiv"><i>I</i></button>' +
      '<button type="button" data-l="ueber">Überschrift</button><i class="tr"></i><button type="button" data-l="liste">• Liste</button>' +
      '<button type="button" data-l="link">Link</button><button type="button" data-l="bild">Bild</button><i class="tr"></i><button type="button" data-l="partie">Partie</button><button type="button" data-l="tabelle">Tabelle</button></div>' +
      '<textarea class="be-text" maxlength="' + MAX + '" placeholder="Leere Zeile = neuer Absatz"></textarea>' +
      '<p class="be-hilfe"><code>*fett*</code> <code>_kursiv_</code> <code>= Überschrift</code> <code>- Punkt</code> <code>[Text](https://…)</code> <code>[Bild 2]</code> – oder einfach die Knöpfe benutzen.</p></div>' +
      '<div class="be-vorschau" hidden></div>' +
      '<div class="be-partien"></div><div class="be-bilder"></div>' +
      '<label class="be-falle" aria-hidden="true">Website <input type="text" name="website" tabindex="-1" autocomplete="off"></label>' +
      '<div class="be-fuss"><span class="klein be-gespeichert"></span><span><button type="button" class="btn leise be-abbrechen" hidden>Abbrechen</button> ' +
      '<button type="button" class="btn be-senden">Einreichen</button></span></div><p class="be-meldung" hidden role="status"></p>' +
      '<div class="be-meine"></div>';
    datumFormat($("[name=datum]"));
    [].forEach.call(APP.querySelectorAll("[data-kat]"), function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-kat"), i = Z.kat.indexOf(k);
        if (i < 0) Z.kat.push(k); else Z.kat.splice(i, 1);
        b.classList.toggle("an", i < 0); merken();
      });
    });
    [].forEach.call(APP.querySelectorAll("[data-tab]"), function (b) {
      b.addEventListener("click", function () {
        var v = b.getAttribute("data-tab") === "vorschau";
        [].forEach.call(APP.querySelectorAll("[data-tab]"), function (x) { x.classList.toggle("an", x === b); });
        $(".be-schreiben").hidden = v; $(".be-vorschau").hidden = !v;
        if (v) $(".be-vorschau").innerHTML = "<h1>" + inline($("[name=titel]").value || "Ohne Titel") + '</h1><p class="news-meta">' +
          esc($("[name=datum]").value) + ($("[name=autor]").value ? " · von " + esc($("[name=autor]").value) : "") + "</p>" + vorschauHtml($(".be-text").value);
        if (v && $(".be-vorschau [data-partie]")) partieModul().then(function (P) { [].forEach.call(APP.querySelectorAll(".be-vorschau [data-partie]"), P.viewer); });
      });
    });
    [].forEach.call(APP.querySelectorAll("[data-l]"), function (b) { b.addEventListener("click", function () { leiste(b.getAttribute("data-l")); }); });
    APP.addEventListener("input", function (ev) { if (ev.target.name === "autor") knopfText(); if (!ev.target.closest(".be-bild")) merken(); });
    $(".be-senden").addEventListener("click", senden);
    $(".be-abbrechen").addEventListener("click", function () { if (confirm("Bearbeiten abbrechen? Ungespeicherte Änderungen gehen verloren.")) neuAnfangen(true); });
  }
  function befuellen(w) {
    $("[name=titel]").value = w.titel || ""; $("[name=autor]").value = w.autor || ""; $("[name=datum]").value = w.datum || heute();
    $(".be-text").value = w.text || ""; if ($("[name=mail]")) $("[name=mail]").value = w.mail || "";
    Z.kat = (w.kat || []).slice(); Z.bilder = (w.bilder || []).slice(); Z.titelbild = w.titelbild || 0; Z.partien = (w.partien || []).slice();
    [].forEach.call(APP.querySelectorAll("[data-kat]"), function (b) { b.classList.toggle("an", Z.kat.indexOf(b.getAttribute("data-kat")) >= 0); });
    bilderZeichnen(); partienZeichnen(); knopfText();
  }
  function neuAnfangen(leeren) {
    Z.id = null; Z.eintrag = null;
    var w = {};
    if (!leeren) { try { w = JSON.parse(localStorage.getItem(SPEICHER) || "{}"); } catch (e) {} }
    if (!w.autor && ICH) w.autor = ICH.ich.name;
    befuellen(w);
    $(".be-kopf").innerHTML = ""; $(".be-abbrechen").hidden = true;
    history.replaceState(null, "", location.pathname + location.hash);
  }

  function senden() {
    var w = felder(), datum = isoDatum(w.datum);
    if (!w.titel.trim() || !w.autor.trim() || !w.text.trim()) return meldung("Bitte Titel, Autor und Text ausfüllen.", "fehler");
    if (!datum) return meldung("Datum bitte als TT.MM.JJJJ.", "fehler");
    var d = { id: Z.id, titel: w.titel, autor: w.autor, datum: datum, text: w.text, mail: w.mail, kategorien: Z.kat,
      titelbild: Z.titelbild, website: $("[name=website]").value,
      partien: Z.partien,
      bilder: Z.bilder.map(function (b) { return b.daten ? { daten: b.daten, unterschrift: b.unterschrift } : { name: b.name, unterschrift: b.unterschrift }; }) };
    var k = $(".be-senden"); k.disabled = true;
    meldung(Z.bilder.some(function (b) { return b.daten; }) ? "Wird hochgeladen – mit Fotos kann das etwas dauern …" : "Wird gesendet …", "");
    api("b_speichern", d).then(function (a) {
      k.disabled = false;
      if (!a.ok) return meldung(a.fehler || "Das hat nicht geklappt.", "fehler");
      var warBearbeiten = !!Z.id;
      try { if (!warBearbeiten) localStorage.removeItem(SPEICHER); } catch (e) {}
      neuAnfangen(true);
      meldung(warBearbeiten ? "Gespeichert." + (a.status === "online" ? " Die Änderung ist nach dem nächsten Build online." : "")
        : a.status === "online" ? "Veröffentlicht! Dein Bericht ist nach dem nächsten Build online (spätestens morgen früh)."
        : "Danke! Dein Bericht ist angekommen und erscheint, sobald ein Admin ihn freigegeben hat.", "ok");
      meineLaden();
    });
  }

  // ---------- Bearbeiten ----------
  function bearbeiten(id) {
    if (!ICH) return meldung("Zum Bearbeiten bitte oben rechts anmelden.", "fehler");
    DETAILS.open = true;
    meldung("Bericht wird geladen …", "");
    api("b_laden", { id: id }).then(function (a) {
      if (!a.ok) return meldung(a.fehler, "fehler");
      var p = ausTypst(a.typst, a.bilder, a.partien);
      if (!p.ok) return meldung("Dieser Bericht enthält Sonderformatierungen, die der Editor nicht kennt. Bitte direkt in der Datei Bericht.typ ändern.", "fehler");
      Z.id = a.eintrag.id; Z.eintrag = a.eintrag;
      befuellen(p);
      $(".be-kopf").innerHTML = '<div class="be-hinweis">Du bearbeitest <b>' + esc(p.titel) + "</b> (" + (a.eintrag.status === "online" ? "online" : "Entwurf") + ").</div>";
      $(".be-abbrechen").hidden = false;
      meldung("", "");
      DETAILS.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  // ---------- Meine Berichte ----------
  function meineLaden() {
    var box = $(".be-meine");
    if (!box || !ICH) return;
    api("b_liste").then(function (a) {
      if (!a.ok || !a.eigene || !a.eigene.length) { box.innerHTML = ""; return; }
      box.innerHTML = "<h3>Meine Berichte</h3><table>" + a.eigene.map(function (e) {
        var knoepfe = '<button type="button" class="kt-mini" data-m="bearbeiten">Bearbeiten</button>';
        if (e.status === "online") knoepfe += '<button type="button" class="kt-mini rot" data-m="zurueckziehen">Zurückziehen</button>';
        else if (darfDirekt() && !e.gast) knoepfe += '<button type="button" class="kt-mini" data-m="veroeffentlichen">Veröffentlichen</button>';
        else knoepfe += '<span class="klein">wartet auf Freigabe</span>';
        return '<tr data-id="' + esc(e.id) + '"><td><b>' + esc(e.titel) + '</b><br><span class="klein">' + esc(deDatum(e.datum)) + "</span></td>" +
          '<td><span class="be-st ' + e.status + '">' + (e.status === "online" ? "online" : "Entwurf") + '</span></td><td class="be-k" style="text-align:right">' + knoepfe + "</td></tr>";
      }).join("") + "</table>";
      [].forEach.call(box.querySelectorAll("[data-m]"), function (b) {
        b.addEventListener("click", function () {
          var id = b.closest("tr").getAttribute("data-id"), was = b.getAttribute("data-m");
          if (was === "bearbeiten") return bearbeiten(id);
          if (was === "zurueckziehen" && !confirm("Bericht zurückziehen? Er ist dann wieder ein Entwurf und verschwindet beim nächsten Build von der Website.")) return;
          b.disabled = true;
          api("b_status", { id: id, aktion: was }).then(function (r) { meldung(r.ok ? r.meldung : r.fehler, r.ok ? "ok" : "fehler"); meineLaden(); });
        });
      });
    });
  }

  // ---------- Start ----------
  var gestartet = false;
  function start(a) {
    if (gestartet) return; gestartet = true;
    ICH = a && a.ich ? a : null;
    formular(); neuAnfangen(false); meineLaden();
    var p = new URLSearchParams(location.search).get("bearbeiten");
    if (p) bearbeiten(p);
    else if (location.hash === "#einreichen") DETAILS.open = true;
  }
  if (!token()) start(null);
  else if (window.AFK_KONTO) window.AFK_KONTO.ich().then(start, function () { start(null); });
  else {
    document.addEventListener("afk-konto", function (ev) { start(ev.detail); });
    setTimeout(function () { if (!gestartet && window.AFK_KONTO) window.AFK_KONTO.ich().then(start); else start(null); }, 6000);
  }
})();
