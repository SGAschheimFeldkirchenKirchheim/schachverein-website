#import "Technik/template.typ": *
#show: template
#import "database.typ": *
#import "Turniere/Neujahrsblitz.typ": *
#import "Turniere/Osterblitz.typ": *
#import "Turniere/Sommerblitz.typ": *
#import "Turniere/Herbstblitz.typ": *
#import "Turniere/Weihnachtsblitz.typ": *
#import "Technik/tabelle.typ": *
#import "Technik/links.typ": turnier-links, stand

// "web" (von build_site.py gesetzt): Gesamtwertung auf EINER hohen Seite für die SVG.
// Sonst (PDF): normales A4.
#let web = sys.inputs.at("format", default: "pdf") == "web"

// gespielt: false -> Spalte grau "ausstehend", zählt nicht, keine Einzelseite.
// Nach dem Turnier einfach auf true setzen (oder ", gespielt: false" löschen).
#let turniere = (
  (name: "Neujahrsblitz",   daten: neujahrsblitz,   url: turnier-links.neujahrsblitz),
  (name: "Osterblitz",      daten: osterblitz,      url: turnier-links.osterblitz),
  (name: "Sommerblitz",     daten: sommerblitz,     url: turnier-links.sommerblitz),
  (name: "Herbstblitz",     daten: herbstblitz,     url: turnier-links.herbstblitz),
  (name: "Weihnachtsblitz", daten: weihnachtsblitz, url: turnier-links.weihnachtsblitz, gespielt: false),
)

#set page(width: 297mm, height: auto, flipped: false) if web
#jahreswertung-tabelle(
  turniere,
  mitglieder,
  titel: "SG AFK – Blitzjahreswertung 2026",
  stand: stand,
  beste: 3,
  sieg-punkte: 20,
)

#pagebreak(weak: true)
#set page(width: 210mm, height: 297mm, flipped: false)
#for t in turniere.filter(t => t.at("gespielt", default: true)) {
  einzelturnier-tabelle(t, mitglieder)
}
