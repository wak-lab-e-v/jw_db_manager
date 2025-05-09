# Jugendweihe DB Manager

Ein Tool zur Sortierung und Namenszuordnung, um eine Videoslideshow der Teilnehmerinnen und Teilnehmer zu erstellen.
Die Scripts erstellen eine Datenbank aus einer Excel welche alle Daten enthlten muss. Dann werden die Bilder welche in Verzeichnissen einsortiert sein müssen eingelesen.
Danach kann man über eine Webseite im Browser alle Daten und Bilder anschauen und bearbeiten.
Das Tool bietet aktuell die Möglichkeit Bilder mit Namen zu versehen und vorher zu drehen.
Dann werden jedem Teilnehmer drei Bilder zugeordnet. Diese landen dann in einer Ausgabe für den Videoschnitt.

## Installation

Um das Projekt auszuführen, stelle sicher, dass du die Python-Pakete der requirements.txt installiert hast. Du kannst dies mit dem folgenden Befehl tun: pip install -r requirements.txt
Oder besser nutze uv dann reicht -> uv run scriptname.py

````

Optional ein Datenbakbrowser
```bash
sudo apt install sqlitebrowswer
````

## Verwendung

    Klone das Repository oder lade die Dateien herunter.
    Installiere die erforderlichen Pakete wie oben beschrieben. Oder starte direkt mit uv run scriptname.py
    Es muss eine Excel geben in der alle Personen und weitere Infos zu Daten und zum Ort der Feier vorhanden sind.

### Anmeldung DB erzeugen

Die Spalten der Excel werden in der excel_config.py zugeordnet.

```bash
python3 db_manager.py import --excel-file ~Bilder/Anmeldung_Excel.xlsx --db-file anmeldungen.db
oder
uv run db_manager.py import --excel-file ~Bilder/Anmeldung_Excel.xlsx --db-file anmeldungen.db
```

Datenbanktabellen wurden neu erstellt.
Import abgeschlossen: 364 Datensätze verarbeitet

- 364 neue Datensätze eingefügt
- 0 bestehende Datensätze übersprungen (keine Änderungen vorgenommen)

#### Zuordnung der Bild Importverzeichnis root

Der Feiertag wird hier zugeordnet. Die Dateien müssen in Ordnern mit dem Datum im Namen abgelegt sein z.B. Feier_24.05.25

```bash
python3 db_manager.py checksrc --db-file anmeldungen.db -p ~/Bilder/Importpath
oder
uv run db_manager.py checksrc --db-file anmeldungen.db -p ~/Bilder/Importpath
```

Gefunden: ID 364, Doe Jon, Feiertag: 24.05.2025 -> ../source/Feier_24.05.25

Ergebnis der Prüfung:

- 364 Quellverzeichnisse gefunden und aktualisiert
- 0 Quellverzeichnisse nicht gefunden

Neuen Bilderstamm anlegen mit copy oder (move gefährlich, aber dann sieht man welche Dateinamen nicht matchen, Importstamm aber vorher sichern)

```bash
python3 db_manager.py checkpic --db-file anmeldungen.db --copy ~/Bilder/Sorted
oder
uv run db_manager.py checkpic --db-file anmeldungen.db --copy ~/Bilder/Sorted
```

Die Datenbank kann kann mit sqlitebrowswer geprüft werden

```bash
sqlitebrowswer anmeldungen.db
```

### Local starten (Rudimentär)

Es muss erst im System tkinter installiert werden.
zB. brew install python-tk

```bash
python3 db_viewer.py anmeldungen.db
oder
uv run db_viewer.py anmeldungen.db
```

### Webserver starten

Die Datenbank anmeldung.db muss im selben Verzeichis liegen

```bash
python3 db_viewer_web.py
oder
uv run db_viewer_web.py
```

#### Browser

<http://localhost:4444>

## Mitwirkende

    Denny
    Hilde

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.
