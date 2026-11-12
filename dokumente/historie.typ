// Vereinsgeschichte der SG AFK. Bis 2020 übernommen aus „Historie 1952 bis 2020“, ab 2021 neu geschrieben.
// Zeilen mit // sind Notizen bzw. offene Fragen: Sie erscheinen weder im PDF noch auf der Website.
// Neues Jahr ergänzen: einen weiteren #jahr("…")[…]-Block ans Ende setzen.
#import "afk-vorlage.typ": *
#show: dokument.with(titel: "Vereinsgeschichte", untertitel: "1952 bis heute")

// Ein Jahr der Zeitleiste: Jahreszahl links, Text rechts
#let jahr(j, inhalt) = block(breakable: false, above: 1.4em)[   // ein Jahr wird nicht über zwei Seiten getrennt
  #grid(columns: (4.2em, 1fr), column-gutter: 1.1em,
    text(13pt, weight: "bold", fill: navy, j),
    block(inset: (left: 1em), stroke: (left: 1.5pt + hellblau), inhalt),
  )
]

#jahr("1952")[
  Gründung der Schachfreunde Feldkirchen durch Klaus Weckert und Hans Schleicher. Genauere Informationen zur Geschichte der Schachfreunde sind leider zurzeit nicht bekannt – das wird noch erforscht. Sobald Ergebnisse vorliegen, werden diese hier veröffentlicht.
]

#jahr("1984")[
  Die Gründungsversammlung wird für den 14. September festgelegt. An diesem Tag gründen 15 Schachspieler den Schach-Club Aschheim.

  1\. Vorsitzender: Helmut Gundel \
  2\. Vorsitzender: Janos Barabas \
  Turnierleiter: Karlheinz Weber \
  Kassier: Norbert Brandl \
  Schriftführerin: Angelika Fischer
]

#jahr("1985")[
  Die erste Clubmeisterschaft gewinnt Karlheinz Weber (6 Punkte) vor Xaver Spaegele (5) und Christoph Sindern (4,5). Gespielt wurden sieben Runden nach Schweizer System.

  Das Weihnachts-Blitzturnier holte sich Christoph Sindern (8 Punkte) vor Karlheinz Weber (7,5), Daniel Pohl (7) und Patrick Pohl (6).

  Mitglieder: 32 (davon 13 Jugendliche)
]

#jahr("1986")[
  Das erste Auftreten des Vereins in einem Mannschaftswettbewerb war in der D-Klasse des Schachbezirkes München.

  In der Jugendabteilung wird Patrick Pohl Blitzmeister vor Daniel Pohl und Florian Weber. Bei der Jugend-Clubmeisterschaft dreht Daniel gegen seinen Bruder Patrick den Spieß um. Dritte wird das einzige Mädchen der Schachjugend Gisi Gundel.

  Am 16. September wird der Zusammenschluss mit den Schachfreunden Feldkirchen auf ein Jahr Probe beschlossen. Neuer Name: Schachgemeinschaft Aschheim/Feldkirchen.
]

#jahr("1987")[
  Am 10. Juli wird die endgültige Fusion beschlossen. 1. Vorsitzender der SG Aschheim/Feldkirchen wird Helmut Gundel. Spiellokal bleibt die Gaststätte „Tassilo“, Spielabend ist der Freitag.
]

#jahr("1992")[
  Als Gast zum Weihnachtsblitz-Turnier konnte der IM Alexander Banguiev gewonnen werden. Der Gast von der ukrainischen Halbinsel Krim gewann alle 15 Partien und siegte souverän vor Claus Pakmor (13) und Hans Wunder (10,5). Wen wundert’s: Banguiev weist eine ELO-Einschätzung von 2400 (!) auf.
]

