/* SG AFK – Mitgliederbereich (Login, Mein Profil, Verwaltung)
   Backend: Apps Script (Mitglieder.gs). Eingebunden in templates/base.html:
     <script src="konto.js" data-skript="<Web-App-URL>" data-pfad="<nav_path>" defer></script>
   Angemeldet bleibt man über localStorage "afk-sitzung" (Token, nur als Hash auf dem Server). */
(function () {
  "use strict";
  var SCRIPT = document.currentScript;
  var SKRIPT = SCRIPT && SCRIPT.getAttribute("data-skript");
  var PFAD = (SCRIPT && SCRIPT.getAttribute("data-pfad")) || "";
  if (!SKRIPT) return;

  var KEY = "afk-sitzung", ICH_KEY = "afk-ich", GEB_KEY = "afk-geb", ICH_MINUTEN = 5, GEB_STUNDEN = 12;
  var MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];
  var WT = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];

  // ---------- Grundlagen ----------
  function token() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } }
  function setzeToken(t) {
    try { if (t) localStorage.setItem(KEY, t); else localStorage.removeItem(KEY); localStorage.removeItem(ICH_KEY); localStorage.removeItem(GEB_KEY); } catch (e) {}
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }
  function api(typ, daten) {
    daten = daten || {};
    daten.typ = typ;
    if (token() && !daten.sitzung) daten.sitzung = token();
    return fetch(SKRIPT, { method: "POST", body: JSON.stringify(daten) })
      .then(function (r) { return r.json(); })
      .then(function (a) { if (a && a.abgemeldet) { setzeToken(""); knopfZeigen(null); } return a; })
      .catch(function () { return { ok: false, fehler: "Keine Verbindung – bitte später nochmal" }; });
  }
  function datumText(iso, mitJahr) {
    var p = String(iso || "").split("-");
    if (p.length !== 3) return "";
    return +p[2] + ". " + MONATE[+p[1] - 1] + (mitJahr === false ? "" : " " + p[0]);
  }
  function textHtml(text) {
    return String(text || "").trim().split(/\n\s*\n/).filter(Boolean).map(function (abs) {
      return "<p>" + esc(abs.trim()).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>').replace(/\n/g, "<br>") + "</p>";
    }).join("");
  }
  function linksHtml(li, cc) {
    var t = [];
    if (li) t.push('Lichess: <a href="https://lichess.org/@/' + encodeURIComponent(li) + '" target="_blank" rel="noopener">' + esc(li) + "</a>");
    if (cc) t.push('Chess.com: <a href="https://www.chess.com/member/' + encodeURIComponent(cc) + '" target="_blank" rel="noopener">' + esc(cc) + "</a>");
    return t.length ? '<p class="sp-links-profil">' + t.join(" · ") + "</p>" : "";
  }

  // Eigene Daten (im Browser gemerkt: Seiten zeigen sofort den letzten Stand, im Hintergrund wird nachgeladen)
  var ICH_PROMISE = null;
  function ich(neu) {
    if (!token()) return Promise.resolve(null);
    if (ICH_PROMISE && !neu) return ICH_PROMISE;
    var frisch = api("m_ich").then(function (a) {
      if (!a.ok) { try { localStorage.removeItem(ICH_KEY); } catch (e) {} return null; }
      try { localStorage.setItem(ICH_KEY, JSON.stringify({ t: token(), zeit: Date.now(), d: a })); } catch (e) {}
      return a;
    });
    if (!neu) {
      // Sofort mit dem letzten Stand anzeigen (kein Warten); im Hintergrund wird nachgeladen,
      // der neue Stand gilt dann ab der nächsten Seite. Rechte prüft der Server ohnehin bei jeder Aktion.
      try {
        var c = JSON.parse(localStorage.getItem(ICH_KEY) || "null");
        if (c && c.t === token()) return (ICH_PROMISE = Promise.resolve(c.d));
      } catch (e) {}
    }
    ICH_PROMISE = frisch;
    return ICH_PROMISE;
  }

  // ---------- Kopfzeile: Personen-Knopf und Menü ----------
  var KNOPF = document.getElementById("konto-knopf");
  function knopfZeigen(a) {
    if (!KNOPF) return;
    KNOPF.hidden = false;
    KNOPF.classList.toggle("an", !!a);
    KNOPF.title = a ? "Angemeldet als " + a.ich.benutzer : "Anmelden";
    KNOPF.setAttribute("aria-label", KNOPF.title);
    var p = KNOPF.querySelector(".kt-zahl");
    if (p) p.remove();
    if (a && a.offen) KNOPF.appendChild(el('<span class="kt-zahl">' + a.offen + "</span>"));
  }
  function menueSchliessen() { var m = document.querySelector(".kt-menue"); if (m) m.remove(); }
  function menue(a) {
    if (document.querySelector(".kt-menue")) return menueSchliessen();
    var m = el('<div class="kt-menue" role="menu">' +
      '<div class="kt-menue-kopf">Angemeldet als <b>' + esc(a.ich.benutzer) + "</b></div>" +
      '<a href="' + PFAD + 'mein-profil.html">Mein Profil</a>' +
      '<a href="' + PFAD + "spieler/" + esc(a.ich.slug) + '.html">Meine Seite ansehen</a>' +
      ((a.listen && a.listen.length) || a.ich.darf.listen ? '<a href="' + PFAD + 'listen.html">Listen' + (a.listen && a.listen.length ? " (" + a.listen.length + ")" : "") + "</a>" : "") +
      (a.ich.darf.verwaltung || a.ich.darf.turniere || a.ich.darf.listen ? '<a href="' + PFAD + "verwaltung.html" +
        (!a.ich.darf.verwaltung ? (a.ich.darf.turniere ? "#turniere" : "#listen") : a.offenTurniere && !a.offenAntraege && !a.offenBerichte ? "#turniere" : a.offenBerichte && !a.offenAntraege ? "#berichte" : "") + '">' +
        "Verwaltung" + (a.offen ? ' <span class="kt-zahl innen">' + a.offen + "</span>" : "") + "</a>" : "") +
      '<button type="button" data-kt="abmelden">Abmelden</button></div>');
    KNOPF.parentNode.appendChild(m);
    m.querySelector("[data-kt=abmelden]").addEventListener("click", function () { abmelden(false); });
    setTimeout(function () {
      document.addEventListener("click", function weg(ev) {
        if (!m.contains(ev.target) && ev.target !== KNOPF) { menueSchliessen(); document.removeEventListener("click", weg); }
      });
    });
  }
  function abmelden(alle) {
    return api("m_abmelden", { alle: !!alle }).then(function () {
      setzeToken(""); location.href = PFAD + "index.html";
    });
  }
  if (KNOPF) {
    KNOPF.addEventListener("click", function () {
      ich().then(function (a) { if (a) menue(a); else fenster("login"); });
    });
  }

  // ---------- Fenster: Anmelden / Registrieren / Code ----------
  function fensterSchliessen() { var f = document.querySelector(".kt-hinter"); if (f) f.remove(); document.removeEventListener("keydown", escTaste); }
  function escTaste(ev) { if (ev.key === "Escape") fensterSchliessen(); }
  function fenster(art) {
    fensterSchliessen();
    var h = el('<div class="kt-hinter"><div class="kt-modal" role="dialog" aria-modal="true">' +
      '<button type="button" class="kt-zu" aria-label="Schließen">×</button><div class="kt-inhalt"></div></div></div>');
    document.body.appendChild(h);
    h.addEventListener("mousedown", function (ev) { if (ev.target === h) fensterSchliessen(); });
    h.querySelector(".kt-zu").addEventListener("click", fensterSchliessen);
    document.addEventListener("keydown", escTaste);
    ansicht(art);
  }
  function tabs(an) {
    return '<div class="kt-tabs"><button type="button" data-ans="login"' + (an === "login" ? ' class="an"' : "") + ">Anmelden</button>" +
      '<button type="button" data-ans="reg"' + (an === "reg" ? ' class="an"' : "") + ">Registrieren</button></div>";
  }
  function feld(name, label, typ, extra) {
    return '<div class="kt-feld"><label for="kt-' + name + '">' + label + '</label><input id="kt-' + name + '" name="' + name +
      '" type="' + (typ || "text") + '" ' + (extra || "") + "><small></small></div>";
  }
  function fehler(form, text) {
    var f = form.querySelector(".kt-fehler");
    f.textContent = text || ""; f.hidden = !text;
  }
  function laedt(form, an) {
    var b = form.querySelector("button[type=submit]");
    b.disabled = an; form.classList.toggle("laedt", an);
  }
  function ansicht(art) {
    var box = document.querySelector(".kt-inhalt");
    if (!box) return;
    if (art === "login") {
      box.innerHTML = tabs("login") + '<form class="kt-form" novalidate>' +
        feld("benutzer", "Benutzername", "text", 'autocomplete="username" autocapitalize="none" required') +
        feld("pw", "Passwort", "password", 'autocomplete="current-password" required') +
        '<p class="kt-fehler" hidden></p><button type="submit" class="kt-btn voll">Anmelden</button>' +
        '<p class="kt-klein">Passwort vergessen? Melde dich bei einem Admin – du bekommst einen Code.<br>' +
        '<button type="button" class="kt-link" data-ans="code">Code vom Admin einlösen</button></p>' +
        '<p class="kt-klein">Registrieren können sich Vereinsmitglieder ab 18 Jahren.</p></form>';
      var f = box.querySelector("form");
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); fehler(f, ""); laedt(f, true);
        api("m_login", { benutzer: f.benutzer.value, pw: f.pw.value, sitzung: "-" }).then(function (a) {
          laedt(f, false);
          if (!a.ok) return fehler(f, a.fehler);
          angemeldet(a);
        });
      });
      setTimeout(function () { f.benutzer.focus(); });
    } else if (art === "reg") {
      box.innerHTML = tabs("reg") + '<form class="kt-form" novalidate>' +
        '<div class="kt-info">Deine Angaben werden mit der Mitgliederliste abgeglichen. Danach bestätigt ein Admin die Registrierung.</div>' +
        '<div class="kt-zwei">' + feld("vorname", "Vorname", "text", 'autocomplete="given-name" required') +
        feld("nachname", "Nachname", "text", 'autocomplete="family-name" required') + "</div>" +
        feld("geb", "Geburtsdatum", "text", 'placeholder="TT.MM.JJJJ" inputmode="numeric" maxlength="10" autocomplete="bday" required') +
        feld("benutzer", "Benutzername", "text", 'autocomplete="username" autocapitalize="none" maxlength="20" required') +
        '<div class="kt-zwei">' + feld("pw", "Passwort", "password", 'autocomplete="new-password" minlength="8" required') +
        feld("pw2", "Wiederholen", "password", 'autocomplete="new-password" required') + "</div>" +
        '<label class="kt-check"><input type="checkbox" name="ok"> <span>Ich bin einverstanden, dass meine Angaben für den Mitgliederbereich gespeichert werden ' +
        '(<a href="' + PFAD + 'impressum.html#mitgliederbereich" target="_blank">Datenschutz</a>).</span></label>' +
        '<p class="kt-fehler" hidden></p><button type="submit" class="kt-btn voll">Registrierung beantragen</button></form>';
      var g = box.querySelector("form"), timer = null, letzte = "";
      function hinweis(name, text, gut) {
        var fd = g.querySelector("[name=" + name + "]").closest(".kt-feld");
        fd.classList.toggle("gut", gut === true); fd.classList.toggle("schlecht", gut === false);
        fd.querySelector("small").textContent = text || "";
      }
      g.benutzer.addEventListener("input", function () {
        var b = g.benutzer.value.trim().toLowerCase();
        clearTimeout(timer);
        if (!b) return hinweis("benutzer", "", null);
        if (!/^[a-z0-9][a-z0-9._-]{2,19}$/.test(b)) return hinweis("benutzer", "3–20 Zeichen: Buchstaben, Ziffern, . _ -", false);
        hinweis("benutzer", "wird geprüft …", null);
        timer = setTimeout(function () {
          letzte = b;
          api("m_name_frei", { benutzer: b, sitzung: "-" }).then(function (a) {
            if (letzte !== b) return;
            if (!a.ok) return hinweis("benutzer", "", null);
            hinweis("benutzer", a.frei ? "Benutzername ist frei" : (a.grund || "„" + g.benutzer.value.trim() + "“ ist schon vergeben"), !!a.frei);
          });
        }, 400);
      });
      g.geb.addEventListener("input", function () {          // nur Ziffern tippen, Punkte kommen von selbst
        if (/^\d{1,2}\.\d{1,2}\.\d{0,4}$/.test(g.geb.value)) return;
        var z = g.geb.value.replace(/\D/g, "").slice(0, 8);
        g.geb.value = z.length > 4 ? z.slice(0, 2) + "." + z.slice(2, 4) + "." + z.slice(4) : z.length > 2 ? z.slice(0, 2) + "." + z.slice(2) : z;
      });
      g.geb.addEventListener("blur", function () {
        var m = g.geb.value.trim().match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
        if (!g.geb.value.trim()) return hinweis("geb", "", null);
        if (!m) return hinweis("geb", "Bitte als TT.MM.JJJJ", false);
        var h = new Date(), a = h.getFullYear() - m[3];
        if (h.getMonth() + 1 < +m[2] || (h.getMonth() + 1 === +m[2] && h.getDate() < +m[1])) a--;
        hinweis("geb", a < 18 ? "Registrieren ist erst ab 18 Jahren möglich." : "", a < 18 ? false : null);
      });
      g.pw2.addEventListener("input", function () { hinweis("pw2", g.pw2.value && g.pw2.value !== g.pw.value ? "Passwörter sind verschieden" : "", g.pw2.value && g.pw2.value !== g.pw.value ? false : null); });
      g.addEventListener("submit", function (ev) {
        ev.preventDefault(); fehler(g, "");
        if (g.pw.value.length < 8) return fehler(g, "Passwort: mindestens 8 Zeichen");
        if (g.pw.value !== g.pw2.value) return fehler(g, "Die Passwörter sind verschieden");
        if (!g.ok.checked) return fehler(g, "Bitte der Datenspeicherung zustimmen");
        laedt(g, true);
        api("m_registrieren", { vorname: g.vorname.value, nachname: g.nachname.value, geburtsdatum: g.geb.value, benutzer: g.benutzer.value,
          pw: g.pw.value, einverstanden: true, sitzung: "-" }).then(function (a) {
          laedt(g, false);
          if (!a.ok) return fehler(g, a.fehler);
          var b = g.benutzer.value.trim();
          if (a.sofort) {
            box.innerHTML = '<div class="kt-fertig"><h2>Willkommen, Inhaber</h2><p>Dein Konto ist sofort aktiv.</p></div>';
            return setTimeout(function () { ansicht("login"); }, 1500);
          }
          box.innerHTML = '<div class="kt-fertig"><h2>Fast geschafft</h2><p>Deine Angaben passen zur Mitgliederliste. ' +
            "Ein Admin meldet sich kurz bei dir und schaltet dein Konto frei.</p>" +
            '<p class="kt-klein">Danach kannst du dich mit <b>' + esc(b) + '</b> anmelden.</p>' +
            '<button type="button" class="kt-btn leise" data-kt="zu">Schließen</button></div>';
          box.querySelector("[data-kt=zu]").addEventListener("click", fensterSchliessen);
        });
      });
      setTimeout(function () { g.vorname.focus(); });
    } else if (art === "code") {
      box.innerHTML = '<h2 class="kt-titel">Neues Passwort</h2><form class="kt-form" novalidate>' +
        '<p class="kt-klein links">Den Code bekommst du von einem Admin. Er gilt 7 Tage.</p>' +
        feld("benutzer", "Benutzername", "text", 'autocapitalize="none" required') +
        feld("code", "Code", "text", 'autocapitalize="characters" autocomplete="one-time-code" required') +
        feld("neu", "Neues Passwort", "password", 'autocomplete="new-password" minlength="8" required') +
        '<p class="kt-fehler" hidden></p><button type="submit" class="kt-btn voll">Passwort setzen und anmelden</button>' +
        '<p class="kt-klein"><button type="button" class="kt-link" data-ans="login">Zurück zum Anmelden</button></p></form>';
      var c = box.querySelector("form");
      c.addEventListener("submit", function (ev) {
        ev.preventDefault(); fehler(c, ""); laedt(c, true);
        api("m_code", { benutzer: c.benutzer.value, code: c.code.value, neu: c.neu.value, sitzung: "-" }).then(function (a) {
          laedt(c, false);
          if (!a.ok) return fehler(c, a.fehler);
          angemeldet(a);
        });
      });
    }
    [].forEach.call(box.querySelectorAll("[data-ans]"), function (b) {
      b.addEventListener("click", function () { ansicht(b.getAttribute("data-ans")); });
    });
  }
  function angemeldet(a) {
    setzeToken(a.sitzung);
    ICH_PROMISE = null;
    fensterSchliessen();
    location.reload();
  }

  // ---------- Seite "Mein Profil" ----------
  function bildVerkleinern(datei) {
    var MAX = 1000;
    function zeichnen(quelle, w, h) {
      var s = Math.min(1, MAX / Math.max(w, h)), c = document.createElement("canvas");
      c.width = Math.round(w * s); c.height = Math.round(h * s);
      c.getContext("2d").drawImage(quelle, 0, 0, c.width, c.height);
      return { url: c.toDataURL("image/jpeg", 0.86), breite: w };
    }
    if (window.createImageBitmap) {
      return createImageBitmap(datei, { imageOrientation: "from-image" }).then(function (b) { return zeichnen(b, b.width, b.height); });
    }
    return new Promise(function (ok, nein) {
      var img = new Image();
      img.onload = function () { ok(zeichnen(img, img.naturalWidth, img.naturalHeight)); };
      img.onerror = nein;
      img.src = URL.createObjectURL(datei);
    });
  }
  function meldung(box, text, art) {
    var m = box.querySelector(".kt-meldung");
    if (!m) { m = el('<p class="kt-meldung"></p>'); box.insertBefore(m, box.firstChild); }
    m.className = "kt-meldung " + (art || "");
    m.textContent = text; m.hidden = !text;
    if (text) m.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  function bitteAnmelden(box, text) {
    box.innerHTML = '<div class="kt-karte kt-leer"><p>' + text + '</p><button type="button" class="kt-btn">Anmelden</button></div>';
    box.querySelector("button").addEventListener("click", function () { fenster("login"); });
  }
  function seiteProfil(box) {
    if (!token()) return bitteAnmelden(box, "Melde dich an, um dein Profil zu bearbeiten.");
    box.innerHTML = '<p class="kt-klein links">Lädt …</p>';
    api("m_ich", { mitFoto: true }).then(function (a) {
      if (!a.ok) return bitteAnmelden(box, a.fehler || "Bitte neu anmelden.");
      var i = a.ich, p = a.profil, jahr = i.jahr, gbDatum = datumText(i.geburtstag);
      var stufe = { inhaber: "Inhaber", admin: "Admin", mitglied: "Mitglied" }[i.stufe];
      function radio(wert, titel, text) {
        return '<label class="kt-radio"><input type="radio" name="gb" value="' + wert + '"' + (p.gb === wert ? " checked" : "") + "><span><b>" + titel + "</b><small>" + text + "</small></span></label>";
      }
      box.innerHTML =
        '<p class="kt-unter">Angemeldet als <b>' + esc(i.benutzer) + '</b> <span class="kt-tag ' + i.stufe + '">' + stufe + "</span> · " +
        'Änderungen siehst du sofort, alle anderen ab morgen früh. <a href="' + PFAD + "spieler/" + esc(i.slug) + '.html">Meine Seite ansehen →</a></p>' +
        '<div class="kt-raster"><form class="kt-haupt" novalidate>' +
        '<div class="kt-karte"><h2>Über mich</h2><div class="kt-feld"><textarea name="text" maxlength="600" rows="6">' + esc(p.text) + "</textarea>" +
        '<small><span class="kt-zaehler"></span> · Leerzeile = neuer Absatz, Links werden klickbar.</small></div>' +
        '<div class="kt-zwei">' + feld("lichess", "Lichess", "text", 'placeholder="Benutzername oder Link" value="' + esc(p.lichess) + '"') +
        feld("chesscom", "Chess.com", "text", 'placeholder="Benutzername oder Link" value="' + esc(p.chesscom) + '"') + "</div></div>" +
        '<div class="kt-karte"><h2>Geburtstag</h2>' +
        radio("jahr", "Nur Jahrgang zeigen", "Alle sehen „Jahrgang " + esc(jahr) + "“. Standard.") +
        radio("oeffentlich", "Geburtstag öffentlich", "Alle sehen „" + esc(gbDatum) + "“, auch auf der Startseite bei „Geburtstage diese Woche“.") +
        radio("nichts", "Nichts zeigen", "Weder Jahrgang noch Geburtstag.") +
        '<p class="kt-klein links">Admins sehen deinen Geburtstag immer – zum Gratulieren.</p></div>' +
        '<div class="kt-karte"><h2>AFK on Tour</h2><label class="kt-check"><input type="checkbox" name="tour"' + (p.tour ? " checked" : "") + '> ' +
        "<span>Meine Turnierreisen (Orte, Abzeichen) auf meinem Profil zeigen – falls ich bei AFK on Tour eingetragen bin.</span></label></div>" +
        '<button type="submit" class="kt-btn">Speichern</button></form>' +
        '<div class="kt-seite-rechts"><div class="kt-karte"><h2>Foto</h2><div class="kt-foto-rahmen">' +
        (p.foto ? '<img class="kt-foto" alt="" src="' + p.foto + '">' : '<div class="kt-foto leer">Noch kein Foto</div>') + "</div>" +
        '<div class="kt-zeile"><label class="kt-btn leise">Neues Foto<input type="file" accept="image/*" hidden></label>' +
        (p.foto ? '<button type="button" class="kt-btn rot" data-kt="foto-weg">Entfernen</button>' : "") + "</div>" +
        '<p class="kt-klein links">Hochformat oder quadratisch, mindestens 800 px breit.</p></div>' +
        '<div class="kt-karte"><h2>Konto</h2><div class="kt-stapel">' +
        '<button type="button" class="kt-btn leise" data-kt="pw">Passwort ändern</button>' +
        '<button type="button" class="kt-btn leise" data-kt="ab">Abmelden</button>' +
        '<button type="button" class="kt-btn leise" data-kt="ab-alle">Auf allen Geräten abmelden</button>' +
        (i.stufe === "inhaber" ? "" : '<button type="button" class="kt-btn rot" data-kt="del">Konto löschen</button>') +
        '</div><div class="kt-unterform"></div></div></div></div>';
      var f = box.querySelector(".kt-haupt"), z = box.querySelector(".kt-zaehler");
      function zaehlen() { z.textContent = f.text.value.length + " / 600 Zeichen"; }
      f.text.addEventListener("input", zaehlen); zaehlen();
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var b = f.querySelector("button[type=submit]"); b.disabled = true;
        api("m_profil", { text: f.text.value, lichess: f.lichess.value, chesscom: f.chesscom.value,
          gb: (f.querySelector("[name=gb]:checked") || {}).value, tour: f.tour.checked }).then(function (r) {
          b.disabled = false;
          if (!r.ok) return meldung(box, r.fehler, "schlecht");
          try { localStorage.removeItem(ICH_KEY); } catch (e) {}
          meldung(box, "Gespeichert. Auf deiner Seite siehst du es sofort, alle anderen ab morgen früh.", "gut");
        });
      });
      var datei = box.querySelector("input[type=file]");
      datei.addEventListener("change", function () {
        if (!datei.files[0]) return;
        meldung(box, "Foto wird hochgeladen …", "");
        bildVerkleinern(datei.files[0]).then(function (b) {
          return api("m_foto", { bild: b.url }).then(function (r) {
            if (!r.ok) return meldung(box, r.fehler, "schlecht");
            meldung(box, b.breite < 800 ? "Foto gespeichert – es ist nur " + b.breite + " px breit und wirkt auf der Seite eventuell unscharf. Ein größeres Foto wäre besser."
              : "Foto gespeichert.", b.breite < 800 ? "warn" : "gut");
            var r2 = box.querySelector(".kt-foto-rahmen"); r2.innerHTML = '<img class="kt-foto" alt="" src="' + b.url + '">';
          });
        }).catch(function () { meldung(box, "Das Bild konnte nicht gelesen werden.", "schlecht"); });
      });
      function klick(name, fn) { var k = box.querySelector("[data-kt=" + name + "]"); if (k) k.addEventListener("click", fn); }
      klick("foto-weg", function () {
        if (!confirm("Foto wirklich entfernen?")) return;
        api("m_foto", { loeschen: true }).then(function (r) {
          if (!r.ok) return meldung(box, r.fehler, "schlecht");
          box.querySelector(".kt-foto-rahmen").innerHTML = '<div class="kt-foto leer">Noch kein Foto</div>';
          var weg = box.querySelector("[data-kt=foto-weg]"); if (weg) weg.remove();
          meldung(box, "Foto entfernt.", "gut");
        });
      });
      var unter = box.querySelector(".kt-unterform");
      klick("pw", function () {
        unter.innerHTML = '<form class="kt-form" novalidate>' + feld("alt", "Altes Passwort", "password", 'autocomplete="current-password"') +
          feld("neu", "Neues Passwort", "password", 'autocomplete="new-password"') +
          '<p class="kt-fehler" hidden></p><button type="submit" class="kt-btn voll">Ändern</button></form>';
        var g = unter.querySelector("form");
        g.addEventListener("submit", function (ev) {
          ev.preventDefault(); laedt(g, true);
          api("m_pw", { alt: g.alt.value, neu: g.neu.value }).then(function (r) {
            laedt(g, false);
            if (!r.ok) return fehler(g, r.fehler);
            setzeToken(r.sitzung); unter.innerHTML = "";
            meldung(box, "Passwort geändert. Andere Geräte sind jetzt abgemeldet.", "gut");
          });
        });
      });
      klick("ab", function () { abmelden(false); });
      klick("ab-alle", function () { if (confirm("Auf allen Geräten abmelden?")) abmelden(true); });
      klick("del", function () {
        unter.innerHTML = '<form class="kt-form" novalidate><p class="kt-klein links">Dein Konto und deine Profilangaben werden gelöscht. ' +
          "Deine Spielerseite bleibt mit den Standardangaben.</p>" + feld("pw", "Passwort zur Bestätigung", "password") +
          '<p class="kt-fehler" hidden></p><button type="submit" class="kt-btn rot voll">Endgültig löschen</button></form>';
        var g = unter.querySelector("form");
        g.addEventListener("submit", function (ev) {
          ev.preventDefault(); laedt(g, true);
          api("m_loeschen", { pw: g.pw.value }).then(function (r) {
            laedt(g, false);
            if (!r.ok) return fehler(g, r.fehler);
            setzeToken(""); location.href = PFAD + "index.html";
          });
        });
      });
    });
  }

  // ---------- Seite "Verwaltung" ----------
  function zeitText(ms) {
    if (!ms) return "noch nie";
    var t = (Date.now() - ms) / 1000;
    if (t < 3600) return "gerade eben";
    if (t < 86400) return "heute";
    var d = Math.round(t / 86400);
    return d === 1 ? "gestern" : d < 14 ? "vor " + d + " Tagen" : d < 60 ? "vor " + Math.round(d / 7) + " Wochen" : "vor " + Math.round(d / 30) + " Monaten";
  }
  function seiteVerwaltung(box) {
    if (!token()) return bitteAnmelden(box, "Die Verwaltung ist nur für Admins.");
    var reiter = (location.hash || "#antraege").slice(1), NUTZER = null, BERICHTE = null, TURNIERE = null, NUR_TURNIERE = false, LISTEN = null, TOUR = null, TOUR_WAHL = "", TOUR_EDIT = -1;
    function laden() {
      Promise.all([api("m_admin_liste"), api("b_liste"), api("m_turniere"), api("l_admin_liste")]).then(function (r) {
        // "Unbekannte Anfrage" = Apps Script noch ohne diese Funktion (keine neue Version bereitgestellt)
        TURNIERE = r[2].ok ? r[2] : { offen: [], rueckfrage: [], angenommen: [], alt: r[2].fehler === "Unbekannte Anfrage", kein: true };
        LISTEN = r[3].ok ? r[3] : { listen: [], alt: r[3].fehler === "Unbekannte Anfrage", kein: !r[0].ok };
        NUR_TURNIERE = !r[0].ok;                        // kein Admin: nur die Reiter seiner Rechte (turniere, listen)
        if (NUR_TURNIERE && !r[2].ok && !r[3].ok) return bitteAnmelden(box, r[0].fehler || "Kein Zugriff.");
        NUTZER = r[0].ok ? r[0] : { nutzer: [], rechte: [], ich: "", inhaber: false };
        if (NUR_TURNIERE && ["turniere", "listen"].indexOf(reiter) < 0) reiter = r[2].ok ? "turniere" : "listen";
        BERICHTE = r[1].ok ? r[1] : { offen: [], online: [] };
        zeichnen();
      });
    }
    function tourLaden() {
      TOUR = "laedt"; zeichnen();
      api("m_tour_daten").then(function (r) { TOUR = r.ok ? r : { fehlerText: r.fehler || "Nicht geladen" }; zeichnen(); });
    }
    function tourHtml() {
      if (!TOUR) return '<button type="button" class="kt-btn leise" data-tour="laden">Einträge anzeigen</button>';
      if (TOUR === "laedt") return '<p class="kt-klein links">Lädt …</p>';
      if (TOUR.fehlerText) return '<p class="kt-warn">' + esc(TOUR.fehlerText) + "</p>";
      var PR = {}, prSp = {};
      ((TOUR.pruefung || {}).eintraege || []).forEach(function (e) {
        var k = e.key; PR[[k.spieler, k.turnier, k.von, k.link, k.stadt].join("|")] = e.meldungen;
        var z = prSp[k.spieler] || (prSp[k.spieler] = { rot: 0, gelb: 0 });
        e.meldungen.forEach(function (m) { z[m.stufe === "rot" ? "rot" : "gelb"]++; });
      });
      function prVon(b) { return PR[[b.spieler, b.turnier || "", b.von || "", b.link || "", b.stadt || ""].join("|")] || []; }
      function zahlText(z) { return z ? [z.rot ? z.rot + (z.rot === 1 ? " Fehler" : " Fehler") : "", z.gelb ? z.gelb + (z.gelb === 1 ? " Hinweis" : " Hinweise") : ""].filter(Boolean).join(", ") : ""; }
      var sp = TOUR.spieler || {}, ids = Object.keys(sp).sort(function (x, y) { return (sp[x].name || x).localeCompare(sp[y].name || y, "de"); });
      var anzahl = function (sid) { return TOUR.besuche.filter(function (b) { return b.spieler === sid; }).length; };
      var mitMeldung = ids.filter(function (sid) { return prSp[sid]; }).sort(function (x, y) { return prSp[y].rot - prSp[x].rot || prSp[y].gelb - prSp[x].gelb; });
      var h = '<div class="kt-karte"><b>Prüfliste</b> <span class="kt-grau">' + (TOUR.pruefung && TOUR.pruefung.stand ? "Stand " + esc(TOUR.pruefung.stand) : "noch nicht erstellt (kommt mit dem nächsten Build)") + "</span>" +
        (mitMeldung.length ? '<div class="kt-pruef-sp">' + mitMeldung.map(function (sid) {
          return '<button type="button" class="kt-mini' + (prSp[sid].rot ? " rot" : "") + '" data-tour-sp="' + esc(sid) + '">' + esc(sp[sid].name || sid) + " · " + zahlText(prSp[sid]) + "</button>";
        }).join("") + "</div>" : '<p class="kt-gut" style="margin:.5rem 0 0">Alles in Ordnung.</p>') + "</div>";
      h += '<div class="kt-feld" style="max-width:24rem"><label>Spieler</label><select data-tour="wahl"><option value="">– wählen –</option>' +
        ids.map(function (sid) { return '<option value="' + esc(sid) + '"' + (sid === TOUR_WAHL ? " selected" : "") + ">" + esc(sp[sid].name || sid) + " (" + anzahl(sid) + ")" + (prSp[sid] ? " – " + zahlText(prSp[sid]) : "") + "</option>"; }).join("") + "</select></div>";
      if (TOUR_WAHL && sp[TOUR_WAHL]) {
        var liste = TOUR.besuche.map(function (b, i) { return { b: b, i: i }; }).filter(function (x) { return x.b.spieler === TOUR_WAHL; })
          .sort(function (x, y) { return String(y.b.von || "").localeCompare(String(x.b.von || "")); });
        h += liste.map(function (x) {
          var b = x.b, wann = String(b.von || "").length >= 7 ? b.von.slice(5, 7) + "." + b.von.slice(0, 4) : esc(b.von || "");
          var titel = b.link ? '<a href="' + esc(b.link) + '" target="_blank" rel="noopener">' + esc(b.turnier || "chess-results") + "</a>" : esc(b.turnier || "–");
          var karte = '<div class="kt-karte kt-antrag" data-ti="' + x.i + '"><div><b>' + esc(b.stadt || "?") + "</b>" + (b.land ? ' <span class="kt-grau">' + esc(b.land) + "</span>" : "") +
            (b.ausgeblendet ? ' <span class="kt-tag aus">ausgeblendet</span>' : "") + '<br><span class="kt-grau">' + titel + " · " + wann + (b.bedenkzeit ? " · " + esc(b.bedenkzeit) : "") + "</span></div><div>" +
            prVon(b).map(function (m) {
              return '<div class="' + (m.stufe === "rot" ? "kt-warn" : "kt-hinweis") + '">' + esc(m.text) +
                ' <button type="button" class="kt-link" data-ta="ok" data-code="' + esc(m.code) + '" data-text="' + esc(m.text) + '">Passt so</button></div>';
            }).join("") + "</div>" +
            '<div class="kt-zeile"><button type="button" class="kt-mini" data-ta="bearbeiten">Bearbeiten</button>' +
            '<button type="button" class="kt-mini" data-ta="' + (b.ausgeblendet ? "einblenden" : "ausblenden") + '">' + (b.ausgeblendet ? "Einblenden" : "Ausblenden") + "</button>" +
            '<button type="button" class="kt-mini rot" data-ta="loeschen">Löschen</button></div></div>';
          if (TOUR_EDIT === x.i) {
            karte += '<form class="kt-karte kt-form" data-tform="' + x.i + '" novalidate>' +
              feld("turnier", "Turnier", "text", 'value="' + esc(b.turnier || "") + '"') +
              feld("link", "chess-results-Link", "url", 'value="' + esc(b.link || "") + '"') +
              '<label class="kt-check"><input type="checkbox" name="cr_holen"> <span>Name und Datum neu von chess-results holen</span></label>' +
              feld("ort", "Ort", "text", 'value="' + esc([b.stadt, b.land].filter(Boolean).join(", ")) + '" placeholder="z. B. Berlin, Deutschland"') +
              feld("datum", "Datum (JJJJ-MM)", "text", 'value="' + esc(String(b.von || "").slice(0, 7)) + '"') +
              '<div class="kt-feld"><label>Bedenkzeit</label><select name="bedenkzeit">' + ["klassisch", "schnell", "blitz"].map(function (z) {
                return '<option value="' + z + '"' + (b.bedenkzeit === z ? " selected" : "") + ">" + z + "</option>"; }).join("") + "</select></div>" +
              feld("ausnahme", "Ausnahme (Begründung, z. B. Deutsche Hochschulmeisterschaft – leer = keine)", "text", 'value="' + esc(b.ausnahme === "ja" ? "ja" : b.ausnahme || "") + '"') +
              '<p class="kt-fehler" hidden></p><div class="kt-zeile"><button type="submit" class="kt-btn gruen">Speichern</button>' +
              '<button type="button" class="kt-btn leise" data-ta="abbrechen">Abbrechen</button></div></form>';
          }
          return karte;
        }).join("") || '<p class="kt-klein links">Keine Einträge.</p>';
        h += '<p style="margin-top:1rem"><button type="button" class="kt-mini rot" data-ta="profil_loeschen">Ganzes Profil löschen</button></p>';
      }
      if (TOUR.wartend && TOUR.wartend.length) h += '<h3 style="margin-top:1.5rem">Wartet auf den nächsten Build</h3><ul class="kt-klein links">' +
        TOUR.wartend.map(function (w) { return "<li>" + esc(w.was) + ' <span class="kt-grau">(' + esc(w.wer || "") + ", " + esc(w.zeit || "") + ")</span></li>"; }).join("") + "</ul>";
      if (TOUR.fehler && TOUR.fehler.length) h += '<h3 style="margin-top:1.5rem">Hat nicht geklappt</h3><ul class="kt-klein links">' +
        TOUR.fehler.map(function (w) { return '<li><span class="kt-warn">' + esc(w.fehler) + "</span> – " + esc(w.was) + ' <span class="kt-grau">(' + esc(w.zeit || "") + ")</span></li>"; }).join("") + "</ul>";
      return h;
    }
    function turnierKarte(t, art) {
      var wo = [t.stadt, t.land].filter(Boolean).join(", "), wann = t.monat ? datumKurz(t.monat + "-01").slice(3) : "";
      var turnier = t.turnier ? esc(t.turnier) : t.link ? "Turnier auf chess-results" : "";
      var zeile2 = [t.link ? '<a href="' + esc(t.link) + '" target="_blank" rel="noopener">' + turnier + "</a>" : turnier,
        esc(wo), esc(wann), esc(t.bedenkzeit || "")].filter(Boolean).join(" · ");
      var hinweis = art === "rueckfrage" ? '<div class="kt-warn">Rückfrage: ' + esc(t.rueckfrage || "bitte am PC prüfen") + "<br>Am PC: py afk_on_tour.py → [2]</div>"
        : art === "angenommen" ? '<div class="kt-gut">Angenommen von ' + esc(t.angenommen_von || "?") + " – wird beim nächsten Build eingetragen</div>"
        : t.ausnahme ? '<div class="kt-warn">Ausnahme beantragt: ' + esc(t.begruendung || "(ohne Begründung)") + "</div>"
        : t.bedenkzeit && t.bedenkzeit !== "klassisch" ? '<div class="kt-warn">Nicht klassisch und keine Ausnahme beantragt</div>'
        : t.link ? '<div class="kt-gut">Mit chess-results-Link – Ort und Datum kommen automatisch</div>' : '<div class="kt-grau">Ohne Link – Angaben bitte kurz prüfen</div>';
      var knoepfe = art === "angenommen" ? "<div></div>" : '<div class="kt-zeile">' +
        (art === "offen" ? '<button type="button" class="kt-btn gruen" data-t="annehmen">Annehmen</button>' : "") +
        '<button type="button" class="kt-btn rot" data-t="ablehnen">Ablehnen</button></div>';
      return '<div class="kt-karte kt-antrag" data-tdatei="' + esc(t.datei) + '"><div><b>' + esc(t.name) + '</b><br><span class="kt-grau">' + zeile2 +
        (t.eingereicht ? "<br>eingereicht " + datumKurz(t.eingereicht) : "") + "</span></div>" + hinweis + knoepfe + "</div>";
    }
    function tag(s) { return '<span class="kt-tag ' + s + '">' + { inhaber: "Inhaber", admin: "Admin", mitglied: "Mitglied" }[s] + "</span>"; }
    function datumKurz(iso) { var m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[3] + "." + m[2] + "." + m[1] : esc(iso || ""); }
    function zeichnen() {
      var a = NUTZER, inh = a.inhaber, n = a.nutzer;
      var offen = n.filter(function (x) { return x.status === "wartet"; });
      var aktiv = n.filter(function (x) { return x.status === "aktiv" && !x.ausgeblendet && !x.ausgetreten; });
      var weg = n.filter(function (x) { return x.status === "aktiv" && (x.ausgeblendet || x.ausgetreten); });
      var meld = box.querySelector(".kt-meldung"), alteMeldung = meld && !meld.hidden ? [meld.textContent, meld.className] : null;
      function aktionen(x) {
        if (x.stufe === "inhaber" || x.benutzer === a.ich) return [];
        var k = [], adminZiel = x.stufe === "admin";
        if (inh && !adminZiel) k.push(["zum_admin", "Zum Admin"]);
        if (inh && adminZiel) k.push(["zum_mitglied", "Zum Mitglied"]);
        if (inh || !adminZiel) {
          k.push(["pw_code", "Passwort-Code"]);
          k.push([x.ausgeblendet ? "einblenden" : "ausblenden", x.ausgeblendet ? "Einblenden" : "Ausblenden"]);
        }
        if (inh) k.push(["loeschen", "Löschen", "rot"]);
        return k;
      }
      function knopf(b, x) { return '<button type="button" class="kt-mini ' + (b[2] || "") + '" data-akt="' + b[0] + '" data-ziel="' + esc(x.benutzer) + '">' + b[1] + "</button>"; }
      function rechte(x) {
        if (x.stufe !== "mitglied") return '<span class="kt-recht">alle</span>';
        if (!inh) return x.rechte.length ? x.rechte.map(function (r) { return '<span class="kt-recht">' + esc(r) + "</span>"; }).join("") : "–";
        return a.rechte.map(function (r) {
          return '<label class="kt-recht-wahl"><input type="checkbox" data-recht="' + r + '" data-ziel="' + esc(x.benutzer) + '"' + (x.rechte.indexOf(r) >= 0 ? " checked" : "") + "> " + esc(r) + "</label>";
        }).join("");
      }
      function nutzerListe(liste) {
        if (!liste.length) return '<p class="kt-klein links">Keine.</p>';
        return '<div class="kt-nutzer">' + liste.map(function (x) {
          return '<div class="kt-karte kt-nk"><div class="kt-nk-kopf"><div><a href="' + PFAD + "spieler/" + esc(x.slug) + '.html"><b>' + esc(x.name) + "</b></a>" +
            (x.ausgetreten ? ' <span class="kt-tag aus">ausgetreten</span>' : x.ausgeblendet ? ' <span class="kt-tag aus">ausgeblendet</span>' : "") +
            '<br><span class="kt-grau">' + esc(x.benutzer) + " · " + zeitText(x.zuletzt) + "</span></div>" + tag(x.stufe) + "</div>" +
            '<div class="kt-nk-rechte"><span class="kt-grau">Rechte:</span> ' + rechte(x) + "</div>" +
            '<div class="kt-nk-akt">' + aktionen(x).map(function (b) { return knopf(b, x); }).join("") + "</div></div>";
        }).join("") + "</div>";
      }
      var B = BERICHTE, bOffen = B.offen || [], bOnline = B.online || [];
      function berichtZeile(e, offenListe) {
        var autor = e.autor ? esc(e.autor) + (e.konto ? ' <span class="kt-verifiziert" style="margin-left:.2rem">verifiziert</span>' : e.gast ? ' <span class="kt-tag mitglied">Gast</span>' : "") : "";
        var bearb = '<a class="kt-btn leise" href="' + PFAD + "bericht-schreiben.html?bearbeiten=" + encodeURIComponent(e.id) + '">' + (offenListe ? "Ansehen" : "Bearbeiten") + "</a>";
        if (offenListe) {
          return '<div class="kt-karte kt-antrag" data-bid="' + esc(e.id) + '"><div><b>' + esc(e.titel) + '</b><br><span class="kt-grau">' + (autor ? "von " + autor + " · " : "") + datumKurz(e.datum) + "</span></div>" +
            (e.gast && e.autor ? '<div><label class="kt-check" style="margin:0"><input type="checkbox" name="autorOk"> <span>Autor ist wirklich <b>' + esc(e.autor) + "</b> (Profil verlinken)</span></label></div>"
              : e.konto ? '<div class="kt-gut">Eingeloggt geschrieben – Autor sicher</div>' : "<div></div>") +
            '<div class="kt-zeile">' + bearb + '<button type="button" class="kt-btn gruen" data-b="veroeffentlichen">Freigeben</button>' +
            '<button type="button" class="kt-btn rot" data-b="loeschen">Löschen</button></div></div>';
        }
        return '<tr data-bid="' + esc(e.id) + '"><td><b>' + esc(e.titel) + '</b> <span class="kt-grau">· ' + (autor ? autor + " · " : "") + datumKurz(e.datum) + "</span></td>" +
          '<td class="kt-akt"><a class="kt-mini" href="' + PFAD + "bericht-schreiben.html?bearbeiten=" + encodeURIComponent(e.id) + '">Bearbeiten</a>' +
          '<button type="button" class="kt-mini rot" data-b="zurueckziehen">Zurückziehen</button></td></tr>';
      }
      function r(name, titel, zahl) {
        return '<button type="button" data-r="' + name + '"' + (reiter === name ? ' class="an"' : "") + ">" + titel + (zahl ? " <em>" + zahl + "</em>" : "") + "</button>";
      }
      function teil(name, html) { return '<div class="kt-reiter-inhalt" data-r="' + name + '"' + (reiter === name ? "" : " hidden") + ">" + html + "</div>"; }
      var T = TURNIERE, tOffen = T.offen.length + T.rueckfrage.length + (T.pruefFehler || 0);
      var turnierTeil = teil("turniere", (T.alt ? '<p class="kt-warn">Das Apps Script kennt die Turnier-Anträge noch nicht: Code.gs und Mitglieder.gs ersetzen, ' +
          "speichern und „Bereitstellen → Bereitstellungen verwalten → Stift → Neue Version“.</p>" : "") +
        "<h3>Offen</h3>" + (T.offen.length ? T.offen.map(function (t) { return turnierKarte(t, "offen"); }).join("") : '<p class="kt-klein links">Keine offenen Anträge.</p>') +
        (T.rueckfrage.length ? '<h3 style="margin-top:1.8rem">Rückfragen</h3>' + T.rueckfrage.map(function (t) { return turnierKarte(t, "rueckfrage"); }).join("") : "") +
        (T.angenommen.length ? '<h3 style="margin-top:1.8rem">Wird gerade eingetragen</h3>' + T.angenommen.map(function (t) { return turnierKarte(t, "angenommen"); }).join("") : "") +
        '<p class="kt-klein links">„Annehmen“: Der nächste Build (startet von selbst, dauert ein paar Minuten) holt Ort und Datum von chess-results bzw. der Karte und trägt das Turnier ein. ' +
        "Ist etwas unklar (Ort nicht gefunden, Name ähnlich wie ein bestehendes Profil), landet der Antrag unter „Rückfragen“.</p>" +
        '<h3 style="margin-top:2.2rem">Alle Einträge bearbeiten</h3><div class="kt-tour">' + tourHtml() + "</div>" +
        '<p class="kt-klein links">Änderungen übernimmt der nächste Build (startet von selbst, ein paar Minuten). Einen neuen Ort sucht er auf der Karte, ' +
        "neue Turniere kommen über das Formular auf der AFK-on-Tour-Seite.</p>");
      if (reiter === "turniere" && !TOUR) { TOUR = "laedt"; api("m_tour_daten").then(function (r) { TOUR = r.ok ? r : { fehlerText: r.fehler || "Nicht geladen" }; zeichnen(); }); }
      var listenTeil = teil("listen", "");
      if (NUR_TURNIERE) {
        box.innerHTML = '<p class="kt-meldung" hidden></p><div class="kt-reiter" role="tablist">' +
          (TURNIERE.kein ? "" : r("turniere", "Turniere", tOffen)) + (LISTEN.kein ? "" : r("listen", "Listen")) + "</div>" +
          (TURNIERE.kein ? "" : turnierTeil) + (LISTEN.kein ? "" : listenTeil);
      } else
      box.innerHTML = '<p class="kt-unter">Angemeldet als <b>' + esc(a.ich) + "</b> " + tag(inh ? "inhaber" : "admin") + "</p>" +
        '<p class="kt-meldung" hidden></p>' +
        '<div class="kt-reiter" role="tablist">' + r("antraege", "Anträge", offen.length) + r("berichte", "Berichte", bOffen.length) +
        r("turniere", "Turniere", tOffen) + r("listen", "Listen") +
        r("nutzer", "Nutzer (" + aktiv.length + ")") + r("weg", "Ausgeblendet / ausgetreten (" + weg.length + ")") + "</div>" + turnierTeil + listenTeil +
        teil("antraege", offen.length ? offen.map(function (x) {
          return '<div class="kt-karte kt-antrag"><div><b>' + esc(x.name) + '</b><br><span class="kt-grau">Benutzername ' + esc(x.benutzer) + " · " + zeitText(x.seit) + "</span></div>" +
            '<div class="kt-gut">Name und Geburtsdatum stimmen mit der Mitgliederliste überein</div>' +
            '<div class="kt-zeile"><button type="button" class="kt-btn gruen" data-akt="annehmen" data-ziel="' + esc(x.benutzer) + '">Annehmen</button>' +
            '<button type="button" class="kt-btn rot" data-akt="ablehnen" data-ziel="' + esc(x.benutzer) + '">Ablehnen</button></div></div>';
        }).join("") : '<p class="kt-klein links">Keine offenen Anträge.</p>') +
        teil("berichte", "<h3>Warten auf Freigabe</h3>" + (bOffen.length ? bOffen.map(function (e) { return berichtZeile(e, true); }).join("") : '<p class="kt-klein links">Keine Entwürfe.</p>') +
          '<h3 style="margin-top:1.8rem">Online</h3>' + (bOnline.length ? '<div class="kt-karte kt-tabelle-rahmen"><table class="kt-tab">' + bOnline.map(function (e) { return berichtZeile(e, false); }).join("") + "</table></div>"
            : '<p class="kt-klein links">Keine.</p>') +
          '<p class="kt-klein links">Hier stehen alle Berichte von diesem und letztem Jahr. „Zurückziehen“ macht einen Bericht wieder zum Entwurf; endgültig löschen geht bei Entwürfen.</p>') +
        teil("nutzer", nutzerListe(aktiv) + '<p class="kt-klein links">' + (inh ? "Rechte: <b>geburtstage</b> = alle Geburtstage sehen, <b>berichte</b> = Berichte ohne Freigabe veröffentlichen, <b>turniere</b> = AFK-on-Tour-Anträge annehmen, <b>listen</b> = Listen (Sommerfest …) anlegen. Admins haben alle Rechte."
          : "Stufen und Rechte kann nur der Inhaber ändern.") + "</p>") +
        teil("weg", nutzerListe(weg) + '<p class="kt-klein links">Ausgetreten = steht nicht mehr in der Mitgliederliste. Diese Konten können sich nicht anmelden; das Profil ist ausgeblendet.</p>');
      if (box.querySelector('[data-r="listen"].kt-reiter-inhalt')) listenVerwaltung(box, LISTEN, zeichnen, fertig);
      if (alteMeldung) { var m2 = box.querySelector(".kt-meldung"); m2.textContent = alteMeldung[0]; m2.className = alteMeldung[1]; m2.hidden = false; }
      [].forEach.call(box.querySelectorAll(".kt-reiter button"), function (b) {
        b.addEventListener("click", function () {
          reiter = b.getAttribute("data-r"); history.replaceState(null, "", "#" + reiter);
          if (reiter === "turniere" && !TOUR) return zeichnen();
          [].forEach.call(box.querySelectorAll(".kt-reiter button"), function (x) { x.classList.toggle("an", x === b); });
          [].forEach.call(box.querySelectorAll(".kt-reiter-inhalt"), function (x) { x.hidden = x.getAttribute("data-r") !== reiter; });
        });
      });
      function fertig(r) {
        meldung(box, r.ok ? r.meldung : r.fehler, r.ok ? (r.code ? "code" : "gut") : "schlecht");
        if (r.ok) { try { localStorage.removeItem(ICH_KEY); } catch (e) {} laden(); ich(true).then(knopfZeigen); }
      }
      [].forEach.call(box.querySelectorAll("[data-akt]"), function (b) {
        b.addEventListener("click", function () {
          var akt = b.getAttribute("data-akt"), ziel = b.getAttribute("data-ziel");
          var fragen = { loeschen: "Konto von „" + ziel + "“ endgültig löschen?", zum_admin: "„" + ziel + "“ zum Admin machen?", ablehnen: "Registrierung von „" + ziel + "“ ablehnen?" };
          if (fragen[akt] && !confirm(fragen[akt])) return;
          b.disabled = true;
          api("m_admin", { aktion: akt, ziel: ziel }).then(function (r) { b.disabled = false; fertig(r); });
        });
      });
      [].forEach.call(box.querySelectorAll("[data-recht]"), function (c) {    // Rechte: Häkchen speichert sofort
        c.addEventListener("change", function () {
          var ziel = c.getAttribute("data-ziel");
          var liste = [].map.call(box.querySelectorAll('[data-recht][data-ziel="' + ziel + '"]:checked'), function (x) { return x.getAttribute("data-recht"); });
          api("m_admin", { aktion: "rechte", ziel: ziel, rechte: liste }).then(fertig);
        });
      });
      var tl = box.querySelector('[data-tour="laden"]'); if (tl) tl.addEventListener("click", tourLaden);
      [].forEach.call(box.querySelectorAll("[data-tour-sp]"), function (k) {
        k.addEventListener("click", function () { TOUR_WAHL = k.getAttribute("data-tour-sp"); TOUR_EDIT = -1; zeichnen(); });
      });
      var tw = box.querySelector('[data-tour="wahl"]'); if (tw) tw.addEventListener("change", function () { TOUR_WAHL = tw.value; TOUR_EDIT = -1; zeichnen(); });
      function tourSenden(aktion, b, werte, knoepfe, zusatz) {
        var sp = TOUR.spieler[TOUR_WAHL] || {};
        var key = b ? { spieler: b.spieler, turnier: b.turnier || "", von: b.von || "", link: b.link || "", stadt: b.stadt || "" } : { spieler: TOUR_WAHL };
        [].forEach.call(knoepfe || [], function (x) { x.disabled = true; });
        api("m_tour_aendern", { aktion: aktion, key: key, sid: TOUR_WAHL, werte: werte || {},
          beschreibung: (sp.name || TOUR_WAHL) + (b ? ", " + (b.stadt || "") + " " + String(b.von || "").slice(0, 7) : "") + (zusatz ? " – " + zusatz : "") }).then(function (r) {
          [].forEach.call(knoepfe || [], function (x) { x.disabled = false; });
          if (r.ok) { TOUR_EDIT = -1; TOUR = null; tourLaden(); }
          fertig(r);
        });
      }
      [].forEach.call(box.querySelectorAll("[data-ta]"), function (k) {
        k.addEventListener("click", function () {
          var was = k.getAttribute("data-ta"), el = k.closest("[data-ti]"), i = el ? +el.getAttribute("data-ti") : -1, b = i >= 0 ? TOUR.besuche[i] : null;
          if (was === "bearbeiten") { TOUR_EDIT = i; return zeichnen(); }
          if (was === "abbrechen") { TOUR_EDIT = -1; return zeichnen(); }
          if (was === "ok") return tourSenden("ok", b, { code: k.getAttribute("data-code") }, [k], k.getAttribute("data-text"));
          if (was === "loeschen" && !confirm("Eintrag " + (b.stadt || "") + " (" + (b.turnier || "") + ") löschen?")) return;
          if (was === "profil_loeschen" && !confirm("Profil „" + ((TOUR.spieler[TOUR_WAHL] || {}).name || TOUR_WAHL) + "“ mit allen Einträgen löschen?")) return;
          tourSenden(was, b, null, [k]);
        });
      });
      var tf = box.querySelector("[data-tform]");
      if (tf) tf.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var b = TOUR.besuche[+tf.getAttribute("data-tform")], w = {};
        var v = function (n) { return (tf.elements[n].value || "").trim(); };
        if (v("turnier") && v("turnier") !== (b.turnier || "")) w.turnier = v("turnier");
        if (v("link") !== (b.link || "") || tf.cr_holen.checked) { w.link = v("link"); w.cr_holen = tf.cr_holen.checked; }
        if (v("ort") && v("ort") !== [b.stadt, b.land].filter(Boolean).join(", ")) w.ort = v("ort");
        if (v("datum") && v("datum") !== String(b.von || "").slice(0, 7)) w.datum = v("datum");
        if (v("bedenkzeit") !== (b.bedenkzeit || "")) w.bedenkzeit = v("bedenkzeit");
        if (v("ausnahme") !== (b.ausnahme || "")) w.ausnahme = v("ausnahme");
        if (!Object.keys(w).length) return fehler(tf, "Nichts geändert.");
        tourSenden("aendern", b, w, tf.querySelectorAll("button"));
      });
      [].forEach.call(box.querySelectorAll("[data-t]"), function (b) {
        b.addEventListener("click", function () {
          var el = b.closest("[data-tdatei]"), was = b.getAttribute("data-t"), name = el.querySelector("b").textContent;
          if (was === "ablehnen" && !confirm("Antrag von „" + name + "“ ablehnen? Er wird gelöscht.")) return;
          [].forEach.call(el.querySelectorAll("button"), function (x) { x.disabled = true; });
          api("m_turnier", { aktion: was, datei: el.getAttribute("data-tdatei") }).then(function (r) {
            [].forEach.call(el.querySelectorAll("button"), function (x) { x.disabled = false; }); fertig(r);
          });
        });
      });
      [].forEach.call(box.querySelectorAll("[data-b]"), function (b) {
        b.addEventListener("click", function () {
          var el = b.closest("[data-bid]"), id = el.getAttribute("data-bid"), was = b.getAttribute("data-b");
          var titel = el.querySelector("b").textContent;
          if (was === "loeschen" && !confirm("„" + titel + "“ endgültig löschen? Das geht nicht rückgängig.")) return;
          if (was === "zurueckziehen" && !confirm("„" + titel + "“ zurückziehen? Er verschwindet beim nächsten Build von der Website.")) return;
          var ok = el.querySelector("[name=autorOk]");
          b.disabled = true;
          api("b_status", { id: id, aktion: was, autorOk: ok ? ok.checked : false }).then(function (r) { b.disabled = false; fertig(r); });
        });
      });
    }
    box.innerHTML = '<p class="kt-klein links">Lädt …</p>';
    laden();
  }

  // ---------- Listen (Sommerfest, Zusagen, Helfer …) ----------
  var L_ARTEN = { text: "Text", zahl: "Zahl", auswahl: "Auswahl (eigene Optionen)", jnv: "Ja / Nein / Vielleicht", aufgaben: "Aufgaben zum Übernehmen" };
  var L_VORLAGEN = {
    leer: { titel: "", felder: [] },
    sommerfest: { titel: "Sommerfest", felder: [
      { name: "Personen", art: "zahl", pflicht: true, summe: true }, { name: "Bringe mit", art: "text" },
      { name: "Grillwunsch", art: "auswahl", optionen: ["Wurst", "Steak", "vegetarisch"], summe: true },
      { name: "Wer übernimmt was", art: "aufgaben", optionen: ["Getränke kaufen", "Grill aufbauen", "Kuchen"] }] },
    zusage: { titel: "Zusage", felder: [{ name: "Ich komme", art: "jnv", pflicht: true, summe: true }, { name: "Kommentar", art: "text" }] },
    helfer: { titel: "Helfer", felder: [{ name: "Aufgabe", art: "aufgaben", optionen: ["Aufbau", "Abbau", "Kasse"], pflicht: true }, { name: "Kommentar", art: "text" }] },
    fahrt: { titel: "Fahrgemeinschaft", felder: [{ name: "Ich bin", art: "auswahl", optionen: ["Fahrer", "Mitfahrer"], pflicht: true, summe: true },
      { name: "Freie Plätze", art: "zahl", summe: true }, { name: "Abfahrt von", art: "text" }] }
  };
  var L_STATUS = { entwurf: "Entwurf", verwaltung: "nur Verwaltung", geplant: "geplant", sichtbar: "sichtbar", beendet: "beendet" };
  function zweistellig(n) { return ("0" + n).slice(-2); }
  function zeitKurz(ms) { if (!ms) return ""; var d = new Date(ms); return zweistellig(d.getDate()) + "." + zweistellig(d.getMonth() + 1) + ". " + zweistellig(d.getHours()) + ":" + zweistellig(d.getMinutes()); }
  function datumDe(iso) { var m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[3] + "." + m[2] + "." + m[1] : ""; }
  function lStatusText(l) {
    if (l.status === "sichtbar") return l.sofort || !l.bis ? "sichtbar" : "sichtbar bis " + datumDe(l.bis);
    if (l.status === "geplant") return "ab " + datumDe(l.von) + " sichtbar";
    return L_STATUS[l.status] || l.status;
  }
  function wertText(f, v) {
    if (v == null || v === "") return "";
    return Array.isArray(v) ? v.join(", ") : String(v);
  }
  function verlauf(e) {
    var t = [];
    (e.frueher || []).forEach(function (x) { t.push("erstellt " + zeitKurz(x.erstellt), "gelöscht " + zeitKurz(x.geloescht)); });
    t.push((t.length ? "neu erstellt " : "erstellt ") + zeitKurz(e.erstellt));
    (e.bearbeitet || []).forEach(function (b, i) { t.push((i + 1) + ". Bearbeitung " + zeitKurz(b)); });
    return t.join(" · ");
  }

  function seiteListen(box) {
    if (!token()) return bitteAnmelden(box, "Listen sind nur für angemeldete Mitglieder.");
    var id = new URLSearchParams(location.search).get("id");
    box.innerHTML = '<p class="kt-klein links">Lädt …</p>';
    if (!id) {
      return api("l_laden", {}).then(function (r) {
        if (!r.ok) return bitteAnmelden(box, r.fehler);
        box.innerHTML = r.listen.length ? '<div class="kt-nutzer">' + r.listen.map(function (l) {
          return '<a class="kt-karte ls-karte" href="?id=' + encodeURIComponent(l.id) + '"><b>' + esc(l.titel) + '</b><span class="kt-grau">' + esc(lStatusText(l)) + "</span></a>";
        }).join("") + "</div>" : '<p class="kt-klein links">Gerade gibt es keine offenen Listen.</p>';
      });
    }
    function laden() { return api("l_laden", { id: id }).then(function (r) { if (!r.ok) return meldung(box, r.fehler, "schlecht"); zeichnen(r); }); }
    function zeichnen(r) {
      var L = r.liste, F = L.felder, E = r.eintraege, aktiv = E.filter(function (e) { return !e.geloescht; });
      var ich = E.filter(function (e) { return e.ich && !e.geloescht; })[0];
      document.title = L.titel + " – SG AFK";
      var h1 = document.querySelector("main h1, h1"); if (h1) h1.textContent = L.titel;
      var html = '<p class="kt-unter">' + esc(lStatusText(L)) + " · nur für angemeldete Mitglieder</p>" +
        (L.status !== "sichtbar" ? '<p class="kt-warn">Diese Liste sehen gerade nur Verwaltung und Listen-Berechtigte.</p>' : "") +
        (L.text ? '<div class="ls-text">' + textHtml(L.text) + "</div>" : "") + '<p class="kt-meldung" hidden></p>';
      // Summen
      var sum = ['<div><b>' + aktiv.length + "</b>Einträge</div>"];
      F.forEach(function (f) {
        if (!f.summe) return;
        if (f.art === "zahl") sum.push("<div><b>" + aktiv.reduce(function (s, e) { return s + (Number(e.werte[f.id]) || 0); }, 0) + "</b>" + esc(f.name) + "</div>");
        else (f.art === "jnv" ? ["Ja", "Nein", "Vielleicht"] : f.optionen).forEach(function (o) {
          var n = aktiv.filter(function (e) { return e.werte[f.id] === o; }).length;
          if (n) sum.push("<div><b>" + n + "</b>" + esc(f.art === "jnv" ? f.name + ": " + o : o) + "</div>");
        });
      });
      html += '<div class="ls-sum">' + sum.join("") + "</div>";
      // Doppelte in Textspalten
      F.forEach(function (f) {
        if (f.art !== "text") return;
        var z = {};
        aktiv.forEach(function (e) { String(e.werte[f.id] || "").split(/,|\bund\b/).forEach(function (t) { t = t.trim(); if (t) { var k = t.toLowerCase(); z[k] = z[k] || { t: t, n: 0 }; z[k].n++; } }); });
        Object.keys(z).forEach(function (k) { if (z[k].n > 1) html += '<p class="kt-hinweis">Hinweis: „' + esc(z[k].t) + "“ steht bei „" + esc(f.name) + "“ schon " + z[k].n + "×.</p>"; });
      });
      // Eigener Eintrag
      if (r.darfEintragen) {
        html += '<form class="kt-karte kt-form ls-form" novalidate><b>Dein Eintrag</b><div class="ls-felder">' + F.map(function (f) {
          var v = ich ? ich.werte[f.id] : undefined, lab = esc(f.name) + (f.pflicht ? " *" : "");
          if (f.art === "aufgaben") return '<div class="kt-feld ls-breit"><label>' + lab + "</label>" + f.optionen.map(function (o) {
            return '<label class="kt-check" style="display:inline-flex;margin-right:1rem"><input type="checkbox" name="' + f.id + '" value="' + esc(o) + '"' + (v && v.indexOf(o) >= 0 ? " checked" : "") + "> <span>" + esc(o) + "</span></label>"; }).join("") + "</div>";
          if (f.art === "auswahl" || f.art === "jnv") return '<div class="kt-feld"><label>' + lab + '</label><select name="' + f.id + '"><option value="">–</option>' +
            (f.art === "jnv" ? ["Ja", "Nein", "Vielleicht"] : f.optionen).map(function (o) { return '<option' + (v === o ? " selected" : "") + ">" + esc(o) + "</option>"; }).join("") + "</select></div>";
          return '<div class="kt-feld' + (f.art === "text" ? " ls-breit" : "") + '"><label>' + lab + '</label><input name="' + f.id + '" type="' + (f.art === "zahl" ? "number" : "text") + '" min="0" value="' + esc(v == null ? "" : v) + '"></div>';
        }).join("") + '</div><p class="kt-fehler" hidden></p><div class="kt-zeile"><button type="submit" class="kt-btn gruen">' + (ich ? "Änderung speichern" : "Eintragen") + "</button>" +
          (ich ? '<button type="button" class="kt-btn rot" data-l="weg">Eintrag löschen</button>' : "") + "</div></form>";
      }
      // Aufgaben
      F.filter(function (f) { return f.art === "aufgaben"; }).forEach(function (f) {
        html += '<h3 style="margin-top:1.6rem">' + esc(f.name) + '</h3><div class="kt-karte ls-auf">' + f.optionen.map(function (o) {
          var wer = aktiv.filter(function (e) { return (e.werte[f.id] || []).indexOf(o) >= 0; });
          var meins = ich && (ich.werte[f.id] || []).indexOf(o) >= 0;
          return "<div>" + esc(o) + "</div><div>" + (wer.length ? esc(wer.map(function (e) { return e.name; }).join(", ")) : '<span class="ls-frei">frei</span>') +
            (r.darfEintragen && !meins ? ' <button type="button" class="kt-mini" data-uebernehmen="' + esc(f.id) + '" data-opt="' + esc(o) + '">Übernehmen</button>' : "") + "</div>";
        }).join("") + "</div>";
      });
      // Alle Einträge
      html += '<div class="ls-kopfzeile"><h3>Alle Einträge</h3>' + (r.verwalter ? '<span class="ls-knoepfe"><button type="button" class="kt-mini" data-l="csv">Excel (CSV)</button>' +
        '<button type="button" class="kt-mini" data-l="druck">Drucken / PDF</button></span>' : "") + "</div>";
      html += '<div class="kt-karte kt-tabelle-rahmen"><table class="ls-tab"><tr><th>Name</th>' + F.map(function (f) { return "<th>" + esc(f.name) + "</th>"; }).join("") + "</tr>" +
        (E.length ? E.map(function (e) {
          if (e.geloescht) return '<tr class="weg"><td>' + esc(e.name) + '</td><td colspan="' + F.length + '">hat den Eintrag am ' + zeitKurz(e.geloescht) + " gelöscht (" + verlauf(e) + ")</td></tr>";
          return '<tr' + (e.ich ? ' class="ich"' : "") + "><td><b>" + esc(e.name) + '</b><span class="ls-zeit">' + verlauf(e) + "</span></td>" +
            F.map(function (f) { return "<td>" + esc(wertText(f, e.werte[f.id])) + "</td>"; }).join("") + "</tr>";
        }).join("") : '<tr><td colspan="' + (F.length + 1) + '" class="kt-grau">Noch niemand eingetragen.</td></tr>') + "</table></div>";
      box.innerHTML = html;
      var form = box.querySelector(".ls-form");
      function senden(zusatz) {
        var w = {};
        F.forEach(function (f) {
          if (f.art === "aufgaben") w[f.id] = [].map.call(form.querySelectorAll('[name="' + f.id + '"]:checked'), function (x) { return x.value; });
          else w[f.id] = (form.elements[f.id].value || "").trim();
        });
        if (zusatz) w[zusatz[0]] = (w[zusatz[0]] || []).concat([zusatz[1]]);
        laedt(form, true);
        api("l_eintragen", { id: id, werte: w }).then(function (a) {
          laedt(form, false);
          if (!a.ok) { fehler(form, a.fehler); form.scrollIntoView({ block: "center" }); return; }
          laden().then(function () { meldung(box, a.meldung, "gut"); });
        });
      }
      if (form) form.addEventListener("submit", function (ev) { ev.preventDefault(); senden(); });
      [].forEach.call(box.querySelectorAll("[data-uebernehmen]"), function (k) {
        k.addEventListener("click", function () { senden([k.getAttribute("data-uebernehmen"), k.getAttribute("data-opt")]); });
      });
      var weg = box.querySelector('[data-l="weg"]');
      if (weg) weg.addEventListener("click", function () {
        if (!confirm("Deinen Eintrag löschen? Alle sehen dann, dass du ihn gelöscht hast.")) return;
        api("l_loeschen", { id: id }).then(function (a) { if (!a.ok) return meldung(box, a.fehler, "schlecht"); laden().then(function () { meldung(box, a.meldung, "gut"); }); });
      });
      var csv = box.querySelector('[data-l="csv"]');
      if (csv) csv.addEventListener("click", function () {
        var q = function (s) { s = String(s == null ? "" : s); return /[";\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
        var zeilen = [["Name"].concat(F.map(function (f) { return f.name; }), ["Erstellt", "Zuletzt geändert", "Gelöscht"])];
        E.forEach(function (e) {
          zeilen.push([e.name].concat(F.map(function (f) { return wertText(f, e.werte[f.id]); }),
            [zeitKurz(e.erstellt), zeitKurz((e.bearbeitet || []).slice(-1)[0]), zeitKurz(e.geloescht)]));
        });
        var blob = new Blob(["﻿" + zeilen.map(function (z) { return z.map(q).join(";"); }).join("\r\n")], { type: "text/csv;charset=utf-8" });
        var a = document.createElement("a"); a.href = URL.createObjectURL(blob);
        a.download = L.titel.replace(/[^\wäöüÄÖÜß -]+/g, "").trim() + ".csv"; document.body.appendChild(a); a.click(); a.remove();
      });
      var druck = box.querySelector('[data-l="druck"]');
      if (druck) druck.addEventListener("click", function () { window.print(); });
    }
    laden();
  }

  // Verwaltung -> Reiter "Listen"
  function listenVerwaltung(box, LISTEN, neuZeichnen, fertig) {
    var S = listenVerwaltung.S || (listenVerwaltung.S = { edit: null });
    function feldZeile(f, i) {
      var opt = f.art === "auswahl" || f.art === "aufgaben";
      return '<div class="ls-feldzeile" data-fi="' + i + '"><input data-f="name" value="' + esc(f.name || "") + '" placeholder="Spaltenname">' +
        '<select data-f="art">' + Object.keys(L_ARTEN).map(function (a) { return '<option value="' + a + '"' + (f.art === a ? " selected" : "") + ">" + L_ARTEN[a] + "</option>"; }).join("") + "</select>" +
        '<input data-f="optionen" value="' + esc((f.optionen || []).join(", ")) + '" placeholder="Optionen mit Komma"' + (opt ? "" : ' class="ls-unsichtbar" tabindex="-1"') + ">" +
        '<label title="Pflicht"><input type="checkbox" data-f="pflicht"' + (f.pflicht ? " checked" : "") + "> Pflicht</label>" +
        '<label title="Summe oben anzeigen"><input type="checkbox" data-f="summe"' + (f.summe ? " checked" : "") + (f.art === "text" || f.art === "aufgaben" ? " disabled" : "") + "> Summe</label>" +
        '<button type="button" class="kt-mini rot" data-fweg="' + i + '">×</button></div>';
    }
    function editor() {
      var l = S.edit;
      return '<form class="kt-karte kt-form ls-editor" novalidate><b>' + (l.id ? "Liste bearbeiten" : "Neue Liste") + "</b>" +
        '<div class="ls-editor-kopf">' + feld("ltitel", "Titel", "text", 'value="' + esc(l.titel || "") + '"') +
        '<div class="kt-feld"><label>Sichtbar für</label><select name="sicht">' +
        [["entwurf", "niemand (Entwurf)"], ["verwaltung", "nur Verwaltung (zum Testen)"], ["mitglieder", "alle angemeldeten Mitglieder"]].map(function (o) {
          return '<option value="' + o[0] + '"' + (l.sicht === o[0] ? " selected" : "") + ">" + o[1] + "</option>"; }).join("") + "</select></div>" +
        feld("von", "Sichtbar ab", "date", 'value="' + esc(l.von || "") + '"') + feld("bis", "bis", "date", 'value="' + esc(l.bis || "") + '"') + "</div>" +
        '<div class="kt-feld"><label for="kt-ltext">Text</label><textarea id="kt-ltext" name="ltext" style="min-height:70px">' + esc(l.text || "") + "</textarea></div>" +
        '<label class="kt-check"><input type="checkbox" name="sofort"' + (l.sofort ? " checked" : "") + "> <span>Sofort sichtbar (Zeitraum ignorieren)</span></label>" +
        '<label class="kt-check"><input type="checkbox" name="startseite"' + (l.startseite ? " checked" : "") + "> <span>Auf der Startseite anzeigen (für angemeldete Mitglieder)</span></label>" +
        '<h3 style="margin-top:1.2rem">Spalten</h3><p class="kt-klein links">Der Name steht immer dabei. Spalten frei benennen; „Summe“ zeigt oben Gesamtzahl bzw. Anzahl je Option.</p>' +
        '<div class="ls-felderliste">' + (l.felder || []).map(feldZeile).join("") + "</div>" +
        '<p><button type="button" class="kt-mini" data-l="feld">+ Spalte</button></p>' +
        '<p class="kt-fehler" hidden></p><div class="kt-zeile"><button type="submit" class="kt-btn gruen">Speichern</button>' +
        '<button type="button" class="kt-btn leise" data-l="abbrechen">Abbrechen</button>' +
        (l.id ? '<button type="button" class="kt-btn rot" data-l="loeschen">Liste löschen</button>' : "") + "</div></form>";
    }
    function lesen(form) {
      var l = S.edit;
      l.titel = form.elements.ltitel.value.trim(); l.text = form.elements.ltext.value; l.sicht = form.elements.sicht.value;
      l.von = form.elements.von.value; l.bis = form.elements.bis.value; l.sofort = form.elements.sofort.checked; l.startseite = form.elements.startseite.checked;
      l.felder = [].map.call(form.querySelectorAll("[data-fi]"), function (z) {
        var alt = l.felder[+z.getAttribute("data-fi")] || {}, g = function (n) { return z.querySelector('[data-f="' + n + '"]'); };
        return { id: alt.id || "", name: g("name").value.trim(), art: g("art").value, pflicht: g("pflicht").checked, summe: g("summe").checked,
          optionen: g("optionen").value.split(",").map(function (o) { return o.trim(); }).filter(Boolean) };
      });
      return l;
    }
    var html = "";
    if (LISTEN && LISTEN.alt) html += '<p class="kt-warn">Das Apps Script kennt die Listen noch nicht: Listen.gs anlegen, Code.gs und Mitglieder.gs ersetzen, neue Version bereitstellen.</p>';
    var listen = (LISTEN && LISTEN.listen) || [];
    html += listen.length ? '<div class="kt-karte kt-tabelle-rahmen"><table class="ls-tab"><tr><th>Liste</th><th>Status</th><th>Einträge</th><th></th></tr>' + listen.map(function (l) {
      return '<tr><td><b>' + esc(l.titel) + '</b></td><td><span class="ls-status ' + l.status + '">' + esc(lStatusText(l)) + "</span></td><td>" + l.eintraege + "</td>" +
        '<td class="kt-akt"><button type="button" class="kt-mini" data-lbearb="' + esc(l.id) + '">Bearbeiten</button>' +
        '<a class="kt-mini" href="' + PFAD + "listen.html?id=" + encodeURIComponent(l.id) + '">Ansehen / Auswertung</a></td></tr>';
    }).join("") + "</table></div>" : '<p class="kt-klein links">Noch keine Listen.</p>';
    if (!S.edit) html += '<p class="kt-zeile" style="align-items:center"><button type="button" class="kt-btn gruen" data-l="neu">Neue Liste</button> <span class="kt-grau">Vorlage</span> <select data-l="vorlage">' +
      [["leer", "leer"], ["sommerfest", "Sommerfest"], ["zusage", "Zusage (ich komme / nicht)"], ["helfer", "Helferliste"], ["fahrt", "Fahrgemeinschaft"]].map(function (v) {
        return '<option value="' + v[0] + '">' + v[1] + "</option>"; }).join("") + "</select></p>";
    else html += editor();
    var teil = box.querySelector('[data-r="listen"].kt-reiter-inhalt');
    teil.innerHTML = html;
    var neu = teil.querySelector('[data-l="neu"]');
    if (neu) neu.addEventListener("click", function () {
      var v = L_VORLAGEN[teil.querySelector('[data-l="vorlage"]').value];
      S.edit = { titel: v.titel, felder: JSON.parse(JSON.stringify(v.felder)), sicht: "entwurf" }; neuZeichnen();
    });
    [].forEach.call(teil.querySelectorAll("[data-lbearb]"), function (k) {
      k.addEventListener("click", function () {
        var l = listen.filter(function (x) { return x.id === k.getAttribute("data-lbearb"); })[0];
        S.edit = JSON.parse(JSON.stringify(l.liste)); neuZeichnen();
      });
    });
    var form = teil.querySelector(".ls-editor");
    if (!form) return;
    form.addEventListener("change", function (ev) {
      if (ev.target.getAttribute("data-f") === "art") { lesen(form); neuZeichnen(); }
    });
    form.querySelector('[data-l="feld"]').addEventListener("click", function () { lesen(form); S.edit.felder.push({ name: "", art: "text" }); neuZeichnen(); });
    [].forEach.call(form.querySelectorAll("[data-fweg]"), function (k) {
      k.addEventListener("click", function () { lesen(form); S.edit.felder.splice(+k.getAttribute("data-fweg"), 1); neuZeichnen(); });
    });
    form.querySelector('[data-l="abbrechen"]').addEventListener("click", function () { S.edit = null; neuZeichnen(); });
    var lw = form.querySelector('[data-l="loeschen"]');
    if (lw) lw.addEventListener("click", function () {
      if (!confirm("„" + S.edit.titel + "“ mit allen Einträgen endgültig löschen? Vorher ggf. unter „Ansehen“ als Excel/PDF sichern.")) return;
      api("l_admin_loeschen", { id: S.edit.id }).then(function (r) { if (r.ok) S.edit = null; fertig(r); });
    });
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var l = lesen(form);
      if (!l.titel) return fehler(form, "Titel fehlt.");
      if (l.felder.some(function (f) { return (f.art === "auswahl" || f.art === "aufgaben") && !f.optionen.length; })) return fehler(form, "Bei Auswahl/Aufgaben bitte Optionen mit Komma eintragen.");
      laedt(form, true);
      api("l_admin_speichern", { liste: l }).then(function (r) { laedt(form, false); if (!r.ok) return fehler(form, r.fehler); S.edit = null; fertig(r); });
    });
  }

  // Startseite: Hinweis auf offene Listen (nur angemeldet)
  function listenHinweis(a) {
    if (!a || !a.listen || !document.querySelector("[data-geb-woche]")) return;
    var l = a.listen.filter(function (x) { return x.startseite; });
    if (!l.length || document.querySelector(".ls-hinweis")) return;
    var ziel = document.querySelector("main") || document.body;
    ziel.insertBefore(el('<div class="kt-leiste ls-hinweis">' + l.map(function (x) {
      return '<span><b>' + esc(x.titel) + "</b>" + (x.bis ? " – bis " + datumDe(x.bis) : "") + '</span><a href="' + PFAD + "listen.html?id=" + encodeURIComponent(x.id) + '">Eintragen</a>';
    }).join("") + "</div>"), ziel.firstChild);
  }

  // ---------- Spielerseiten: eigene Änderungen sofort, Admin-Ansicht ----------
  function spielerseite(a) {
    var oben = document.querySelector("[data-profil-slug]");
    if (!oben || !a) return;
    var slug = oben.getAttribute("data-profil-slug"), benutzer = oben.getAttribute("data-benutzer") || "";
    var gbZeile = document.querySelector("[data-gb-zeile]");
    function gbSetzen(label, wert, zusatz) {
      if (!gbZeile) return;
      gbZeile.hidden = !wert;
      gbZeile.querySelector("dt").textContent = label;
      gbZeile.querySelector("dd").innerHTML = esc(wert) + (zusatz || "");
    }
    if (a.ich.slug === slug) {
      api("m_ich", { mitFoto: true }).then(function (r) {
        if (!r.ok) return;
        var p = r.profil, box = document.querySelector("[data-kt-text]");
        if (box) {
          var inhalt = textHtml(p.text) + linksHtml(p.lichess, p.chesscom);
          box.innerHTML = inhalt; box.hidden = !inhalt;
        }
        var img = document.querySelector(".sp-foto");
        if (p.foto) {
          if (!img) { img = el('<img class="sp-foto" alt="">'); oben.appendChild(img); }
          img.src = p.foto;
        } else if (img && img.getAttribute("data-konto")) img.remove();
        if (p.gb === "nichts") gbSetzen("Jahrgang", "");
        else if (p.gb === "oeffentlich") gbSetzen("Geburtstag", datumText(r.ich.geburtstag));
        else gbSetzen("Jahrgang", r.ich.jahr);
        if (!document.querySelector(".kt-eigen")) oben.parentNode.insertBefore(el('<div class="kt-leiste kt-eigen"><span>Deine Seite – Änderungen sehen andere ab morgen früh.</span>' +
          '<a href="' + PFAD + 'mein-profil.html">Profil bearbeiten</a></div>'), oben);
      });
    }
    if (a.ich.darf.geburtstage) {
      geburtstage().then(function (g) {
        var m = g && g.liste.filter(function (x) { return x.slug === slug; })[0];
        if (m && !m.oeffentlich) gbSetzen("Geburtstag", datumText(m.datum), ' <span class="kt-tag admin">nur für Admins</span>');
      });
    }
    if (a.ich.darf.verwaltung && a.ich.slug !== slug) {
      var leiste = el('<div class="kt-leiste kt-admin"><span>Admin-Ansicht</span><span>' +
        (benutzer ? '<button type="button" data-akt="ausblenden">Profil ausblenden</button>' : "") +
        '<a href="' + PFAD + 'verwaltung.html#nutzer">Konten verwalten</a></span></div>');
      oben.parentNode.insertBefore(leiste, oben.parentNode.firstChild);
      var aus = leiste.querySelector("[data-akt]");
      if (aus) aus.addEventListener("click", function () {
        if (!confirm("Profil ab dem nächsten Build ausblenden?")) return;
        api("m_admin", { aktion: "ausblenden", ziel: benutzer }).then(function (r) { alert(r.ok ? r.meldung : r.fehler); });
      });
    }
  }

  var GEB_PROMISE = null;
  function geburtstage() {
    if (GEB_PROMISE) return GEB_PROMISE;
    var c = null;
    try { c = JSON.parse(localStorage.getItem(GEB_KEY) || "null"); } catch (e) {}
    var gueltig = c && c.t === token() && Date.now() - c.zeit < GEB_STUNDEN * 3600000;
    var laden = function () {
      return api("m_geburtstage").then(function (r) {
        try { if (r.ok) localStorage.setItem(GEB_KEY, JSON.stringify({ t: token(), zeit: Date.now(), d: r })); else localStorage.removeItem(GEB_KEY); } catch (e) {}
        return r.ok ? r : null;
      });
    };
    if (gueltig) { if (Date.now() - c.zeit > 3600000) laden(); return (GEB_PROMISE = Promise.resolve(c.d)); }
    return (GEB_PROMISE = laden());
  }

  // Startseite: "Geburtstage diese Woche" für Berechtigte mit allen Mitgliedern
  function startseite(a) {
    var box = document.querySelector("[data-geb-woche]");
    if (!box || !a || !a.ich.darf.geburtstage) return;
    var tage = +box.getAttribute("data-geb-woche") || 7;
    geburtstage().then(function (g) {
      if (!g) return;
      var heute = new Date(); heute.setHours(0, 0, 0, 0);
      var treffer = [];
      g.liste.forEach(function (m) {
        var p = m.datum.split("-").map(Number);
        for (var i = 0; i <= tage; i++) {
          var d = new Date(heute); d.setDate(d.getDate() + i);
          if (d.getMonth() + 1 === p[1] && d.getDate() === p[2]) treffer.push({ d: d, i: i, m: m, alter: d.getFullYear() - p[0] });
        }
      });
      treffer.sort(function (x, y) { return x.i - y.i; });
      if (!treffer.length) return;
      box.hidden = false;
      box.querySelector("ul").innerHTML = treffer.map(function (t) {
        return "<li><span><b>" + esc(t.m.vorname + " " + t.m.nachname) + '</b> <span class="st-meta">' +
          (t.i === 0 ? "heute" : WT[t.d.getDay()] + " " + ("0" + t.d.getDate()).slice(-2) + "." + ("0" + (t.d.getMonth() + 1)).slice(-2) + ".") +
          "</span>" + (t.m.oeffentlich ? "" : ' <span class="kt-tag admin">nur für Admins</span>') + "</span><em>wird " + t.alter + "</em></li>";
      }).join("");
    });
  }

  // ---------- Start ----------
  ich().then(function (a) {
    knopfZeigen(a);
    var seite = document.getElementById("kt-seite");
    if (seite) {
      var art = seite.getAttribute("data-seite");
      if (art === "profil") seiteProfil(seite);
      if (art === "verwaltung") seiteVerwaltung(seite);
      if (art === "listen") seiteListen(seite);
    }
    spielerseite(a);
    startseite(a);
    listenHinweis(a);
    // Andere Skripte (z. B. "Ich will hin") können die Anmeldung nutzen
    document.dispatchEvent(new CustomEvent("afk-konto", { detail: a }));
  });
  window.AFK_KONTO = { token: token, ich: ich, fenster: fenster, api: api };
})();
