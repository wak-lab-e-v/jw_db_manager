from flask import Flask, render_template, request, Response
import sqlite3
import os
import subprocess
import datetime
from PIL import Image
import piexif

def get_image_info(file_path):
    """Extract image dimensions and DPI information from an image file"""
    try:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            with Image.open(file_path) as img:
                width, height = img.size
                dpi = img.info.get('dpi', (0, 0))
                return width, height, int(dpi[0]), int(dpi[1])
        return None, None, None, None
    except Exception as e:
        return None, None, None, None

# Konfigurierbare Statusoptionen für alle Status-Dropdowns
STATUS_OPTIONS = [
    'neu',
    'in Bearbeitung',
    'Erledigt',
    'Problem',
    'Storniert'
]

app = Flask(__name__)
DB_PATH = 'anmeldungen.db'  # Standard, kann per ?db=... überschrieben werden
TABLE = 'anmeldungen'

def get_db_connection(db_path):
    # Prüfen, ob die Datenbank existiert
    if not os.path.exists(db_path):
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None

@app.route("/")
def index():
    db = request.args.get("db") or DB_PATH
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    feiertag = request.args.get("feiertag", "")
    feieruhrzeit = request.args.get("feieruhrzeit", "")
    has_images = request.args.get("has_images", "")
    
    # Prüfen, ob die Datenbank existiert
    conn = get_db_connection(db)
    if conn is None:
        return render_template(
            "index.html",
            rows=[],
            q=q,
            status=status,
            status_options=[],
            feiertag=feiertag,
            feiertag_options=[],
            feieruhrzeit=feieruhrzeit,
            feieruhrzeit_options=[],
            has_images=has_images,
            db=db,
            db_error=f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        )
    
    try:
        cur = conn.cursor()
        # Status-Optionen
        cur.execute(f"SELECT DISTINCT status FROM {TABLE} ORDER BY status")
        status_options = [row[0] for row in cur.fetchall() if row[0]]
        # Feiertag-Optionen
        cur.execute(f"SELECT DISTINCT feiertag FROM {TABLE} ORDER BY feiertag")
        feiertag_options = [row[0] for row in cur.fetchall() if row[0]]
        # Feieruhrzeit-Optionen
        cur.execute(f"SELECT DISTINCT feieruhrzeit FROM {TABLE} ORDER BY feieruhrzeit")
        feieruhrzeit_options = [row[0] for row in cur.fetchall() if row[0]]
        # Query
        sql = f"SELECT * FROM {TABLE}"
        params = []
        where = []
        if q:
            where.append("(bestellnummer LIKE ? OR name LIKE ? OR vorname LIKE ? OR hint LIKE ?)")
            params.extend([f"%{q}%"] * 4)
        if status:
            where.append("status = ?")
            params.append(status)
        if feiertag:
            where.append("feiertag = ?")
            params.append(feiertag)
        if feieruhrzeit:
            where.append("feieruhrzeit = ?")
            params.append(feieruhrzeit)
        if has_images == "yes":
            where.append("work_path IS NOT NULL AND work_path != ''")
        elif has_images == "no":
            where.append("(work_path IS NULL OR work_path = '')")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
    except sqlite3.Error as e:
        return render_template(
            "index.html",
            rows=[],
            q=q,
            status=status,
            status_options=[],
            feiertag=feiertag,
            feiertag_options=[],
            feieruhrzeit=feieruhrzeit,
            feieruhrzeit_options=[],
            has_images=has_images,
            db=db,
            db_error=f"Fehler beim Zugriff auf die Tabelle '{TABLE}' in der Datenbank '{db}'."
        )
    return render_template(
        "index.html",
        rows=rows,
        q=q,
        status=status,
        status_options=status_options,
        feiertag=feiertag,
        feiertag_options=feiertag_options,
        feieruhrzeit=feieruhrzeit,
        feieruhrzeit_options=feieruhrzeit_options,
        has_images=has_images,
        db=db
    )