#jahr("1994/95")[
  Vereinsmeister wird Prof. Dr. Hans Schmidt. Am Ende der 13 Runden stehen 10 Punkte auf seinem Konto. Den zweiten Platz teilen sich Dr. Günter Kopp und Hans Schleicher mit je 9,5 Zählern.

  Bei den Münchner Schnellschachmeisterschaften gelang der Mannschaft des Vereins mit Claus Pakmor, Neuzugang Frederik Prause, Klaus Weckert und Dr. Günter Kopp sensationell der Aufstieg in die Hauptrunde gegen erheblich höher eingeschätzte Gegner aus der Bezirks- und A-Klasse. In der Endrunde hingen für den einzigen teilnehmenden Verein der B-Klasse die Trauben dann zu hoch.

  Die erste Mannschaft kann sich in der B-Klasse halten, die zweite steigt in die C-Klasse auf.

  Das Weihnachts-Blitzturnier holte sich auf Anhieb Frederik Prause (12 von 14 Punkten) vor Claus Pakmor (11) und Dr. Schmidt (10,5)
]

#jahr("1996/97")[
  Der 62jährige Klaus Weckert sorgt mit seinem Sieg bei der Pokalmeisterschaft für eine dicke Überraschung. Er verweist Prause, Hahn und Dr. Kopp auf die Plätze.

  In einem echten „Endspiel“ bei der letzten Runde setzte sich bei den Clubmeisterschaften Pakmor gegen Prause durch. Dritter wurde Horst Hahn.

  Die Rangliste des Vereins zu diesem Zeitpunkt lautete nach DWZ: Pakmor (1962), Prause (1832), Holler (1802), Hahn (1753), Weckert (1722), Dr. Kopp (1708).

  Bei den Münchner Mannschaftsmeisterschaften wird die erste Mannschaft (Pakmor, Prause, Hahn, Kopp, Weckert, Holler, Schleicher, Schmidt) Vierter in der B-Gruppe. Die zweite Mannschaft (Sindern, Gundel, Gruner, Wunder, Brand, Blaha, Dillinger) verlor in der D-Gruppe keine einzige Partie, verpasst trotzdem den Aufstieg in die C-Klasse um einen halben Punkt.
]

#jahr("1998")[
  Die SG Aschheim/Feldkirchen trauert um Prof. Dr. Hans Schmidt. Das Gründungsmitglied stirbt im März plötzlich und unerwartet.

  Der Ranglistenerste Claus Pakmor steht der 1. Mannschaft aus beruflichen Gründen nicht mehr zur Verfügung. Für Verstärkung sorgt Neuzugang Ronny Damaske.

  Eine eigene Homepage wird eingerichtet.
]

#jahr("1999")[
  Bei den Münchner Mannschaftsmeisterschaften erzielt Dr. Günter Kopp sein 12. Remis hintereinander! Der Mannschaftsführer spielt an Brett 4.

  Ganz im Zeichen von Frederik Prause standen die internen Turniere. Der Spitzenspieler wird Blitz- und Vereinsmeister.

  Die erste Mannschaft kann sich trotz zahlreichen Ausfällen in der B-Klasse halten.

  Weihnachtsblitz: Pakmor sen. vor Pakmor jr. und Prause.
]

#jahr("2000")[
  Der erst 17jährige Rüdiger Pakmor wird Vereinsmeister. Zweiter wird Horst Hahn vor Ronny Damaske.

  Schade, dass der Clubmeister und sein Vater bei den Münchner Mannschaftsmeisterschaften für Vaterstetten spielen.

  Den Franz-Lackermeier-Gedächtnispokal holt sich zum vierten Male in Folge Frederik Prause.
]

#jahr("2001")[
  Sensation im Pokal-Turnier: Außenseiter Richard Brand (12. der Vereinsrangliste) gewinnt im Finale gegen Peter Blaha (14.).

  Der Vorstand mit Helmut Gundel an der Spitze wird einstimmig bestätigt. Neu ist Turnierleiter Ronny Damaske, der den nicht mehr angetretenen Dr. Kopp ablöst.

  Die erste Mannschaft kann sich in der B-Liga nicht halten und steigt ab.

  Erstmals wird über einen Zusammenschluss mit dem Schachklub Kirchheim debattiert.
]

