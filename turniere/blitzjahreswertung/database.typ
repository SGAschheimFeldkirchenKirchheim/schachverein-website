#let punkte(id, turnier) = turnier.at(id, default: 0)

#let mitglieder = (
  "EduardA": (
    Vorname: "Eduard",
    Nachname: "Abud",
  ),
  "JohannA": (
    Vorname: "Johann",
    Nachname: "Alt",
  ),
  "JohannesA": (
    Vorname: "Johannes",
    Nachname: "Aumüller",
  ),
  "ChristianB": (
    Vorname: "Christian",
    Nachname: "Braun",
  ),
  "StefanC": (
    Vorname: "Stefan",
    Nachname: "Cazacu",
  ),
  "AndrasC": (
    Vorname: "Andras",
    Nachname: "Centgraf",
  ),
  "RonnyD": (
    Vorname: "Ronny",
    Nachname: "Damaske",
  ),
  "DominikD": (
    Vorname: "Dominik",
    Nachname: "Dax",
  ),
  "ClausD": (
    Vorname: "Claus",
    Nachname: "Dillinger",
  ),
  "LiamE": (
    Vorname: "Liam",
    Nachname: "Egersdörfer",
  ),
  "LotharE": (
    Vorname: "Lothar",
    Nachname: "Egersdörfer",
  ),
  "NilsE": (
    Vorname: "Nils",
    Nachname: "Egersdörfer",
  ),
  "HansE": (
    Vorname: "Hans",
    Nachname: "Eiberweiser",
  ),
  "RalfE": (
    Vorname: "Ralf",
    Nachname: "Eisl",
  ),
  "AimanE": (
    Vorname: "Aiman",
    Nachname: "El Sewisy",
  ),
  "LeopoldE": (
    Vorname: "Leopold",
    Nachname: "Elger",
  ),
  "HelmutE": (
    Vorname: "Helmut",
    Nachname: "Englmann",
  ),
  "KeremE": (
    Vorname: "Kerem",
    Nachname: "Ertürk",
  ),
  "PeterE": (
    Vorname: "Peter",
    Nachname: "Esser",
  ),
  "PhilippE": (
    Vorname: "Philipp",
    Nachname: "Esser",
  ),
  "SimonE": (
    Vorname: "Simon",
    Nachname: "Esser",
  ),
  "EricF": (
    Vorname: "Eric",
    Nachname: "Fan",
  ),
  "TobiasF": (
    Vorname: "Tobias",
    Nachname: "Felser",
  ),
  "BastianF": (
    Vorname: "Bastian",
    Nachname: "Fischer",
  ),
  "LiamG": (
    Vorname: "Liam",
    Nachname: "Ganga",
  ),
  "JörgG": (
    Vorname: "Jörg",
    Nachname: "Gerstenberg",
  ),
  "LarsG": (
    Vorname: "Lars",
    Nachname: "Goldbeck",
  ),
  "ChristianG": (
    Vorname: "Christian",
    Nachname: "Graf",
  ),
  "ValentinG": (
    Vorname: "Valentin",
    Nachname: "Gritsch",
  ),
  "MaximilianG": (
    Vorname: "Maximilian",
    Nachname: "Gubarev",
  ),
  "HelmutG": (
    Vorname: "Helmut",
    Nachname: "Gundel",
  ),
  "HorstH": (
    Vorname: "Horst",
    Nachname: "Hahn",
  ),
  "HanspeterH": (
    Vorname: "Hanspeter",
    Nachname: "Hecht",
  ),
  "KilianH": (
    Vorname: "Kilian",
    Nachname: "Herold",
  ),
  "KianH": (
    Vorname: "Kian",
    Nachname: "Herrmann",
  ),
  "NilsH": (
    Vorname: "Nils",
    Nachname: "Heuwinkel",
  ),
  "VasylH": (
    Vorname: "Vasyl",
    Nachname: "Hez",
  ),
  "JonathanH": (
    Vorname: "Jonathan",
    Nachname: "Hix",
  ),
  "FinlayH": (
    Vorname: "Finlay",
    Nachname: "Hoffmann",
  ),
  "EmilJ": (
    Vorname: "Emil",
    Nachname: "Janeba",
  ),
  "VitusK": (
    Vorname: "Vitus",
    Nachname: "Karasz",
  ),
  "JakobK": (
    Vorname: "Jakob",
    Nachname: "Karpen",
  ),
  "EmilK": (
    Vorname: "Emil",
    Nachname: "Kasims",
  ),
  "StefansK": (
    Vorname: "Stefans",
    Nachname: "Kasims",
  ),
  "KonradK": (
    Vorname: "Konrad",
    Nachname: "Keblat",
  ),
  "NiklasKe": (
    Vorname: "Niklas",
    Nachname: "Keichel",
  ),
  "EmrahK": (
    Vorname: "Emrah",
    Nachname: "Kocak",
  ),
  "NiklasKö": (
    Vorname: "Niklas",
    Nachname: "Köppel",
  ),
  "VaskoK": (
    Vorname: "Vasko",
    Nachname: "Kolemanov",
  ),
  "ArthurK": (
    Vorname: "Arthur",
    Nachname: "Krumm",
  ),
  "AleksandrK": (
    Vorname: "Aleksandr",
    Nachname: "Kurochkin",
  ),
  "AndreiK": (
    Vorname: "Andrei",
    Nachname: "Kurochkin",
  ),
  "CorbinianL": (
    Vorname: "Corbinian",
    Nachname: "Lanz",
  ),
  "StepanL": (
    Vorname: "Stepan",
    Nachname: "Lettetskii",
  ),
  "RalfL": (
    Vorname: "Ralf",
    Nachname: "Liebich",
  ),
  "MaximilianL": (
    Vorname: "Maximilian",
    Nachname: "Loose",
  ),
  "QuirinM": (
    Vorname: "Quirin",
    Nachname: "Magori",
  ),
  "AntonM": (
    Vorname: "Anton",
    Nachname: "Mai",
  ),
  "PhilippM": (
    Vorname: "Philipp",
    Nachname: "Mai",
  ),
  "DavidM": (
    Vorname: "David",
    Nachname: "Mehlhorn",
  ),
  "AlexanderM": (
    Vorname: "Alexander",
    Nachname: "Meißner",
  ),
  "GauravM": (
    Vorname: "Gaurav",
    Nachname: "Mudan",
  ),
  "FabianM": (
    Vorname: "Fabian",
    Nachname: "Müller",
  ),
  "PeterM": (
    Vorname: "Peter",
    Nachname: "Mur",
  ),
  "MatthiasN": (
    Vorname: "Matthias",
    Nachname: "Naumann",
  ),
  "AlexisN": (
    Vorname: "Alexis",
    Nachname: "Neumann",
  ),
  "RolfN": (
    Vorname: "Rolf",
    Nachname: "Nicolay",
  ),
  "BerndN": (
    Vorname: "Bernd",
    Nachname: "Nowotny",
  ),
  "CédricO": (
    Vorname: "Cédric",
    Nachname: "Oberhofer",
  ),
  "RudolfO": (
    Vorname: "Rudolf",
    Nachname: "Oster",
  ),
  "HajunP": (
    Vorname: "Hajun",
    Nachname: "Park",
  ),
  "SandraP": (
    Vorname: "Sandra",
    Nachname: "Phung",
  ),
  "SophiaP": (
    Vorname: "Sophia",
    Nachname: "Phung",
  ),
  "StefanP": (
    Vorname: "Stefan",
    Nachname: "Phung",
  ),
  "DanielP": (
    Vorname: "Daniel",
    Nachname: "Pohl",
  ),
  "NiklasP": (
    Vorname: "Niklas",
    Nachname: "Potteck",
  ),
  "FrederikP": (
    Vorname: "Frederik",
    Nachname: "Prause",
  ),
  "YaranQ": (
    Vorname: "Yaran",
    Nachname: "Quan",
  ),
  "JasperR": (
    Vorname: "Jasper",
    Nachname: "Rademacher",
  ),
  "JakobR": (
    Vorname: "Jakob",
    Nachname: "Regner",
  ),
  "JakobR2": (
    Vorname: "Jakob",
    Nachname: "Richter",
  ),
  "LauraR": (
    Vorname: "Laura",
    Nachname: "Röll",
  ),
  "LeaR": (
    Vorname: "Lea",
    Nachname: "Röll",
  ),
  "LorenzR": (
    Vorname: "Lorenz",
    Nachname: "Röll",
  ),
  "NicolasR": (
    Vorname: "Nicolas",
    Nachname: "Rudenko",
  ),
  "KorbinianR": (
    Vorname: "Korbinian",
    Nachname: "Ruff",
  ),
  "AlexanderS": (
    Vorname: "Alexander",
    Nachname: "Schmidt",
  ),
  "RaphaelS": (
    Vorname: "Raphael",
    Nachname: "Schramm",
  ),
  "AndreasS": (
    Vorname: "Andreas",
    Nachname: "Schwarz",
  ),
  "GeorgS": (
    Vorname: "Georg",
    Nachname: "Schweiger",
  ),
  "RainerS": (
    Vorname: "Rainer",
    Nachname: "Seidl",
  ),
  "AnxinS": (
    Vorname: "Anxin",
    Nachname: "Shao",
  ),
  "CharlesS": (
    Vorname: "Charles",
    Nachname: "Shen",
  ),
  "PierreT": (
    Vorname: "Pierre",
    Nachname: "Tassell",
  ),
  "ArminT": (
    Vorname: "Armin",
    Nachname: "Tobisch",
  ),
  "StefanV": (
    Vorname: "Stefan",
    Nachname: "Vasylevskyi",
  ),
  "DieterV": (
    Vorname: "Dieter",
    Nachname: "Vischer",
  ),
  "EliasW": (
    Vorname: "Elias",
    Nachname: "Wachsmuth",
  ),
  "AlexanderW": (
    Vorname: "Alexander",
    Nachname: "Wittko",
  ),
  "AntonioX": (
    Vorname: "Antonio",
    Nachname: "Xie",
  ),
  "MartinX": (
    Vorname: "Martin",
    Nachname: "Xie",
  ),
  "YifanX": (
    Vorname: "Yifan",
    Nachname: "Xu",
  ),
  "YisuY": (
    Vorname: "Yisu",
    Nachname: "Yan",
  ),
  "LuisZ": (
    Vorname: "Luis",
    Nachname: "Zhang",
  ),
)
