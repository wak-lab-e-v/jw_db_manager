#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import os
import re
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'db_editor_secret_key'  # Für Flash-Nachrichten

# Standardkonfiguration
DB_PATH = 'anmeldungen.db'  # Standard, kann per ?db=... überschrieben werden

def get_db_connection(db_path):
    """Stellt eine Verbindung zur Datenbank her"""
    # Prüfen, ob die Datenbank existiert
    if not os.path.exists(db_path):
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None

def get_table_schema(conn, table_name):
    """Gibt das Schema einer Tabelle zurück"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    except sqlite3.Error:
        return []

def get_tables(conn):
    """Gibt alle Tabellen in der Datenbank zurück"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error:
        return []

def execute_query(conn, query, params=None):
    """Führt eine SQL-Abfrage aus und gibt die Ergebnisse zurück"""
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Wenn es sich um ein SELECT handelt, Ergebnisse zurückgeben
        if query.strip().upper().startswith("SELECT"):
            return cursor.fetchall()
        else:
            conn.commit()
            return {"affected_rows": cursor.rowcount}
    except sqlite3.Error as e:
        return {"error": str(e)}

@app.route("/")
def index():
    """Hauptseite mit Datenbankübersicht"""
    db = request.args.get("db") or DB_PATH
    
    # Prüfen, ob die Datenbank existiert
    conn = get_db_connection(db)
    if conn is None:
        return render_template(
            "db_edit_index.html",
            tables=[],
            db=db,
            db_error=f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        )
    
    # Tabellen abrufen
    tables = get_tables(conn)
    conn.close()
    
    return render_template(
        "db_edit_index.html",
        tables=tables,
        db=db
    )

@app.route("/table/<table_name>")
def view_table(table_name):
    """Zeigt den Inhalt einer Tabelle an"""
    db = request.args.get("db") or DB_PATH
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    offset = (page - 1) * limit
    search = request.args.get("search", "")
    
    conn = get_db_connection(db)
    if conn is None:
        return render_template(
            "db_edit_table.html",
            table_name=table_name,
            columns=[],
            rows=[],
            db=db,
            db_error=f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        )
    
    # Schema der Tabelle abrufen
    schema = get_table_schema(conn, table_name)
    if not schema:
        conn.close()
        return render_template(
            "db_edit_table.html",
            table_name=table_name,
            columns=[],
            rows=[],
            db=db,
            db_error=f"Die Tabelle '{table_name}' wurde nicht gefunden."
        )
    
    columns = [col[1] for col in schema]  # Spaltennamen
    column_types = {col[1]: col[2] for col in schema}  # Spaltentypen
    primary_key = next((col[1] for col in schema if col[5] == 1), None)  # Primärschlüssel
    
    # Suchbedingung erstellen
    where_clause = ""
    params = []
    if search:
        search_conditions = []
        for col in columns:
            search_conditions.append(f"{col} LIKE ?")
            params.append(f"%{search}%")
        where_clause = " WHERE " + " OR ".join(search_conditions)
    
    # Gesamtanzahl der Datensätze
    count_query = f"SELECT COUNT(*) FROM {table_name}{where_clause}"
    count_result = execute_query(conn, count_query, params)
    total_rows = count_result[0][0] if isinstance(count_result, list) else 0
    
    # Datensätze abrufen
    query = f"SELECT * FROM {table_name}{where_clause} LIMIT {limit} OFFSET {offset}"
    rows = execute_query(conn, query, params)
    
    # Gesamtanzahl der Seiten
    total_pages = (total_rows + limit - 1) // limit
    
    conn.close()
    
    return render_template(
        "db_edit_table.html",
        table_name=table_name,
        columns=columns,
        column_types=column_types,
        primary_key=primary_key,
        rows=rows,
        db=db,
        page=page,
        limit=limit,
        total_pages=total_pages,
        total_rows=total_rows,
        search=search
    )