#jahr("2002")[
  Die Schachgemeinschaft trauert um Peter Stojanov.

  Die erste Mannschaft schafft postwendend den Wiederaufstieg in die B-Klasse. Auch die zweite Mannschaft steigt auf und spielt in Zukunft in der C-Klasse.

  Dr. Günter Kopp wird wieder Turnierleiter, da Ronny Damaske wegen beruflicher Mehrbelastung kürzer treten muss.

  Weihnachtsblitz: Prause klar vor Armin Tobisch und Claus Pakmor.
]

#jahr("2003")[
  Die Vereinsmeisterschaft gewinnt Claus Pakmor vor Horst Hahn und Ronny Damaske.

  Sowohl die 1. (B-Klasse) als auch die 2. Mannschaft (C-Klasse) können sich in den Ligen halten.

  Frederik Prause gewinnt zum fünften Mal den Franz-Lackermeier-Pokal und darf ihn mit nach Hause nehmen.
]

#jahr("2004")[
  Nach seiner überraschenden Qualifikation für das Vormeisterturnier der Münchner Einzelmeisterschaften ist Ronny Damaske der klare Favorit für die Vereinsmeisterschaft. Der Feldkirchener lässt nichts anbrennen und siegt vor Horst Hahn und den punktgleichen Dr. Günter Kopp und Michael Miller.

  Die 1. Mannschaft belegt in der B-Klasse mit dem wieder für den Verein am Spitzenbrett spielenden Claus Pakmor (4,5 Punkte aus 6 Partien) einen ausgezeichneten dritten Rang. Weitere Punktelieferanten sind Frederik Prause (5 aus 7) und Neuzugang Dr. Peter Esser (3 aus 5).

  Dagegen ist die 2. Mannschaft in der C-Klasse überfordert und steigt in die D-Klasse ab.
]

#jahr("2005")[
  Die Schachfreunde trauern um Klaus Weckert, der 70jährig stirbt. Als 18jähriger gründete er gemeinsam mit Hans Schleicher den Schachklub Feldkirchen.

  Bei den Münchner Mannschaftsmeisterschaften endet die 1. Mannschaft in der B-Klasse im Mittelfeld, die 2. wird in der D-Klasse Dritte.

  Zur ersten Austragung eines offenen Schnellschachturniers konnte der SG-Vorsitzende Helmut Gundel 28 Teilnehmer begrüßen. Unter ihnen den ukrainischen IM Sasha Beletzky (ELO 2380). Der große Favorit holte sieben Punkte aus sieben Partien.
]

#jahr("2006")[
  Titelverteidiger Ronny Damaske (10 Punkte) wird wieder Clubmeister. Zweiter wird Michael Müller (8,5) vor Horst Hahn, Dr. Günter Kopp und Hans Schleicher (je 6).

  Die erste Mannschaft (C. Pakmor, Prause, Dr. Esser, Damaske, R. Pakmor, Holler, Hahn, Miller) erreicht in der B-Klasse einen achtungsvollen zweiten Rang.

  Ganz groß trumpft Team 2 (Dr. Daniel Pohl, Dr. Kopp, Sindern, Gundel, Brand, Blaha) auf, gewinnt alle 8 Begegnungen und steigt in die C-Klasse auf.
]

#jahr("2007")[
  Richard Brand wird überraschenderweise Clubmeister. Peter Blaha und Dr. Günter Kopp teilen sich den zweiten Platz vor Horst Hahn.

  Die Fusion mit den Schachfreunden Kirchheim wird zum 1.1.2008 beschlossen. Neuer gemeinsamer Name: Schachgemeinschaft Aschheim/Feldkirchen/Kirchheim (SG AFK)
]

