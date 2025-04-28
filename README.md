# Jugendweihe DB Manager

Ein Tool zur Sortierung und Namenszuordnung, um eine Videoslideshow der Teilnehmerinnen und Teilnehmer zu erstellen.

## Installation

Um das Projekt auszuführen, stelle sicher, dass du die folgenden Python-Pakete installiert hast:

```bash
pip install pandas>=1.3.0
pip install openpyxl>=3.0.0
pip install customtkinter
pip install Flask>=2.0.0
sudo apt install python3-psd-tools
sudo apt install python3-piexif
```

Optional ein Datenbakbrowser
```bash
sudo apt install sqlitebrowswer
```

## Verwendung

    Klone das Repository oder lade die Dateien herunter.
    Installiere die erforderlichen Pakete wie oben beschrieben.
    Starte die Anwendung und folge den Anweisungen zur Erstellung der Videoslideshow.

### Anmeldung DB erzeugen
```bash
python3 db_manager.py import --excel-file ~Bilder/Anmeldung_Excel.xlsx --db-file anmeldungen.db
```
Datenbanktabellen wurden neu erstellt.
Import abgeschlossen: 364 Datensätze verarbeitet
  - 364 neue Datensätze eingefügt
  - 0 bestehende Datensätze übersprungen (keine Änderungen vorgenommen)

#### Zuordnung der Bild Importverzeichnis root
Der Feiertag wird hier zugeordnet. Die Dateien müssen in Ordnern mit dem Datum im Namen abgelegt sein z.B. Feier_24.05.25
```bash
python3 db_manager.py checksrc --db-file anmeldungen.db -p ~/Bilder/Importpath
```

Gefunden: ID 364, Doe Jon, Feiertag: 24.05.2025 -> ../source/Feier_24.05.25

Ergebnis der Prüfung:
  - 364 Quellverzeichnisse gefunden und aktualisiert
  - 0 Quellverzeichnisse nicht gefunden


Neuen Bilderstamm anlegen mit copy oder (move gefährlich, aber dann sieht man welche Dateinamen nicht matchen, Importstamm aber vorher sichern) 
```bash
python3 db_manager.py checkpic --db-file anmeldungen.db --copy ~/Bilder/Sorted
```

Die Datenbank kann kann mit sqlitebrowswer geprüft werden
```bash
sqlitebrowswer anmeldungen.db
```

### Local starten (Rudimentär)
```bash
python3 db_viewer.py
```

### Webserver starten
 Die Datenbank anmeldung.db muss im selben Verzeichis liegen

```bash
python3 db_viewer_web.py
```

#### Browser

http://localhost:4444


## Mitwirkende

    Denny
    Hilde

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.