@app.route("/details/<int:entry_id>", methods=["GET", "POST"])
def details(entry_id):
    db = request.args.get("db") or DB_PATH
    full_size = request.args.get("full_size") == "1"
    
    # Prüfen, ob die Datenbank existiert
    conn = get_db_connection(db)
    if conn is None:
        return f'<h2>Die Datenbank "{db}" wurde nicht gefunden oder konnte nicht geöffnet werden.</h2>', 404
    
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {TABLE} WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return '<h2>Eintrag nicht gefunden</h2>', 404
    except sqlite3.Error as e:
        return f'<h2>Fehler beim Zugriff auf die Tabelle "{TABLE}" in der Datenbank "{db}".</h2>', 404
    
    # Felder extrahieren
    bestellnummer = row[1]
    vorname = row[3]
    name = row[2]
    uid = row[4]
    feiertag = row[5]
    feieruhrzeit = row[6]
    location = row[7]
    hint = row[8]
    src_path = row[9]
    work_path = row[10]
    
    final_picture_1 = row[11]
    final_picture_2 = row[12]
    final_picture_3 = row[13]
    status = row[14]
    created_at = row[15]
    updated_at = row[16]
    
    # Wenn POST-Request, Daten aktualisieren
    if request.method == "POST":
        vorname = request.form.get("vorname", vorname)
        name = request.form.get("name", name)
        hint = request.form.get("hint", hint)
        status = request.form.get("status", status)
        
        # Neue Werte für Feiertag und Feieruhrzeit
        new_feiertag = request.form.get("feiertag", feiertag)
        new_feieruhrzeit = request.form.get("feieruhrzeit", feieruhrzeit)
        
        # Validierung für Feiertag (TT.MM.YYYY)
        import re
        feiertag_valid = re.match(r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(19|20)\d\d$', new_feiertag) is not None if new_feiertag else True
        
        # Validierung für Feieruhrzeit (HH-MM)
        feieruhrzeit_valid = re.match(r'^([01]?[0-9]|2[0-3])\-([0-5][0-9])$', new_feieruhrzeit) is not None if new_feieruhrzeit else True
        
        # Finale Bilder aus dem Formular extrahieren
        new_final_picture_1 = request.form.get("final_picture_1", "")
        new_final_picture_2 = request.form.get("final_picture_2", "")
        new_final_picture_3 = request.form.get("final_picture_3", "")
        
        # Nur aktualisieren, wenn die Formate gültig sind
        if feiertag_valid and feieruhrzeit_valid:
            feiertag = new_feiertag
            feieruhrzeit = new_feieruhrzeit
            
            # Prüfen, ob ein Bild mehrfach als finales Bild ausgewählt wurde
            final_pictures = [pic for pic in [new_final_picture_1, new_final_picture_2, new_final_picture_3] if pic]
            if len(final_pictures) != len(set(final_pictures)):
                # Fehlermeldung setzen, wenn doppelte Bilder gefunden wurden
                hint = "FEHLER: Ein Bild kann nicht mehrfach als finales Bild ausgewählt werden!\n" + hint
            else:
                # Nur wenn keine doppelten Bilder vorhanden sind, die Werte aktualisieren
                final_picture_1 = new_final_picture_1
                final_picture_2 = new_final_picture_2
                final_picture_3 = new_final_picture_3
                
                # Datenbank aktualisieren
                conn = get_db_connection(db)
                cur = conn.cursor()
                cur.execute(f"UPDATE {TABLE} SET vorname = ?, name = ?, hint = ?, status = ?, feiertag = ?, feieruhrzeit = ?, final_picture_1 = ?, final_picture_2 = ?, final_picture_3 = ? WHERE id = ?", 
                           (vorname, name, hint, status, feiertag, feieruhrzeit, final_picture_1, final_picture_2, final_picture_3, entry_id))
                conn.commit()
                conn.close()
        else:
            # Fehlermeldung setzen (wird später im HTML angezeigt)
            error_msg = ""
            if not feiertag_valid:
                error_msg += "Feiertag muss im Format TT.MM.YYYY sein. "
            if not feieruhrzeit_valid:
                error_msg += "Feieruhrzeit muss im Format HH-MM sein."
            hint = error_msg + "\n" + hint
    
    # Dateien und Bilder für die Galerie vorbereiten
    image_files = []
    files = []
    file_count = 0
    
    if work_path and os.path.exists(work_path):
        file_count = len([f for f in os.listdir(work_path) if os.path.isfile(os.path.join(work_path, f))])
        
        # Dateien für die Tabelle vorbereiten
        for f in os.listdir(work_path):
            if os.path.isfile(os.path.join(work_path, f)):
                file_size = round(os.path.getsize(os.path.join(work_path, f))/1024, 1)
                width, height, dpi_x, dpi_y = get_image_info(os.path.join(work_path, f))
                
                files.append({
                    'name': os.path.basename(f),
                    'size': file_size,
                    'width': width if width else '-',
                    'height': height if height else '-',
                    'dpi_x': dpi_x if dpi_x else '-',
                    'dpi_y': dpi_y if dpi_y else '-'
                })
                
                # Bilder für die Galerie sammeln
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.psd')):
                    image_files.append(f)
    
    # Status-Optionen importieren
    global STATUS_OPTIONS
    
    # Template rendern
    return render_template(
        "details.html",
        entry_id=entry_id,
        bestellnummer=bestellnummer,
        vorname=vorname,
        name=name,
        uid=uid,
        feiertag=feiertag,
        feieruhrzeit=feieruhrzeit,
        location=location,
        hint=hint,
        src_path=src_path,
        work_path=work_path,
        final_picture_1=final_picture_1,
        final_picture_2=final_picture_2,
        final_picture_3=final_picture_3,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        status_options=STATUS_OPTIONS,
        image_files=image_files,
        files=files,
        file_count=file_count,
        full_size=full_size,
        db=db
    )

@app.route("/image/<int:entry_id>/<path:filename>")
def serve_image(entry_id, filename):
    # Get the entry's work_path from the database
    db = request.args.get("db") or DB_PATH
    
    # Prüfen, ob die Datenbank existiert
    conn = get_db_connection(db)
    if conn is None:
        return "Database not found", 404
    
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT work_path FROM {TABLE} WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return "Image not found", 404
    except sqlite3.Error as e:
        return "Database error", 404
    
    work_path = row[0]
    image_path = os.path.join(work_path, filename)
    
    # Check if the file exists and is within the work_path
    if not os.path.exists(image_path) or not os.path.isfile(image_path):
        return "Image not found", 404
    
    # Determine the content type based on file extension
    content_type = "image/jpeg"  # Default
    if filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".gif"):
        content_type = "image/gif"
    elif filename.lower().endswith(".bmp"):
        content_type = "image/bmp"
    
    # Read and return the image file
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    return Response(image_data, mimetype=content_type)