#jahr("2008")[
  Die Fusion mit den Schachfreunden Kirchheim.

  Der Kirchheimer Schachklub wurde 1975 gegründet. Gründungsmitglied war u.a. auch Hans-Peter Hecht, der bis zur Fusion auch Kassier des Clubs war. Gespielt wurde damals beim Neuwirt, zeitweise sogar im Sitzungssaal der Gemeinde und am Ende im Merowinger Hof. 1976 wurde erstmals in einer Mannschaftsmeisterschaft teilgenommen. Und zwar in einer von 8(!) verschiedenen D-Klassen. Ein Punktspiel wurde gewonnen, alle anderen verloren! Aber schon im nächsten Jahr sah alles ganz anders aus: Die Mannschaft wurde Zweiter und stieg auf. Bei der Fusion bekleidete Helmut Kaufmann den Posten des 1. Vorsitzenden des Kirchheimer Schachclubs. Im neuen Verein tauchen zum ersten Male u.a. die Namen Eiberweiser, Hecht, Kaufmann, Nicolay, Nowotny, Tobisch und Vischer auf.

  Beflügelt durch die Verstärkung schafft die 1. Mannschaft zum ersten Mal den Aufstieg in die A-Klasse. Dies ist die zweithöchste Liga im Schachbezirk München. Die Spieler waren Prause, Dr. Esser, Damaske, Vischer, Hecht, Hahn, Kaufmann, Miller und Holler.
]

#jahr("2009")[
  Aschheims Bürgermeister, Helmut Englmann, 1984 Initiator und Gründungsmitglied des Schach-Club Aschheim, wird zum Ehrenmitglied ernannt.

  Die Vereinsmeisterschaft sichert sich Ronny Damaske vor Bernd Nowotny und Dieter Vischer.
]

#jahr("2012")[
  Dieter Vischer wird zur bestimmenden Figur und sichert sich Meisterschaft und Pokal.

  Die Blitzmeisterschaft geht an Ronny Damaske.
]

#jahr("2014")[
  Matthias Naumann wird zum 1. Vorsitzenden gewählt und wird Nachfolger von Helmut Gundel, der nicht mehr kandidiert.

  Da alle Teilnehmer des von Frederik Prause und Dr. Peter Esser geleiteten Kinder- und Jugendtrainings genügende Kenntnisse erworben haben, wird ein erstes Schnellschachturnier der Youngsters mit 15 Minuten Bedenkzeit veranstaltet. In den drei nach Geburtsjahrgängen geteilten Gruppen siegten Korbinian Ruff, Amelie Huber und Colin Reimann.

  In sieben Runden nach Schweizer System wurde die Clubmeisterschaft ausgetragen. Keine Partie verlor Hanspeter Hecht (5 Siege, 2 Remis) und verwies Ronny Damaske und Armin Tobisch auf die Plätze.

  Beim Weihnachts-Blitzturnier ist Armin Tobisch nicht zu halten, gewinnt alle 11 Partien und siegt vor Ronny Damaske (10), Frederik Prause (8) und den punktgleichen Rolf Nicolay und Dieter Vischer (je 6,5).
]

#jahr("2015")[
  Nach einer längeren Durststrecke holte die SG AFK den begehrten Wanderpokal des „Oberlandquartetts“. Es spielten: Prause, Damaske, Vischer, Tobisch, Hecht, Nowotny, Sindern, Miller und Naumann.

  Hanspeter Hecht (6,5 Punkte) verteidigt seinen Vereinstitel gegen Frederik Prause (6) und Dieter Vischer (4,5).

  Die Vereinsblitzmeisterschaft wird eine sichere Beute von Frederik Prause (7 Siege in sieben Partien!). Zweiter wird Hans Jörg Eiberweiser vor Hanspeter Hecht (beide 4,5). Das Weihnachts-Blitzturnier musste nach

  Stichkampf zwischen Ronny Damaske und Frederik Prause (je 11,5 Punkte) entschieden werden. Dabei hatte der Erstgenannte knapp den Kopf vorne. Dritter wurde Hans Jörg Eiberweiser (10,5).
]

