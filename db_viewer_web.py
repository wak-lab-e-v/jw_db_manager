from flask import Flask, render_template_string, request
import sqlite3
import os
from PIL import Image

def get_image_info(file_path):
    """Extract image dimensions and DPI information from an image file"""
    try:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            with Image.open(file_path) as img:
                width, height = img.size
                dpi = img.info.get('dpi', (0, 0))
                return f'<td style="text-align: center; padding: 5px; border-bottom: 1px solid #eee;">{width} x {height}</td>' + \
                       f'<td style="text-align: center; padding: 5px; border-bottom: 1px solid #eee;">{int(dpi[0])} x {int(dpi[1])}</td>'
        return '<td style="text-align: center; padding: 5px; border-bottom: 1px solid #eee;">-</td>' + \
               '<td style="text-align: center; padding: 5px; border-bottom: 1px solid #eee;">-</td>'
    except Exception as e:
        return '<td style="text-align: center; padding: 5px; border-bottom: 1px solid #eee;">-</td>' + \
               '<td style="text-align: center; padding: 5px; border-bottom: 1px solid #eee;">-</td>'

# Konfigurierbare Statusoptionen für alle Status-Dropdowns
STATUS_OPTIONS = [
    'neu importiert',
    'in Bearbeitung',
    'abgeschlossen',
    'wartet',
    'storniert'
]

app = Flask(__name__)
DB_PATH = 'anmeldungen.db'  # Standard, kann per ?db=... überschrieben werden
TABLE = 'anmeldungen'

TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Datenbank-Viewer Web</title>
    <style>
        body { font-family: sans-serif; background: #f8f9fa; }
        table { border-collapse: collapse; width: 100%; background: #fff; margin-top: 1em; }
        th, td { border: 1px solid #ccc; padding: 8px 10px; }
        th { background: #e9ecef; }
        tr:nth-child(even) { background: #f2f2f2; }
        .searchbar { margin-top: 1em; }
        .filter { margin-left: 1em; }
    </style>
</head>
<body>
    <h1>Datenbank-Übersicht</h1>
    <p style="font-weight:bold;">{{ rows|length }} Einträge gefunden.</p>
    <form method="get" class="searchbar" style="display: flex; align-items: center; justify-content: space-between; gap: 1em;" id="searchForm">
        <div style="flex:1; min-width:200px; display: flex; align-items: center; gap: 0.5em;">
            <input type="text" name="q" id="searchInput" value="{{ q }}" placeholder="Suche...">
            <button type="submit">Suchen/Filtern</button>
            <button type="button" onclick="resetSearch()">Zurücksetzen</button>
            <input type="hidden" name="db" value="{{ db }}">
        </div>
        <div style="display:flex; align-items:center; gap:0.5em;">
            <label for="status">Status:</label>
            <select name="status" id="status" class="filter" onchange="this.form.submit()">
                <option value="">Alle</option>
                {% for s in status_options %}
                    <option value="{{ s }}" {% if s == status %}selected{% endif %}>{{ s }}</option>
                {% endfor %}
            </select>
            <label for="feiertag">Feiertag:</label>
            <select name="feiertag" id="feiertag" class="filter" onchange="this.form.submit()">
                <option value="">Alle</option>
                {% for f in feiertag_options %}
                    <option value="{{ f }}" {% if f == feiertag %}selected{% endif %}>{{ f }}</option>
                {% endfor %}
            </select>
            <label for="feieruhrzeit">Feierzeit:</label>
            <select name="feieruhrzeit" id="feieruhrzeit" class="filter" onchange="this.form.submit()">
                <option value="">Alle</option>
                {% for t in feieruhrzeit_options %}
                    <option value="{{ t }}" {% if t == feieruhrzeit %}selected{% endif %}>{{ t }}</option>
                {% endfor %}
            </select>
            <label for="has_images">Bilder:</label>
            <select name="has_images" id="has_images" class="filter" onchange="this.form.submit()">
                <option value="">Alle</option>
                <option value="yes" {% if has_images == 'yes' %}selected{% endif %}>Vorhanden</option>
                <option value="no" {% if has_images == 'no' %}selected{% endif %}>Nicht vorhanden</option>
            </select>
        </div>
    </form>
    <script>
    function resetSearch() {
        document.getElementById('searchInput').value = '';
        document.getElementById('searchForm').submit();
    }
    </script>
    <table>
        <tr>
            <th>Bestellnummer</th>
            <th style="width:125px;">Vorname</th>
            <th>Name</th>
            <th>Feieruhrzeit</th>
            <th>Feiertag</th>
            <th>Hint</th>
            <th>Status</th>
            <th>Created</th>
            <th>Updated</th>
            <th>Bilder</th>
            <th>Final</th>
            <th>Details</th>
        </tr>
        {% for row in rows %}
        <tr>
            <td>{{ row['bestellnummer'] }}</td>
            <td style="text-align:right">{{ row['vorname'] }}</td>
            <td style="text-align:left">{{ row['name'] }}</td>
            <td>{{ row['feieruhrzeit'] }}</td>
            <td>{{ row['feiertag'] }}</td>
            <td>{{ row['hint'] }}</td>
            <td>{{ row['status'] }}</td>
            <td>{{ row['created_at'] }}</td>
            <td>{{ row['updated_at'] }}</td>
            <td style="text-align:center">
                {% if row['work_path'] %}
                <span title="Bilder vorhanden" style="color: green; font-size: 1.2em;">&#128247;</span>
                {% else %}
                
                {% endif %}
            </td>
            <td style="text-align:center">
                {% if row['final_picture_1'] %}<span title="Final Bild 1" style="color: blue;">1</span>{% endif %}
                {% if row['final_picture_2'] %}<span title="Final Bild 2" style="color: blue;">2</span>{% endif %}
                {% if row['final_picture_3'] %}<span title="Final Bild 3" style="color: blue;">3</span>{% endif %}
            </td>
            <td><a href="/details/{{ row['id'] }}?db={{ db }}" target="_blank"><button>Details</button></a></td>
        </tr>
        {% endfor %}
    </table>
    <p style="font-weight:bold;">{{ rows|length }} Einträge gefunden.</p>
</body>
</html>
'''

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    db = request.args.get("db") or DB_PATH
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    feiertag = request.args.get("feiertag", "")
    feieruhrzeit = request.args.get("feieruhrzeit", "")
    has_images = request.args.get("has_images", "")
    conn = get_db_connection(db)
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
        where.append("(bestellnummer LIKE ? OR name LIKE ? OR vorname LIKE ? OR status LIKE ?)")
        params += [f"%{q}%"] * 4
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
    return render_template_string(
        TEMPLATE,
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
    conn = get_db_connection(db)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {TABLE} WHERE id = ?", (entry_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return '<h2>Eintrag nicht gefunden</h2>', 404
    # Felder extrahieren
    bestellnummer = row[1]
    vorname = row[3]
    name = row[2]
    uid = row[4]
    feiertag = row[5]
    feieruhrzeit = row[6]
    hint = row[7]
    src_path = row[8]
    work_path = row[9]
    final_picture_1 = row[10] if len(row) > 13 else None
    final_picture_2 = row[11] if len(row) > 13 else None
    final_picture_3 = row[12] if len(row) > 13 else None
    status = row[13] if len(row) > 13 else row[10]
    created_at = row[14] if len(row) > 13 else row[11]
    updated_at = row[15] if len(row) > 13 else row[12]
    
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
    # Status-Optionen importieren
    global STATUS_OPTIONS
    html = f'''
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>{vorname} {name} - Details</title>
        <style>
            body {{ font-family: sans-serif; background: #f8f9fa; margin: 0; padding: 0; }}
            .details-container {{ width: calc(100% - 100px); margin: 50px; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px #0001; padding: 48px 40px; box-sizing: border-box; }}
            .details-title-row {{ display: flex; align-items: baseline; gap: 2.5em; margin-bottom: 2.8em; }}
            .details-title-main {{ font-size: 2.2em; font-weight: 700; color: #333; }}
            .details-title-name {{ font-size: 1.5em; color: #1976d2; font-weight: 500; }}
            .details-row {{ display: flex; flex-direction: row; align-items: flex-start; margin-bottom: 2.2em; }}
            .details-label {{ width: 180px; font-weight: bold; font-size: 1.18em; color: #333; }}
            .details-value {{ flex: 1; font-size: 1.15em; color: #222; word-break: break-word; background: #f5f5f5; padding: 10px 22px; border-radius: 6px; }}
            .details-row-inline {{ display: flex; flex-direction: row; align-items: center; margin-bottom: 2.2em; }}
            .details-label-inline {{ width: 180px; font-weight: bold; font-size: 1.18em; color: #333; }}
            .details-value-inline {{ flex: 1; font-size: 1.15em; color: #222; padding: 0; }}
            .details-status-row {{ display: flex; flex-direction: row; align-items: center; margin-bottom: 2.2em; }}
            .details-status-label {{ width: 180px; font-weight: bold; font-size: 1.18em; color: #333; }}
            .details-status-select {{ font-size: 1.1em; padding: 7px 20px; border-radius: 6px; border: 1px solid #bbb; background: white; color: #222; }}
            .details-meta-row {{ display: flex; flex-direction: row; align-items: center; gap: 2.5em; color: #888; font-size: 0.97em; margin-top: 2.7em; margin-bottom: 0.4em; }}
            .details-uid {{ font-size: 0.92em; color: #aaa; }}
            .save-button {{ background: #1976d2; color: white; border: none; border-radius: 5px; padding: 10px 20px; font-size: 1.1em; cursor: pointer; margin-top: 20px; }}
            .save-button:hover {{ background: #1565c0; }}
            input[type=text], textarea {{ width: 100%; font-size: 1.15em; padding: 10px; border-radius: 6px; border: 1px solid #ccc; background: white; }}
            textarea {{ min-height: 80px; }}
        </style>
    </head>
    <body>
        <div class="details-container">
            <div class="details-title-row">
                <div class="details-title-main">Eintragsdetails</div>
                <div class="details-title-name">{vorname} {name} <span style="font-size: 0.85em; opacity: 0.8;">({bestellnummer})</span></div>
            </div>
            <form method="post">
                <div class="details-row-inline" style="display: flex; gap: 20px; align-items: flex-start;">
                    <div style="width: 60%;">
                        <span class="details-label-inline">Name:</span>
                        <div style="display: flex; gap: 10px;">
                            <span class="details-value-inline" style="flex: 1;">
                                <input type="text" name="vorname" value="{vorname}" style="width:95%; padding:8px; border-radius:5px; border:1px solid #ccc;">
                            </span>
                            <span class="details-value-inline" style="flex: 1;">
                                <input type="text" name="name" value="{name}" style="width:95%; padding:8px; border-radius:5px; border:1px solid #ccc;">
                            </span>
                        </div>
                    </div>
                    <div style="width: 33%;">
                        <div class="details-label">Feiertag:</div>
                        <div class="details-value" style="background: transparent; padding: 0;">
                            <input type="text" name="feiertag" value="{feiertag}" style="padding:8px; border-radius:5px; border:1px solid #ccc; width: 90%;" placeholder="TT.MM.YYYY">
                            <div style="font-size: 0.8em; color: #666; margin-top: 5px;">Format: TT.MM.YYYY</div>
                        </div>
                    </div>
                </div>
                <div class="details-row-inline" style="display: flex; gap: 20px; align-items: flex-start; margin-top: -10px;">
                    <div style="width: 60%;">
                        <div class="details-status-row" style="margin-top: 0;">
                            <span class="details-status-label">Status:</span>
                            <select class="details-status-select" name="status">
                                {''.join([f'<option value="{opt}"'+(' selected' if opt==status else '')+f'>{opt}</option>' for opt in STATUS_OPTIONS])}
                            </select>
                        </div>
                    </div>
                    <div style="width: 33%;">
                        <div class="details-label">Feieruhrzeit:</div>
                        <div class="details-value" style="background: transparent; padding: 0;">
                            <input type="text" name="feieruhrzeit" value="{feieruhrzeit}" style="padding:8px; border-radius:5px; border:1px solid #ccc; width: 90%;" placeholder="HH-MM">
                            <div style="font-size: 0.8em; color: #666; margin-top: 5px;">Format: HH-MM</div>
                        </div>
                    </div>
                </div>
                <div class="details-row" style="margin-top: 10px; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <div class="details-label">Hinweis:</div>
                        <div class="details-value" style="background: transparent; padding: 0; max-width: 800px;">
                            <textarea name="hint" style="width: 95%;">{hint}</textarea>
                        </div>
                    </div>
                    <div style="margin-left: 20px; display: flex; align-items: center; height: 100%;">
                        <button type="submit" class="save-button">Speichern</button>
                    </div>
                </div>
                
            </form>
            <hr/>
            <div style="margin: 15px 0; color: #333;">
                <h3 style="margin-bottom: 10px;">Finale Bilder auswählen:</h3>
                <form method="post" style="display: flex; gap: 20px; margin-bottom: 20px;">
                    <div style="flex: 1;">
                        <label for="final_picture_1" style="display: block; margin-bottom: 5px; font-weight: bold;">Bild 1:</label>
                        <select name="final_picture_1" id="final_picture_1" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #ccc;">
                            <option value="">-- Kein Bild ausgewählt --</option>
                            {''.join([f'<option value="{os.path.join(work_path, f)}" {"selected" if final_picture_1 == os.path.join(work_path, f) else ""}>{os.path.basename(f)}</option>' 
                                      for f in os.listdir(work_path) 
                                      if work_path and os.path.exists(work_path) and os.path.isfile(os.path.join(work_path, f)) and 
                                      f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])}
                        </select>
                    </div>
                    <div style="flex: 1;">
                        <label for="final_picture_2" style="display: block; margin-bottom: 5px; font-weight: bold;">Bild 2:</label>
                        <select name="final_picture_2" id="final_picture_2" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #ccc;">
                            <option value="">-- Kein Bild ausgewählt --</option>
                            {''.join([f'<option value="{os.path.join(work_path, f)}" {"selected" if final_picture_2 == os.path.join(work_path, f) else ""}>{os.path.basename(f)}</option>' 
                                      for f in os.listdir(work_path) 
                                      if work_path and os.path.exists(work_path) and os.path.isfile(os.path.join(work_path, f)) and 
                                      f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])}
                        </select>
                    </div>
                    <div style="flex: 1;">
                        <label for="final_picture_3" style="display: block; margin-bottom: 5px; font-weight: bold;">Bild 3:</label>
                        <select name="final_picture_3" id="final_picture_3" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #ccc;">
                            <option value="">-- Kein Bild ausgewählt --</option>
                            {''.join([f'<option value="{os.path.join(work_path, f)}" {"selected" if final_picture_3 == os.path.join(work_path, f) else ""}>{os.path.basename(f)}</option>' 
                                      for f in os.listdir(work_path) 
                                      if work_path and os.path.exists(work_path) and os.path.isfile(os.path.join(work_path, f)) and 
                                      f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])}
                        </select>
                    </div>
                    <div style="display: flex; align-items: flex-end;">
                        <button type="submit" style="padding: 8px 15px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Speichern</button>
                    </div>
                </form>
                
                <h3 style="margin-bottom: 10px;">Dateien: {len([f for f in os.listdir(work_path) if work_path and os.path.exists(work_path) and os.path.isfile(os.path.join(work_path, f))]) if work_path and os.path.exists(work_path) else 0} gefunden</h3>
                
                <!-- Dateiliste mit Größen -->
                <div style="margin-bottom: 20px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #f5f5f5;">
                            <th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Dateiname</th>
                            <th style="text-align: right; padding: 5px; border-bottom: 1px solid #ddd;">Größe</th>
                            <th style="text-align: center; padding: 5px; border-bottom: 1px solid #ddd;">Dimensionen</th>
                            <th style="text-align: center; padding: 5px; border-bottom: 1px solid #ddd;">DPI</th>
                        </tr>
                        {''.join([f'<tr>' +
                                  f'<td style="padding: 5px; border-bottom: 1px solid #eee;">{os.path.basename(f)}</td>' +
                                  f'<td style="text-align: right; padding: 5px; border-bottom: 1px solid #eee;">{round(os.path.getsize(os.path.join(work_path, f))/1024, 1)} KB</td>' +
                                  get_image_info(os.path.join(work_path, f)) +
                                  f'</tr>'
                                  for f in os.listdir(work_path) 
                                  if work_path and os.path.exists(work_path) and os.path.isfile(os.path.join(work_path, f))]) 
                         if work_path and os.path.exists(work_path) else '<tr><td colspan="4" style="color: #888; padding: 5px;">Keine Dateien vorhanden</td></tr>'}
                    </table>
                </div>
                
                <!-- Bildergalerie mit Toggle-Button für Bildgröße -->
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <h3 style="margin-bottom: 0; margin-right: 15px;">Bildergalerie:</h3>
                    {"<button onclick='window.location.href = window.location.href.replace(\"&full_size=1\", \"\");' style='padding: 5px 10px; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; cursor: pointer;'>Thumbnail anzeigen</button>" if request.args.get("full_size") else f"<button onclick=\"window.location.href = window.location.href + '&full_size=1';\" style=\"padding: 5px 10px; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; cursor: pointer;\">Originalgröße anzeigen</button>"}
                </div>
                
                <div id="imageGallery" style="display: flex; flex-direction: column; gap: 15px;">
                    {''.join([f'<div style="display: flex; align-items: center; margin-bottom: 10px;">' +
                              f'<img src="/image/{entry_id}/{os.path.basename(f)}" class="gallery-image" style="max-width: {"none" if request.args.get("full_size") else "400px"}; max-height: {"none" if request.args.get("full_size") else "400px"}; object-fit: contain; margin-right: 15px;">' +
                              f'<div style="display: flex; flex-direction: column; gap: 5px;">' +
                              f'<div style="font-size: 0.9em;">{os.path.basename(f)}</div>' +
                              f'<div style="display: flex; gap: 10px;">' +
                              f'<form method="post" style="display: inline;">' +
                              f'<input type="hidden" name="final_picture_1" value="{os.path.join(work_path, f)}">' +
                              f'<button type="submit" style="padding: 3px 8px; background-color: {"#007bff" if final_picture_1 == os.path.join(work_path, f) else "#f0f0f0"}; color: {"white" if final_picture_1 == os.path.join(work_path, f) else "black"}; border: 1px solid #ccc; border-radius: 3px; cursor: pointer;">' +
                              f'Bild 1{" ✓" if final_picture_1 == os.path.join(work_path, f) else ""}</button>' +
                              f'</form>' +
                              f'<form method="post" style="display: inline;">' +
                              f'<input type="hidden" name="final_picture_2" value="{os.path.join(work_path, f)}">' +
                              f'<button type="submit" style="padding: 3px 8px; background-color: {"#007bff" if final_picture_2 == os.path.join(work_path, f) else "#f0f0f0"}; color: {"white" if final_picture_2 == os.path.join(work_path, f) else "black"}; border: 1px solid #ccc; border-radius: 3px; cursor: pointer;">' +
                              f'Bild 2{" ✓" if final_picture_2 == os.path.join(work_path, f) else ""}</button>' +
                              f'</form>' +
                              f'<form method="post" style="display: inline;">' +
                              f'<input type="hidden" name="final_picture_3" value="{os.path.join(work_path, f)}">' +
                              f'<button type="submit" style="padding: 3px 8px; background-color: {"#007bff" if final_picture_3 == os.path.join(work_path, f) else "#f0f0f0"}; color: {"white" if final_picture_3 == os.path.join(work_path, f) else "black"}; border: 1px solid #ccc; border-radius: 3px; cursor: pointer;">' +
                              f'Bild 3{" ✓" if final_picture_3 == os.path.join(work_path, f) else ""}</button>' +
                              f'</form>' +
                              f'</div>' +
                              f'</div>' +
                              f'</div>' 
                              for f in os.listdir(work_path) 
                              if work_path and os.path.exists(work_path) and os.path.isfile(os.path.join(work_path, f)) and 
                              f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]) 
                     if work_path and os.path.exists(work_path) and any(f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')) for f in os.listdir(work_path) if os.path.isfile(os.path.join(work_path, f))) 
                     else '<div style="color: #888;">Keine Bilder vorhanden</div>'}
                
            </div>
            <hr/>
            <div style="margin-top: 2.7em; margin-bottom: 0.4em; color: #888; font-size: 0.97em;">
                <div style="margin-bottom: 8px;">Quell Path: {src_path}</div>
                <div style="margin-bottom: 8px;">Arbeits Path: {work_path}</div>
                <div style="margin-bottom: 8px;">Final Bild 1: {final_picture_1 or '-'}</div>
                <div style="margin-bottom: 8px;">Final Bild 2: {final_picture_2 or '-'}</div>
                <div style="margin-bottom: 8px;">Final Bild 3: {final_picture_3 or '-'}</div>
                <div class="details-meta-row">
                    <span>Created: {created_at}</span>
                    <span>Updated: {updated_at}</span>
                    <span class="details-uid">UID: {uid}</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route("/image/<int:entry_id>/<path:filename>")
def serve_image(entry_id, filename):
    # Get the entry's work_path from the database
    db = request.args.get("db") or DB_PATH
    conn = get_db_connection(db)
    cur = conn.cursor()
    cur.execute(f"SELECT work_path FROM {TABLE} WHERE id = ?", (entry_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return "Image not found", 404
    
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
    
    from flask import Response
    return Response(image_data, mimetype=content_type)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