@app.route("/edit/<table_name>/<row_id>", methods=["GET", "POST"])
def edit_row(table_name, row_id):
    """Bearbeitet einen Datensatz"""
    db = request.args.get("db") or DB_PATH
    
    conn = get_db_connection(db)
    if conn is None:
        return render_template(
            "db_edit_row.html",
            table_name=table_name,
            row={},
            columns=[],
            db=db,
            db_error=f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        )
    
    # Schema der Tabelle abrufen
    schema = get_table_schema(conn, table_name)
    if not schema:
        conn.close()
        return render_template(
            "db_edit_row.html",
            table_name=table_name,
            row={},
            columns=[],
            db=db,
            db_error=f"Die Tabelle '{table_name}' wurde nicht gefunden."
        )
    
    columns = [col[1] for col in schema]  # Spaltennamen
    column_types = {col[1]: col[2] for col in schema}  # Spaltentypen
    primary_key = next((col[1] for col in schema if col[5] == 1), None)  # Primärschlüssel
    
    # Wenn kein Primärschlüssel gefunden wurde, ersten Spaltennamen verwenden
    if not primary_key and columns:
        primary_key = columns[0]
    
    if request.method == "POST":
        # Daten aus dem Formular extrahieren
        data = {}
        for col in columns:
            if col != primary_key or primary_key not in request.form:  # Primärschlüssel nicht aktualisieren, wenn nicht im Formular
                data[col] = request.form.get(col, "")
                
                # Leere Strings in NULL umwandeln, wenn der Wert leer ist
                if data[col] == "":
                    data[col] = None
        
        # Aktualisierungsabfrage erstellen
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = ?"
        params = list(data.values()) + [row_id]
        
        # Abfrage ausführen
        result = execute_query(conn, query, params)
        
        if isinstance(result, dict) and "error" in result:
            flash(f"Fehler beim Aktualisieren des Datensatzes: {result['error']}", "error")
        else:
            flash("Datensatz erfolgreich aktualisiert", "success")
            return redirect(url_for("view_table", table_name=table_name, db=db))
    
    # Datensatz abrufen
    query = f"SELECT * FROM {table_name} WHERE {primary_key} = ?"
    rows = execute_query(conn, query, [row_id])
    
    if not rows:
        conn.close()
        return render_template(
            "db_edit_row.html",
            table_name=table_name,
            row={},
            columns=[],
            db=db,
            db_error=f"Der Datensatz mit {primary_key}={row_id} wurde nicht gefunden."
        )
    
    row = rows[0]
    conn.close()
    
    return render_template(
        "db_edit_row.html",
        table_name=table_name,
        row=row,
        columns=columns,
        column_types=column_types,
        primary_key=primary_key,
        primary_key_value=row_id,
        db=db
    )

@app.route("/new/<table_name>", methods=["GET", "POST"])
def new_row(table_name):
    """Erstellt einen neuen Datensatz"""
    db = request.args.get("db") or DB_PATH
    
    conn = get_db_connection(db)
    if conn is None:
        return render_template(
            "db_edit_new.html",
            table_name=table_name,
            columns=[],
            db=db,
            db_error=f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        )
    
    # Schema der Tabelle abrufen
    schema = get_table_schema(conn, table_name)
    if not schema:
        conn.close()
        return render_template(
            "db_edit_new.html",
            table_name=table_name,
            columns=[],
            db=db,
            db_error=f"Die Tabelle '{table_name}' wurde nicht gefunden."
        )
    
    columns = [col[1] for col in schema]  # Spaltennamen
    column_types = {col[1]: col[2] for col in schema}  # Spaltentypen
    primary_key = next((col[1] for col in schema if col[5] == 1), None)  # Primärschlüssel
    auto_increment = primary_key and "INTEGER" in column_types.get(primary_key, "").upper()  # Prüfen, ob Primärschlüssel auto-increment ist
    
    if request.method == "POST":
        # Daten aus dem Formular extrahieren
        data = {}
        for col in columns:
            # Auto-increment Primärschlüssel überspringen
            if col == primary_key and auto_increment:
                continue
                
            data[col] = request.form.get(col, "")
            
            # Leere Strings in NULL umwandeln, wenn der Wert leer ist
            if data[col] == "":
                data[col] = None
        
        # Einfügeabfrage erstellen
        columns_str = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data.values()])
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        params = list(data.values())
        
        # Abfrage ausführen
        result = execute_query(conn, query, params)
        
        if isinstance(result, dict) and "error" in result:
            flash(f"Fehler beim Erstellen des Datensatzes: {result['error']}", "error")
        else:
            flash("Datensatz erfolgreich erstellt", "success")
            return redirect(url_for("view_table", table_name=table_name, db=db))
    
    conn.close()
    
    return render_template(
        "db_edit_new.html",
        table_name=table_name,
        columns=columns,
        column_types=column_types,
        primary_key=primary_key,
        auto_increment=auto_increment,
        db=db
    )