#jahr("2016")[
  Mit ganz starken Leistungen sicherten sich unsere Senioren den Sieg in ihrer Gruppe bei den Münchner Meisterschaften und stiegen in die Gruppe 1 auf. Für diesen Triumph sorgten in erster Linie Frederik Prause, Hanspeter Hecht und Hans Jörg Eiberweiser.

  In verschiedenen Turnieren des Landkreises München konnten unsere Jugendlichen erste Erfahrungen sammeln. Besonders gut aus der Affäre zogen sich beim Einstand Korbinian Ruff, Colin Reimann, Amelie Huber und Katharina Esser.

  In gewohnt souveräner Manier wurde Frederik Prause Vereinsblitzmeister. Neun Punkte aus neun Partien sprechen für sich. Da blieb für Dieter Vischer (8), Matthias Naumann und Hans Jörg Eiberweiser (je 5,5) nur Rang zwei bis vier über.

  Weihnachts-Blitz: Ronny Damaske (13 Punkte) vor Frederik Prause und Dr. Peter Esser (je 11)
]

#jahr("2017")[
  Die Jugendlichen unseres Vereins erreichten bei den Münchner Schulschach-Einzelmeisterschaften erfreuliche Platzierungen. Bei den Schülern der 3. Klasse wurde Colin Reimann mit vier Punkten aus sechs Partien in einem Feld von 40 Schülern Neunter. Mit der gleichen Punktzahl belegte Simon Esser den 13. Diego Heinze mit drei Punkten den 21. Platz. Bei den Schülern der Klassen 7-9 erkämpfte sich David Mehlhorn 4 Punkte aus sechs Partien und wurde Vierter. Arthur Krumm hatte am Ende einen Punkt weniger auf seinem Konto und belegte Rang 12. Insgesamt nahmen 28 Kinder teil. Ebenfalls ein stark beachteter vierter Platz war die Ausbeute von Mesut Ceylan in der Kategorie der Klassen 10-12. Hier waren 16 Teilnehmer am Start.

  Neuer Vereinsmeister wurde Dieter Vischer.
]

#jahr("2018")[
  Die Schachgemeinschaft trauert um Helmut Kaufmann, Vorsitzender des Schach-Klubs Kirchheim bis zur Fusion und später langjähriger Spielleiter der Schachgemeinschaft.

  Den dank des erfreulichen Zuwachses an jugendlichen Mitgliedern nach Dekaden erstmalig wieder ausgespielten Jugend-Pokal der Schachgemeinschaft sicherte sich David Mehlhorn durch einen Sieg im Finale gegen Arthur Krumm.

  Infolge der durch unsere jugendlichen Mitglieder deutlich gewachsenen Anzahl an aktiven Mitgliedern war unsere Schachgemeinschaft erstmalig mit 3 Mannschaften in den Münchner Mannschaftsmeisterschaften vertreten und erreichte folgende erfreulichen Platzierungen: mit der 1. Mannschaft in der B-Klasse einen 2. Platz und damit den Aufstieg in die A-Klasse, mit der 2. Mannschaft in der D-Klasse den 4. Platz sowie mit der neu gegründeten 3. Mannschaft mit überwiegend jugendlichen Spielern in der E-Klasse den 2. Platz.

  Pokalsieger wurde unser neues Vereinsmitglied Pierre Tassell, Blitzschachmeister wie schon so oft Frederik Prause und Sieger unseres Weihnachtsblitzturnieres im zweiten Jahr seiner Vereinszugehörigkeit Rudolf Oster.

  Ende September war Internationaler Meister Frank Zeller zu Gast und spielte simultan gegen unsere Mitglieder. Im Herbst konnten sich zudem unsere Jugendlichen bei den Münchner U16-Mannschaftsmeisterschaften und den Münchner Schüler-Einzelmeisterschaften über schöne Erfolge freuen.
]