@app.route("/convert_image", methods=["GET", "POST"])
def convert_image():
    # Parameter aus GET oder POST Request holen
    if request.method == "POST":
        source_file = request.form.get("source_file")
        destination_file = request.form.get("destination_file")
        text = request.form.get("text")
    else:  # GET
        source_file = request.args.get("source_file")
        destination_file = request.args.get("destination_file")
        text = request.args.get("text")
    
    # Überprüfen, ob die Quelldatei existiert
    if not os.path.exists(source_file) or not os.path.isfile(source_file):
        return f"<h2>Fehler: Die Quelldatei '{source_file}' wurde nicht gefunden.</h2>", 404
    
    # Verzeichnis für die Zieldatei erstellen, falls es nicht existiert
    destination_dir = os.path.dirname(destination_file)
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    
    try:
        # Debug-Meldungen ausgeben
        print("\n==== BILDKONVERTIERUNG GESTARTET ====")
        print(f"Quelldatei: {source_file}")
        print(f"Zieldatei: {destination_file}")
        print(f"Text: {text}")
        
        # dbv_autoimgcov.py mit den entsprechenden Parametern aufrufen
        cmd = ["python", "dbv_autoimgcov.py", "auto", 
               "--source-file", source_file, 
               "--destination-file", destination_file, 
               "--text", text]
        
        print(f"Ausgeführter Befehl: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Rückgabecode: {result.returncode}")
        print(f"Ausgabe: {result.stdout}")
        print(f"Fehler: {result.stderr}")
        print("==== BILDKONVERTIERUNG BEENDET ====")
        
        if result.returncode == 0:
            # Zurück zur Detailseite mit einer Erfolgsmeldung
            entry_id = request.referrer.split("/")[-1].split("?")[0] if request.referrer else ""
            db = request.args.get("db") or DB_PATH
            
            # Direkt zur Detailseite zurückkehren
            return f"""<html>
                    <head>
                        <meta http-equiv='refresh' content='0;url=/details/{entry_id}?db={db}'>
                        <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                    </head>
                    <body>
                        <h2>Bild wurde erfolgreich konvertiert!</h2>
                        <p>Sie werden weitergeleitet...</p>
                        <p><a href='/details/{entry_id}?db={db}'>Klicken Sie hier, wenn Sie nicht automatisch weitergeleitet werden.</a></p>
                    </body>
                </html>"""
        else:
            # Fehler anzeigen
            return f"""<html>
                    <head>
                        <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                    </head>
                    <body>
                        <h2>Fehler bei der Bildkonvertierung</h2>
                        <p>Fehlermeldung: {result.stderr}</p>
                        <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                    </body>
                </html>"""
    except Exception as e:
        return f"""<html>
                <head>
                    <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                </head>
                <body>
                    <h2>Fehler bei der Bildkonvertierung</h2>
                    <p>Fehlermeldung: {str(e)}</p>
                    <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                </body>
            </html>"""