@app.route("/delete/<table_name>/<row_id>", methods=["POST"])
def delete_row(table_name, row_id):
    """Löscht einen Datensatz"""
    db = request.args.get("db") or DB_PATH
    
    conn = get_db_connection(db)
    if conn is None:
        return jsonify({"success": False, "error": f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."})
    
    # Schema der Tabelle abrufen
    schema = get_table_schema(conn, table_name)
    if not schema:
        conn.close()
        return jsonify({"success": False, "error": f"Die Tabelle '{table_name}' wurde nicht gefunden."})
    
    primary_key = next((col[1] for col in schema if col[5] == 1), None)  # Primärschlüssel
    
    # Wenn kein Primärschlüssel gefunden wurde, ersten Spaltennamen verwenden
    if not primary_key and schema:
        primary_key = schema[0][1]
    
    # Löschabfrage erstellen
    query = f"DELETE FROM {table_name} WHERE {primary_key} = ?"
    params = [row_id]
    
    # Abfrage ausführen
    result = execute_query(conn, query, params)
    
    conn.close()
    
    if isinstance(result, dict) and "error" in result:
        return jsonify({"success": False, "error": result["error"]})
    else:
        return jsonify({"success": True})

@app.route("/query", methods=["GET", "POST"])
def custom_query():
    """Führt benutzerdefinierte SQL-Abfragen aus"""
    db = request.args.get("db") or DB_PATH
    query = request.form.get("query", "")
    result = None
    error = None
    
    if request.method == "POST" and query:
        conn = get_db_connection(db)
        if conn is None:
            error = f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        else:
            # Abfrage ausführen
            result = execute_query(conn, query)
            
            if isinstance(result, dict) and "error" in result:
                error = result["error"]
                result = None
            
            conn.close()
    
    return render_template(
        "db_edit_query.html",
        query=query,
        result=result,
        error=error,
        db=db
    )

@app.route("/structure/<table_name>", methods=["GET", "POST"])
def table_structure(table_name):
    """Zeigt die Struktur einer Tabelle an und ermöglicht Änderungen"""
    db = request.args.get("db") or DB_PATH
    
    conn = get_db_connection(db)
    if conn is None:
        return render_template(
            "db_edit_structure.html",
            table_name=table_name,
            schema=[],
            db=db,
            db_error=f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."
        )
    
    # Schema der Tabelle abrufen
    schema = get_table_schema(conn, table_name)
    if not schema:
        conn.close()
        return render_template(
            "db_edit_structure.html",
            table_name=table_name,
            schema=[],
            db=db,
            db_error=f"Die Tabelle '{table_name}' wurde nicht gefunden."
        )
    
    # Wenn POST-Request, Änderungen an der Tabellenstruktur vornehmen
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_column":
            column_name = request.form.get("column_name")
            column_type = request.form.get("column_type")
            
            if column_name and column_type:
                query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                result = execute_query(conn, query)
                
                if isinstance(result, dict) and "error" in result:
                    flash(f"Fehler beim Hinzufügen der Spalte: {result['error']}", "error")
                else:
                    flash(f"Spalte '{column_name}' erfolgreich hinzugefügt", "success")
                    # Schema aktualisieren
                    schema = get_table_schema(conn, table_name)
        
        elif action == "create_index":
            index_name = request.form.get("index_name")
            index_columns = request.form.get("index_columns")
            
            if index_name and index_columns:
                query = f"CREATE INDEX {index_name} ON {table_name}({index_columns})"
                result = execute_query(conn, query)
                
                if isinstance(result, dict) and "error" in result:
                    flash(f"Fehler beim Erstellen des Index: {result['error']}", "error")
                else:
                    flash(f"Index '{index_name}' erfolgreich erstellt", "success")
    
    # Indizes abrufen
    indices = []
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA index_list({table_name})")
        indices = cursor.fetchall()
    except sqlite3.Error:
        pass
    
    conn.close()
    
    return render_template(
        "db_edit_structure.html",
        table_name=table_name,
        schema=schema,
        indices=indices,
        db=db
    )

@app.route("/create_table", methods=["GET", "POST"])
def create_table():
    """Erstellt eine neue Tabelle"""
    db = request.args.get("db") or DB_PATH
    
    if request.method == "POST":
        table_name = request.form.get("table_name")
        columns_json = request.form.get("columns")
        
        if table_name and columns_json:
            try:
                columns = json.loads(columns_json)
                
                # SQL-Abfrage zum Erstellen der Tabelle generieren
                column_defs = []
                for col in columns:
                    column_def = f"{col['name']} {col['type']}"
                    
                    if col.get('primary_key'):
                        column_def += " PRIMARY KEY"
                        if col.get('autoincrement') and col['type'].upper() == "INTEGER":
                            column_def += " AUTOINCREMENT"
                    
                    if col.get('not_null'):
                        column_def += " NOT NULL"
                    
                    if col.get('default'):
                        column_def += f" DEFAULT {col['default']}"
                    
                    column_defs.append(column_def)
                
                query = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
                
                conn = get_db_connection(db)
                if conn is None:
                    return jsonify({"success": False, "error": f"Die Datenbank '{db}' wurde nicht gefunden oder konnte nicht geöffnet werden."})
                
                result = execute_query(conn, query)
                conn.close()
                
                if isinstance(result, dict) and "error" in result:
                    return jsonify({"success": False, "error": result["error"]})
                else:
                    return jsonify({"success": True})
            except json.JSONDecodeError:
                return jsonify({"success": False, "error": "Ungültiges JSON-Format für Spalten"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)})
    
    return render_template(
        "db_edit_create_table.html",
        db=db
    )

if __name__ == "__main__":
    # Templates-Ordner erstellen, falls nicht vorhanden
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    app.run(debug=True, host="0.0.0.0", port=3333)