#jahr("2019")[
  Nach ihrem Abstieg aus der 1. Seniorenliga des Schachbezirks München in die 2. Seniorenliga gelang unserer Senioren-Mannschaft (Ü60) der direkte Wiederaufstieg in die 1. Seniorenliga: die „siegreichen Vier“ waren Frederik Prause (3,5 / 4), Hanspeter Hecht (3,5 / 4), Rudolf Oster (2 / 4) und Matthias Naumann (2,5 / 3).

  In den Münchner Mannschaftsmeisterschaften konnte sich unsere 1. Mannschaft nach ihrem Aufstieg in die A-Klasse dort im Mittelfeld (8:10 Mannschaftspunkte) ebenso souverän behaupten wie unsere 2. Mannschaft im ersten Jahr ihrer Spielberechtigung in der C-Klasse (9:5 Mannschaftspunkte). Unsere Jugendmannschaft (U20), die schon in der Vorsaison in die 1. Jugendbezirksliga aufgestiegen war, sicherte dort als Fünfter von sieben Mannschaften den Klassenerhalt. Damit war die Saison 2018/19 für alle vier Mannschaften ein Erfolg. Die besten Punktesammler: Pierre Tassell (6 aus 7) in der 1. Mannschaft, Korbinian Ruff (5 aus 7) in der 2. Mannschaft, Frederik Prause und Hanspeter Hecht (je 2,5 aus 3) bei den Senioren sowie András Centgraf (4 aus 6) in der U20.

  Beim Oberland-Quartett in Höhenkirchen belegte unsere Mannschaft nach engen Wettkämpfen den 3. Platz; gegen den Turniersieger Deisenhofen ging die letzte Runde nur knapp mit 3,5 : 4,5 verloren.

  Als bisher jüngster Spieler in der Vereins-Historie errang der 15-jährige Arthur Krumm den Titel des Vereinsmeisters, gefolgt von den vier an sich favorisierten „Oldies“ Dieter Vischer, Hanspeter Hecht, Rudolf Oster und Frederik Prause. Den Vereinspokal konnte Pierre Tassell erfolgreich verteidigen, genauso wie David Mehlhorn den Vereins-Jugend-Pokal. Meister im Blitzschach unserer Schachgemeinschaft wurde Dieter Vischer. Die Blitzmeisterschaft wurde in diesem Jahr an vier Spielabenden ausgetragen, von denen die besten drei Ergebnisse zählten.
]

#jahr("2020")[
  Die Schachgemeinschaft trauert um Christoph Sindern, Gründungsmitglied des Schach-Clubs Aschheim und später langjähriger Spielleiter der Schachgemeinschaft und Mannschaftsführer der 2. Mannschaft.

  Da bei den Wahlen zum Vorstand des Vereins Matthias Naumann nach 6 Jahren als 1. Vorsitzender aus familiären Gründen nicht für eine vierte Amtszeit kandidierte, wurde für mehrere Vorstandspositionen neu kandidiert und wie folgt gewählt: 1. Vorsitzender Andreas Schwarz, 2. Vorsitzender Dr. Daniel Pohl, Kassenwart Frederik Prause, Spielleiter Pierre Tassell, Schriftführer Rudolf Oster.

  Unsere 1. Jugendmannschaft wird Jugend-Mannschafts-Meister des Schachbezirks München und steigt in die Jugend-Landesliga Süd auf.

  Großer Erfolg auch für die 1. Mannschaft, die erstmals in der Vereinsgeschichte in die Bezirksliga, die höchste Spielklasse des Schachbezirks München, aufsteigt. Für die meisten Punkte sorgten Frederik Prause, Ronny Damaske (verlor keine einzige Partie!) und Dieter Vischer.

  Infolge der Corona-Pandemie konnten nicht alle vereins-internen Titel neu ausgespielt werden. Als online-Turniere wurden durchgeführt: die Vereins-Blitzmeisterschaft, die sich Frederik Prause sicherte, sowie das Weihnachts-Blitzturnier mit dem Gewinner Pierre Tassell.
]

#jahr("2021")[
  // OFFEN: Mannschaften 2020/21 (AFK 1 in der Bezirksliga?), Jugend, Vereinsmeisterschaft wegen Corona ausgefallen?
  Die Schnellschach-Vereinsmeisterschaft gewinnt Pierre Tassell. Erster Kirchheimer Stadtmeister in unseren Reihen wird Arthur Krumm.

  Den Osterblitz holt sich Frederik Prause, das Weihnachts-Blitzturnier David Mehlhorn.
]

