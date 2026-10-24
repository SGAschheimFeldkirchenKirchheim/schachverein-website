#import "Technik/template.typ": *
#show: template
#import "database.typ": *
#import "Turniere/Neujahrsblitz.typ": *
#import "Turniere/Osterblitz.typ": *
#import "Turniere/Sommerblitz.typ": *
#import "Turniere/Herbstblitz.typ": * 
#import "Turniere/Weihnachtsblitz.typ": * 
#import "Technik/wertung.typ": * 
#import "Technik/tabelle.typ": * 
#import "Technik/links.typ": turnier-links

#let alle-turniere = (
  (name: "Neujahrsblitz", daten: neujahrsblitz),
  (name: "Osterblitz", daten: osterblitz),
  (name: "Sommerblitz", daten: sommerblitz),
  (name: "Herbstblitz", daten: herbstblitz),
  (name: "Weihnachtsblitz", daten: weihnachtsblitz),
)
// Weniger Turniere ==> besserer Platz
// Gesamtwertung: breit (Querformat-Breite), Höhe passt sich an, also alles auf einer Seite
#set page(width: 297mm, height: auto, flipped: false)
#jahreswertung-tabelle(alle-turniere, mitglieder)

// Einzelturniere: wieder A4 hoch
#set page(width: 210mm, height: 297mm, flipped: false)
#einzelturnier-tabelle(neujahrsblitz, "Neujahrsblitz", mitglieder, turnier-url: turnier-links.neujahrsblitz)

#einzelturnier-tabelle(osterblitz, "Osterblitz", mitglieder, turnier-url: turnier-links.osterblitz)

#einzelturnier-tabelle(sommerblitz, "Sommerblitz", mitglieder, turnier-url: turnier-links.sommerblitz)

#einzelturnier-tabelle(herbstblitz, "Herbstblitz", mitglieder, turnier-url: turnier-links.herbstblitz)

#einzelturnier-tabelle(weihnachtsblitz, "Weihnachtsblitz", mitglieder, turnier-url: turnier-links.weihnachtsblitz)