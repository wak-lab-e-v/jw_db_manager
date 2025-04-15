"""
Datenbankmanager für die Anmeldungsdaten.
Hauptdatei, die die Datenbankverbindung verwaltet und die Befehle koordiniert.
"""

import os
import sys
import sqlite3
import argparse
import warnings

# Unterdrücke die Warnung über bedingte Formatierung von openpyxl
warnings.filterwarnings('ignore', category=UserWarning, message='Conditional Formatting extension is not supported and will be removed')

# Importiere die Befehlsmodule
from cmd_import import execute_import
from cmd_stats import execute_stats
from cmd_checksrc import execute_checksrc

class DatabaseManager:
    def __init__(self, db_path):
        """
        Initialisiert den Datenbankmanager.
        
        Args:
            db_path (str): Pfad zur SQLite-Datenbankdatei
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Stellt eine Verbindung zur Datenbank her."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Ermöglicht Zugriff auf Spalten über Namen
        self.cursor = self.conn.cursor()
        return self.conn
    
    def close(self):
        """Schließt die Datenbankverbindung."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def create_tables(self):
        """
        Erstellt die Tabellen basierend auf dem Schema in db_schema.txt.
        
        Returns:
            bool: True, wenn die Datenbank bereits existiert, False sonst
        """
        try:
            self.connect()
            
            # Prüfe, ob die Tabelle bereits existiert
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='anmeldungen'")
            table_exists = self.cursor.fetchone() is not None
            
            if table_exists:
                print("Datenbank existiert bereits. Tabellen werden nicht neu erstellt.")
                return True
            
            # Lese das Schema aus der Datei
            with open('db_schema.txt', 'r') as f:
                schema_sql = f.read()
            
            # Führe das Schema-SQL aus
            self.conn.executescript(schema_sql)
            self.conn.commit()
            print("Datenbanktabellen wurden neu erstellt.")
            return False
            
        except Exception as e:
            print(f"Fehler beim Erstellen der Tabellen: {e}")
            return False
        finally:
            self.close()
    
    def get_all_entries(self, limit=100):
        """
        Gibt alle Einträge aus der Datenbank zurück.
        
        Args:
            limit (int): Maximale Anzahl der zurückzugebenden Einträge
        
        Returns:
            list: Liste der Einträge als Dictionaries
        """
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM anmeldungen LIMIT ?", (limit,))
            rows = self.cursor.fetchall()
            
            # Konvertiere die Zeilen in Dictionaries
            result = []
            for row in rows:
                result.append(dict(row))
            
            return result
        except Exception as e:
            print(f"Fehler beim Abrufen der Einträge: {e}")
            return []
        finally:
            self.close()
    
    def search_entries(self, search_term, field=None, limit=100):
        """
        Sucht nach Einträgen in der Datenbank.
        
        Args:
            search_term (str): Suchbegriff
            field (str, optional): Feldname, in dem gesucht werden soll. Wenn None, wird in allen Textfeldern gesucht.
            limit (int): Maximale Anzahl der zurückzugebenden Einträge
        
        Returns:
            list: Liste der gefundenen Einträge als Dictionaries
        """
        try:
            self.connect()
            
            if field:
                # Suche in einem bestimmten Feld
                sql = f"SELECT * FROM anmeldungen WHERE {field} LIKE ? LIMIT ?"
                self.cursor.execute(sql, (f"%{search_term}%", limit))
            else:
                # Suche in allen Textfeldern
                sql = """
                SELECT * FROM anmeldungen 
                WHERE bestellnummer LIKE ? 
                OR name LIKE ? 
                OR vorname LIKE ? 
                OR feiertag LIKE ? 
                OR feieruhrzeit LIKE ? 
                OR hint LIKE ? 
                OR src_path LIKE ? 
                OR work_path LIKE ? 
                OR status LIKE ? 
                LIMIT ?
                """
                params = [f"%{search_term}%"] * 9 + [limit]
                self.cursor.execute(sql, params)
            
            rows = self.cursor.fetchall()
            
            # Konvertiere die Zeilen in Dictionaries
            result = []
            for row in rows:
                result.append(dict(row))
            
            return result
        except Exception as e:
            print(f"Fehler bei der Suche: {e}")
            return []
        finally:
            self.close()
    
    def update_entry(self, entry_id, data):
        """
        Aktualisiert einen Eintrag in der Datenbank.
        
        Args:
            entry_id (int): ID des zu aktualisierenden Eintrags
            data (dict): Zu aktualisierende Daten
        
        Returns:
            bool: True, wenn erfolgreich, sonst False
        """
        try:
            self.connect()
            
            # Erstelle die SET-Klausel für das UPDATE-Statement
            set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
            values = list(data.values()) + [entry_id]
            
            # Führe das UPDATE aus
            sql = f"UPDATE anmeldungen SET {set_clause} WHERE id = ?"
            self.cursor.execute(sql, values)
            self.conn.commit()
            
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Fehler beim Aktualisieren des Eintrags: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            self.close()


def parse_arguments():
    """
    Parst die Kommandozeilenargumente.
    
    Returns:
        argparse.Namespace: Die geparsten Argumente
    """
    parser = argparse.ArgumentParser(description='Verwaltung der Anmeldungsdatenbank')
    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Kommandos')
    
    # Import-Kommando
    import_parser = subparsers.add_parser('import', help='Importiert Daten aus einer Excel-Datei in die Datenbank')
    import_parser.add_argument('--excel-file', '-e', required=True, help='Pfad zur Excel-Datei')
    import_parser.add_argument('--db-file', '-d', required=True, help='Pfad zur SQLite-Datenbankdatei')
    
    # Stats-Kommando
    stats_parser = subparsers.add_parser('stats', help='Zeigt Statistiken über die Daten in der Datenbank')
    stats_parser.add_argument('--db-file', '-d', required=True, help='Pfad zur SQLite-Datenbankdatei')
    stats_parser.add_argument('--detail', action='store_true', help='Zeigt detailliertere Statistiken')
    
    # CheckSrc-Kommando
    checksrc_parser = subparsers.add_parser('checksrc', help='Prüft, ob Quellverzeichnisse existieren und aktualisiert src_path')
    checksrc_parser.add_argument('--db-file', '-d', required=True, help='Pfad zur SQLite-Datenbankdatei')
    checksrc_parser.add_argument('--path-prefix', '-p', required=True, help='Pfad-Präfix, in dem nach Verzeichnissen gesucht wird')
    
    return parser.parse_args()


if __name__ == "__main__":
    # Parse die Kommandozeilenargumente
    args = parse_arguments()
    
    if not args.command:
        print("Fehler: Kein Kommando angegeben. Verwende 'python db_manager.py -h' für Hilfe.")
        sys.exit(1)
    
    # Initialisiere den Datenbankmanager
    db_manager = DatabaseManager(args.db_file)
    
    # Führe das entsprechende Kommando aus
    if args.command == 'import':
        success, message = execute_import(db_manager, args.excel_file)
        print(f"\nImport in {args.db_file} abgeschlossen.")
    
    elif args.command == 'stats':
        success, message = execute_stats(db_manager, args.detail)
    
    elif args.command == 'checksrc':
        success, message = execute_checksrc(db_manager, args.path_prefix)