#jahr("2022")[
  // OFFEN: Mannschaften 2021/22, Pokalsieger 2022
  Pierre Tassell wird erstmals Vereinsmeister und sichert sich auch die Blitzmeisterschaft. Schnellschachmeister wird David Mehlhorn.

  Das Weihnachts-Blitzturnier gewinnt Lars Goldbeck.
]

#jahr("2023")[
  // OFFEN: Mannschaften 2022/23, Pokalsieger 2023, Ergebnis der Vorstandswahl 2023
  Pierre Tassell verteidigt seinen Titel als Vereinsmeister. Die Blitzmeisterschaft teilen sich Ronny Damaske und Pierre Tassell.

  Armin Tobisch wird Schnellschachmeister und Kirchheimer Stadtmeister. Ronny Damaske gewinnt sowohl den Osterblitz als auch das Weihnachts-Blitzturnier.
]

#jahr("2024")[
  // OFFEN: Mannschaften 2023/24 (wie viele?), Schnellschachmeister 2024
  Pierre Tassell gewinnt alles, was es an großen Vereinstiteln zu gewinnen gibt: Vereinsmeisterschaft, Blitzmeisterschaft und Pokal.

  Den Osterblitz entscheidet Moritz Stöttner für sich, das Weihnachts-Blitzturnier Stefans Kasims.
]

#jahr("2025")[
  // OFFEN: Zahl der Mannschaften 2024/25, Ergebnis der Vorstandswahl 2025, Senioren und Jugend
  In der Saison 2024/25 starten gleich zwei Mannschaften in der D-Klasse. Die 4. Mannschaft mit Mannschaftsführer Korbinian Ruff wird Erster und steigt auf, die 5. Mannschaft belegt Platz zwei.

  Neu im Vereinsleben ist die Blitzjahreswertung: Die Blitzturniere des Jahres werden zu einer Serie zusammengefasst. Erster Blitzserienmeister wird Pierre Tassell.

  Pierre Tassell gewinnt zum vierten Mal in Folge die Vereinsmeisterschaft. Alexander Wittko holt den Vereinspokal und wird Jugend-Vereinsmeister. Schnellschachmeister wird Stefans Kasims, Blitzmeister Fabian Müller.
]

#jahr("2026")[
  // OFFEN: Senioren und Jugend 2025/26, Mitgliederzahl, Blitzserienmeister 2026 (nach dem Weihnachtsblitz)
  Mit sechs Mannschaften ist die Schachgemeinschaft in der Saison 2025/26 so breit aufgestellt wie nie. Die Aufsteiger des Vorjahres, jetzt als 3. Mannschaft in der C-Klasse, marschieren direkt durch und steigen in die B-Klasse auf. Auch die 2. Mannschaft feiert den Aufstieg, sie spielt künftig in der A-Klasse. Alle anderen Mannschaften halten ihre Klasse.

  Im September zieht der Verein in das Gymnasium Kirchheim um. Die Schule ist Schachschule und unser neuer Spielort.

  Alexander Wittko wird Vereinsmeister und gewinnt auch den Pokal.

  Dominik Dax ist der Mann des Herbstes: Beim OIS gewinnt er das C-Turnier souverän mit 6,5 aus 7 Punkten, kurz darauf den Herbstblitz (10,5 aus 13) und schließlich die Schnellschach-Vereinsmeisterschaft. Diese wird als Kooperationsturnier mit der SU Ebersberg-Grafing ausgetragen und bringt mit 40 Teilnehmern einen Rekord. Arthur Krumm wird punktgleich Zweiter, Schnellschach-Jugendmeister Konrad Keblat.

  Beim Kooperationsturnier mit dem Gymnasium Kirchheim gewinnen Poldi Elger und Stefans Kasims das Profiturnier.
]