@app.route("/delete_image")
def delete_image():
    file_path = request.args.get("file")
    
    # Überprüfen, ob die Datei existiert
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"<h2>Fehler: Die Datei '{file_path}' wurde nicht gefunden.</h2>", 404
    
    try:
        # Debug-Meldungen ausgeben
        print("\n==== BILD LÖSCHEN GESTARTET ====")
        print(f"Datei: {file_path}")
        
        # Datei löschen
        os.remove(file_path)
        
        print(f"Datei wurde gelöscht: {file_path}")
        print("==== BILD LÖSCHEN BEENDET ====")
        
        # Zurück zur Detailseite
        entry_id = request.referrer.split("/")[-1].split("?")[0] if request.referrer else ""
        db = request.args.get("db") or DB_PATH
        
        # Direkt zur Detailseite zurückkehren
        return f"""<html>
                <head>
                    <meta http-equiv='refresh' content='0;url=/details/{entry_id}?db={db}'>
                    <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                </head>
                <body>
                    <h2>Bild wurde erfolgreich gelöscht!</h2>
                    <p>Sie werden weitergeleitet...</p>
                    <p><a href='/details/{entry_id}?db={db}'>Klicken Sie hier, wenn Sie nicht automatisch weitergeleitet werden.</a></p>
                </body>
            </html>"""
    except Exception as e:
        return f"""<html>
                <head>
                    <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                </head>
                <body>
                    <h2>Fehler beim Löschen der Datei</h2>
                    <p>Fehlermeldung: {str(e)}</p>
                    <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                </body>
            </html>"""

