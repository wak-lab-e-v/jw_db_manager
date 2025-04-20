from flask import Flask, render_template_string, request
import sqlite3

# Konfigurierbare Statusoptionen für alle Status-Dropdowns
STATUS_OPTIONS = [
    'neu',
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
        db=db
    )


@app.route("/details/<int:entry_id>")
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
    status = row[10]
    created_at = row[11]
    updated_at = row[12]
    # Status-Optionen importieren
    global STATUS_OPTIONS
    html = f'''
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>Details zum Eintrag</title>
        <style>
            body {{ font-family: sans-serif; background: #f8f9fa; }}
            .details-container {{ max-width: 700px; margin: 40px auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px #0001; padding: 48px 40px; }}
            .details-title-row {{ display: flex; align-items: baseline; gap: 2.5em; margin-bottom: 2.8em; }}
            .details-title-main {{ font-size: 2.2em; font-weight: 700; color: #333; }}
            .details-title-name {{ font-size: 1.5em; color: #1976d2; font-weight: 500; }}
            .details-row {{ display: flex; flex-direction: row; align-items: flex-start; margin-bottom: 2.2em; }}
            .details-label {{ width: 180px; font-weight: bold; font-size: 1.18em; color: #333; }}
            .details-value {{ flex: 1; font-size: 1.15em; color: #222; word-break: break-word; background: #f5f5f5; padding: 10px 22px; border-radius: 6px; }}
            .details-row-inline {{ display: flex; flex-direction: row; align-items: center; gap: 2em; margin-bottom: 2.2em; }}
            .details-label-inline {{ font-weight: bold; font-size: 1.18em; color: #333; margin-right: 0.7em; }}
            .details-value-inline {{ font-size: 1.15em; color: #222; background: #f5f5f5; padding: 10px 22px; border-radius: 6px; min-width: 120px; }}
            .details-status-row {{ display: flex; flex-direction: row; align-items: center; gap: 1em; margin-bottom: 2.2em; }}
            .details-status-label {{ font-weight: bold; font-size: 1.18em; color: #333; margin-right: 0.7em; }}
            .details-status-select {{ font-size: 1.1em; padding: 7px 20px; border-radius: 6px; border: 1px solid #bbb; background: #f0f0f0; color: #888; pointer-events: none; }}
            .details-meta-row {{ display: flex; flex-direction: row; align-items: center; gap: 2.5em; color: #888; font-size: 0.97em; margin-top: 2.7em; margin-bottom: 0.4em; }}
            .details-uid {{ font-size: 0.92em; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="details-container">
            <div class="details-title-row">
                <div class="details-title-main">Eintragsdetails</div>
                <div class="details-title-name">{vorname} {name}</div>
            </div>
            <div class="details-row-inline">
                <span class="details-label-inline">Vorname:</span>
                <span class="details-value-inline">{vorname}</span>
                <span class="details-label-inline">Name:</span>
                <span class="details-value-inline">{name}</span>
            </div>
            <div class="details-row">
                <div class="details-label">Bestellnummer:</div>
                <div class="details-value">{bestellnummer}</div>
            </div>
            <div class="details-row">
                <div class="details-label">Feiertag:</div>
                <div class="details-value">{feiertag}</div>
            </div>
            <div class="details-row">
                <div class="details-label">Feieruhrzeit:</div>
                <div class="details-value">{feieruhrzeit}</div>
            </div>
            <div class="details-row">
                <div class="details-label">Hinweis:</div>
                <div class="details-value">{hint}</div>
            </div>
            <div class="details-row">
                <div class="details-label">src_path:</div>
                <div class="details-value">{src_path}</div>
            </div>
            <div class="details-row">
                <div class="details-label">work_path:</div>
                <div class="details-value">{work_path}</div>
            </div>
            <div class="details-status-row">
                <span class="details-status-label">Status:</span>
                <select class="details-status-select" disabled>
                    {''.join([f'<option value="{opt}"'+(' selected' if opt==status else '')+f'>{opt}</option>' for opt in STATUS_OPTIONS])}
                </select>
            </div>
            <div class="details-meta-row">
                <span>Created: {created_at}</span>
                <span>Updated: {updated_at}</span>
                <span class="details-uid">UID: {uid}</span>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

if __name__ == "__main__":
    app.run(debug=True, port=5000)