@app.route("/rotate_image")
def rotate_image():
    file_path = request.args.get("file")
    angle = int(request.args.get("angle", 0))
    
    # Überprüfen, ob die Datei existiert
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"<h2>Fehler: Die Datei '{file_path}' wurde nicht gefunden.</h2>", 404
    
    try:
        # Debug-Meldungen ausgeben
        print("\n==== BILD ROTATION GESTARTET ====")
        print(f"Datei: {file_path}")
        print(f"Winkel: {angle}")
        
        # dbv_rotateexif.py mit den entsprechenden Parametern aufrufen
        cmd = ["python", "dbv_rotateexif.py", file_path, file_path, str(angle)]
        
        print(f"Ausgeführter Befehl: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Rückgabecode: {result.returncode}")
        print(f"Ausgabe: {result.stdout}")
        print(f"Fehler: {result.stderr}")
        print("==== BILD ROTATION BEENDET ====")
        
        if result.returncode == 0:
            # Zurück zur Detailseite
            entry_id = request.referrer.split("/")[-1].split("?")[0] if request.referrer else ""
            db = request.args.get("db") or DB_PATH
            
            # Direkt zur Detailseite zurückkehren
            return f"""<html>
                    <head>
                        <meta http-equiv='refresh' content='0;url=/details/{entry_id}?db={db}'>
                        <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                    </head>
                    <body>
                        <h2>Bild wurde erfolgreich rotiert!</h2>
                        <p>Sie werden weitergeleitet...</p>
                        <p><a href='/details/{entry_id}?db={db}'>Klicken Sie hier, wenn Sie nicht automatisch weitergeleitet werden.</a></p>
                    </body>
                </html>"""
        else:
            # Fehler anzeigen
            return f"""<html>
                    <head>
                        <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                    </head>
                    <body>
                        <h2>Fehler bei der Bildrotation</h2>
                        <p>Fehlermeldung: {result.stderr}</p>
                        <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                    </body>
                </html>"""
    except Exception as e:
        return f"""<html>
                <head>
                    <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                </head>
                <body>
                    <h2>Fehler bei der Bildrotation</h2>
                    <p>Fehlermeldung: {str(e)}</p>
                    <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                </body>
            </html>"""

@app.route("/convert_psd")
def convert_psd():
    source_file = request.args.get("source_file")
    destination_file = request.args.get("destination_file")
    
    # Überprüfen, ob die Quelldatei existiert
    if not os.path.exists(source_file) or not os.path.isfile(source_file):
        return f"<h2>Fehler: Die Quelldatei '{source_file}' wurde nicht gefunden.</h2>", 404
    
    try:
        # Debug-Meldungen ausgeben
        print("\n==== PSD KONVERTIERUNG GESTARTET ====")
        print(f"Quelldatei: {source_file}")
        print(f"Zieldatei: {destination_file}")
        
        # dbv_psdconvert.py mit den entsprechenden Parametern aufrufen
        cmd = ["python", "dbv_psdconvert.py", source_file, destination_file]
        
        print(f"Ausgeführter Befehl: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Rückgabecode: {result.returncode}")
        print(f"Ausgabe: {result.stdout}")
        print(f"Fehler: {result.stderr}")
        print("==== PSD KONVERTIERUNG BEENDET ====")
        
        if result.returncode == 0:
            # Zurück zur Detailseite
            entry_id = request.referrer.split("/")[-1].split("?")[0] if request.referrer else ""
            db = request.args.get("db") or DB_PATH
            
            # Direkt zur Detailseite zurückkehren
            return f"""<html>
                    <head>
                        <meta http-equiv='refresh' content='0;url=/details/{entry_id}?db={db}'>
                        <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                    </head>
                    <body>
                        <h2>PSD-Datei wurde erfolgreich konvertiert!</h2>
                        <p>Sie werden weitergeleitet...</p>
                        <p><a href='/details/{entry_id}?db={db}'>Klicken Sie hier, wenn Sie nicht automatisch weitergeleitet werden.</a></p>
                    </body>
                </html>"""
        else:
            # Fehler anzeigen
            return f"""<html>
                    <head>
                        <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                    </head>
                    <body>
                        <h2>Fehler bei der PSD-Konvertierung</h2>
                        <p>Fehlermeldung: {result.stderr or result.stdout}</p>
                        <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                    </body>
                </html>"""
    except Exception as e:
        return f"""<html>
                <head>
                    <style>body {{ font-family: sans-serif; text-align: center; margin-top: 50px; }}</style>
                </head>
                <body>
                    <h2>Fehler bei der PSD-Konvertierung</h2>
                    <p>Fehlermeldung: {str(e)}</p>
                    <p><a href='{request.referrer}'>Zurück zur vorherigen Seite</a></p>
                </body>
            </html>"""

@app.route("/dbfunc", methods=["GET", "POST"])
def dbfunc():
    """Funktionen-Seite mit Dropdown-Menüs für Feierzeit und Feiertag"""
    db = request.args.get("db") or DB_PATH
    
    # Prüfen, ob die Datenbank existiert
    conn = get_db_connection(db)
    if conn is None:
        return "Database not found", 404
    
    # Feierzeiten und Feiertage aus der Datenbank abrufen
    try:
        cur = conn.cursor()
        
        # Feierzeiten abrufen
        cur.execute(f"SELECT DISTINCT feieruhrzeit FROM {TABLE} WHERE feieruhrzeit IS NOT NULL AND feieruhrzeit != '' ORDER BY feieruhrzeit")
        feierzeiten = [row[0] for row in cur.fetchall()]
        
        # Feiertage abrufen
        cur.execute(f"SELECT DISTINCT feiertag FROM {TABLE} WHERE feiertag IS NOT NULL AND feiertag != '' ORDER BY feiertag")
        feiertage = [row[0] for row in cur.fetchall()]
        
        # Locations abrufen
        cur.execute(f"SELECT DISTINCT location FROM {TABLE} WHERE location IS NOT NULL AND location != '' ORDER BY location")
        locations = [row[0] for row in cur.fetchall()]
        
        message = None
        success = False
        
        # POST-Anfrage verarbeiten
        if request.method == "POST":
            feierzeit = request.form.get("feierzeit", "")
            feiertag = request.form.get("feiertag", "")
            action = request.form.get("action", "")
            
            location = request.form.get("location", "")
            
            if not feierzeit and not feiertag and not location:
                message = "Bitte wählen Sie mindestens einen Filter aus (Feierzeit, Feiertag oder Location)."
                success = False
            elif action == "prepare_final_images":
                # Aktion: Finale Bilder im OUT bereitstellen
                try:
                    # Abfrage erstellen basierend auf den ausgewählten Filtern + Status = "Erledigt"
                    query = f"SELECT id, vorname, name, bestellnummer, work_path, final_picture_1, final_picture_2, final_picture_3 FROM {TABLE} WHERE status = 'Erledigt'"
                    params = []
                    
                    if feierzeit:
                        query += " AND feieruhrzeit = ?"
                        params.append(feierzeit)
                    
                    if feiertag:
                        query += " AND feiertag = ?"
                        params.append(feiertag)
                    
                    if location:
                        query += " AND location = ?"
                        params.append(location)
                    
                    # Daten abrufen
                    cur.execute(query, params)
                    entries = cur.fetchall()
                    
                    if not entries:
                        message = "Keine passenden Einträge gefunden."
                        success = False
                    else:
                        # Erstelle einen Ordnernamen basierend auf den ausgewählten Filtern
                        folder_components = []
                        if location:
                            folder_components.append(location)
                        if feiertag:
                            folder_components.append(feiertag)
                        if feierzeit:
                            folder_components.append(feierzeit)
                            
                        # Erstelle einen sicheren Ordnernamen (ersetze problematische Zeichen)
                        folder_name = "_".join(folder_components)
                        folder_name = folder_name.replace("/", "-").replace("\\", "-").replace(":", "-")
                        
                        # Definiere den Pfad zum OUT-Verzeichnis
                        out_dir = "/diashow/out"
                        target_dir = os.path.join(out_dir, folder_name)
                        
                        try:
                            # Erstelle das Verzeichnis, falls es nicht existiert
                            os.makedirs(target_dir, exist_ok=True)
                            
                            # Zähler für kopierte Bilder
                            copied_count = 0
                            skipped_count = 0
                            
                            # Log-Datei für alle Datensätze erstellen
                            log_filename = os.path.join(target_dir, f"db_records_{folder_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                            with open(log_filename, 'w', encoding='utf-8') as log_file:
                                log_file.write(f"Datenbankabfrage vom {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                log_file.write(f"Filter: {', '.join(filter(None, [location, feiertag, feierzeit]))}\n\n")
                                log_file.write("ID | Vorname | Name | Bestellnummer | Work Path | Final Picture 1 | Final Picture 2 | Final Picture 3\n")
                                log_file.write("-" * 120 + "\n")
                                for entry in entries:
                                    log_file.write(" | ".join(str(item) for item in entry) + "\n")
                            
                            # Iteriere über alle gefundenen Einträge
                            for entry in entries:
                                entry_id, vorname, name, bestellnummer, work_path, final_picture_1, final_picture_2, final_picture_3 = entry
                                
                                # Erstelle einen sicheren Basisnamen für die Bilder
                                safe_vorname = vorname.replace(" ", "_").replace("/", "-").replace("\\", "-").replace(":", "-")
                                safe_name = name.replace(" ", "_").replace("/", "-").replace("\\", "-").replace(":", "-")
                                safe_bestellnummer = str(bestellnummer).replace(" ", "_").replace("/", "-").replace("\\", "-").replace(":", "-")
                                base_filename = f"{safe_vorname}_{safe_name}_{safe_bestellnummer}"
                                
                                # Prüfe jedes der final_picture-Felder
                                final_pics = [final_picture_1, final_picture_2, final_picture_3]
                                
                                # Mindestens ein Feld muss Daten enthalten
                                has_valid_pic = False
                                
                                for i, pic_path in enumerate(final_pics, 1):
                                    if pic_path and os.path.exists(pic_path):
                                        has_valid_pic = True
                                        
                                        # Bestimme die Dateiendung
                                        _, ext = os.path.splitext(pic_path)
                                        
                                        # Erstelle den neuen Dateinamen
                                        new_filename = f"{base_filename}_row{i}{ext}"
                                        target_path = os.path.join(target_dir, new_filename)
                                        
                                        # Kopiere die Datei
                                        try:
                                            import shutil
                                            shutil.copy2(pic_path, target_path)
                                            copied_count += 1
                                            
                                            # Log für jede kopierte Datei
                                            copy_log_path = os.path.join(target_dir, f"copied_files_{folder_name}.log")
                                            with open(copy_log_path, 'a', encoding='utf-8') as copy_log:
                                                copy_log.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Kopiert: {pic_path} -> {target_path}\n")
                                        except Exception as copy_err:
                                            print(f"Fehler beim Kopieren von {pic_path}: {str(copy_err)}")
                                            skipped_count += 1
                                
                                if not has_valid_pic:
                                    skipped_count += 1
                            
                            # Erstelle eine Erfolgsmeldung
                            message = f"{len(entries)} Einträge gefunden. {copied_count} Bilder nach {target_dir} kopiert. {skipped_count} Einträge übersprungen."
                            success = True
                        except Exception as e:
                            message = f"Fehler bei der Verarbeitung: {str(e)}"
                            success = False
                        
                except Exception as e:
                    message = f"Fehler bei der Verarbeitung: {str(e)}"
                    success = False
            else:
                message = "Unbekannte Aktion"
                success = False
        
        conn.close()
        return render_template("dbfunc.html", 
                              db=db, 
                              feierzeiten=feierzeiten, 
                              feiertage=feiertage, 
                              locations=locations,
                              message=message, 
                              success=success)
    
    except sqlite3.Error as e:
        if conn:
            conn.close()
        return f"Datenbankfehler: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=4444)
