"""
Datenbankmanager für die Anmeldungsdaten.
Erstellt die Datenbank basierend auf dem Schema und bietet Funktionen zum Importieren
der Daten aus der Excel-Datei.

Verwendung:
    python db_manager.py --excel-file Anmeldung_Export.xlsx --db-file anmeldungen.db
"""

import os
import sys
import sqlite3
import pandas as pd
import argparse
import zlib  # Für CRC32
import warnings
from excel_config import EXCEL_HEADER_MAPPING, update_indices

# Unterdrücke die Warnung über bedingte Formatierung von openpyxl
warnings.filterwarnings('ignore', category=UserWarning, message='Conditional Formatting extension is not supported and will be removed')

def read_excel_data(file_path):
    """
    Liest die Excel-Datei und extrahiert die benötigten Spalten.
    
    Args:
        file_path (str): Pfad zur Excel-Datei
        
    Returns:
        pandas.DataFrame: DataFrame mit den extrahierten Daten
    """
    # Excel-Datei ohne Header einlesen und Datumskonvertierung deaktivieren
    df = pd.read_excel(file_path, header=None, parse_dates=False)
    
    # Überprüfe, ob die Datei Daten enthält
    if df.empty:
        print("Die Excel-Datei enthält keine Daten.")
        return None
    
    # Aktualisiere die Spaltenindizes basierend auf der tatsächlichen Datei
    updated_mapping = update_indices(df)
            
    # Prüfe, ob alle benötigten Spalten gefunden wurden
    required_columns = ["BESTELLNUMMER", "NAME", "VORNAME"]
    missing_columns = [col for col in required_columns if col not in updated_mapping]
    if missing_columns:
        print(f"FEHLER: Folgende Pflichtfelder wurden in der Excel-Datei nicht gefunden: {', '.join(missing_columns)}")
        return None
    
    # Erstelle ein neues DataFrame mit nur den benötigten Spalten (ab Zeile 1, da Zeile 0 die Header sind)
    selected_columns = list(updated_mapping.values())
    extracted_df = df.iloc[1:, selected_columns].copy()
    
    # Setze die richtigen Spaltennamen
    column_names = {col_idx: var_name for var_name, col_idx in updated_mapping.items()}
    extracted_df.rename(columns=column_names, inplace=True)
    
    return extracted_df


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
        """Erstellt die Tabellen basierend auf dem Schema in db_schema.txt."""
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
    
    def import_excel_data(self, excel_path):
        """
        Importiert Daten aus der Excel-Datei in die Datenbank.
        
        Args:
            excel_path (str): Pfad zur Excel-Datei
        
        Returns:
            tuple: (Anzahl der neuen Einträge, Anzahl der aktualisierten Einträge)
        """
        try:
            # Lese die Excel-Daten
            df = read_excel_data(excel_path)
            if df is None or df.empty:
                print("Keine Daten zum Importieren gefunden.")
                return (0, 0)
            
            # Verbinde zur Datenbank
            self.connect()
            
            # Zähle die importierten Datensätze
            new_count = 0
            updated_count = 0
            
            # Iteriere über die Zeilen und füge sie in die Datenbank ein
            skipped_count = 0
            for idx, row in df.iterrows():
                # Excel-Zeilennummer (Header ist Zeile 0, Daten beginnen bei Zeile 1, daher +1 für die tatsächliche Excel-Zeile)
                excel_row = idx + 2  # +2 weil idx bei 0 beginnt und wir den Header haben
                
                # Extrahiere und validiere die Daten
                bestellnummer = str(row.get('BESTELLNUMMER', '')) if row.get('BESTELLNUMMER') is not None else ''
                # Entferne Leerzeichen links und rechts von Namen und Vornamen
                name = str(row.get('NAME', '')) if row.get('NAME') is not None else ''
                name = name.strip()  # Entferne Leerzeichen links und rechts
                vorname = str(row.get('VORNAME', '')) if row.get('VORNAME') is not None else ''
                vorname = vorname.strip()  # Entferne Leerzeichen links und rechts
                
                # Debug-Ausgabe für die Zeile
                #print(f"DEBUG Zeile {excel_row}: Name='{name}', Vorname='{vorname}', Bestellnummer='{bestellnummer}'")
                
                # Validiere die Pflichtfelder
                missing_fields = []
                if not name or name.lower() == 'nan' or name.strip() == '':
                    missing_fields.append('Name')
                if not vorname or vorname.lower() == 'nan' or vorname.strip() == '':
                    missing_fields.append('Vorname')
                if not bestellnummer or bestellnummer.lower() == 'nan' or bestellnummer.strip() == '':
                    missing_fields.append('Bestellnummer')
                
                # Wenn Pflichtfelder fehlen, überspringe diesen Eintrag
                if missing_fields:
                    error_message = f"FEHLER in Zeile {excel_row}: Fehlende Pflichtfelder: {', '.join(missing_fields)}"
                    if name and name.strip() and name.lower() != 'nan':
                        error_message += f" für {name}"
                    if vorname and vorname.strip() and vorname.lower() != 'nan':
                        error_message += f" {vorname}"
                    print(error_message)
                    skipped_count += 1
                    continue
                
                # Generiere die UID (CRC32-Hash aus Name, Vorname und Bestellnummer)
                uid_string = f"{name}{vorname}{bestellnummer}"
                # CRC32 gibt einen Integer zurück, konvertiere zu Hex-String ohne führende 0x
                crc32_value = zlib.crc32(uid_string.encode('utf-8')) & 0xFFFFFFFF  # Stelle sicher, dass es ein 32-bit unsigned int ist
                uid = format(crc32_value, '08x')  # 8-stelliger Hex-String
                
                # Prüfe, ob ein Eintrag mit dieser UID bereits existiert
                self.cursor.execute("SELECT id FROM anmeldungen WHERE uid = ?", (uid,))
                existing_entry = self.cursor.fetchone()
                
                # Bereite die Daten vor und konvertiere alle Werte in Strings
                
                # Verarbeite den Feiertag - behalte das ursprüngliche Format bei
                feiertag = str(row.get('FEIERTAG', '')) if row.get('FEIERTAG') is not None else ''
                # Entferne Uhrzeit, falls vorhanden, aber behalte das ursprüngliche Datumsformat bei
                if ' 00:00:00' in feiertag:
                    feiertag = feiertag.split(' ')[0]
                # Stelle sicher, dass das Datum im ursprünglichen Format bleibt (z.B. TT.MM.JJJJ statt JJJJ-MM-TT)
                # Wenn das Datum im Format JJJJ-MM-TT ist, konvertiere es zu TT.MM.JJJJ
                if feiertag and '-' in feiertag and len(feiertag.split('-')) == 3:
                    year, month, day = feiertag.split('-')
                    feiertag = f"{day}.{month}.{year}"
                
                # Verarbeite die Feieruhrzeit - entferne Sekunden und ersetze Doppelpunkte/Punkte durch Bindestriche
                feieruhrzeit = str(row.get('FEIERUHRZEIT', '')) if row.get('FEIERUHRZEIT') is not None else ''
                if feieruhrzeit:
                    # Normalisiere zuerst: Ersetze Punkte durch Doppelpunkte für einheitliche Verarbeitung
                    feieruhrzeit = feieruhrzeit.replace('.', ':')
                    
                    # Entferne Sekunden, falls vorhanden (Format kann HH:MM:SS oder HH:MM sein)
                    parts = feieruhrzeit.split(':')
                    if len(parts) >= 2:
                        # Behalte nur Stunden und Minuten
                        feieruhrzeit = f"{parts[0]}:{parts[1]}"
                    
                    # Ersetze Doppelpunkte durch Bindestriche
                    feieruhrzeit = feieruhrzeit.replace(':', '-')
                
                data = {
                    'bestellnummer': bestellnummer,
                    'name': name,
                    'vorname': vorname,
                    'uid': uid,
                    'feiertag': feiertag,
                    'feieruhrzeit': feieruhrzeit,
                    'hint': '',        # Kein Hinweis, da wir Zeilen mit fehlenden Pflichtfeldern überspringen
                    'src_path': '',    # Standardwert für Quellpfad
                    'work_path': '',    # Standardwert für Arbeitspfad
                    'status': 'neu'     # Status ist immer 'neu', da wir Zeilen mit Fehlern überspringen
                }
                
                if existing_entry:
                    # Eintrag existiert bereits, keine Schreibvorgänge durchführen
                    updated_count += 1
                else:
                    # Neuen Eintrag einfügen
                    sql = '''
                    INSERT INTO anmeldungen (
                        bestellnummer, name, vorname, uid, feiertag, feieruhrzeit, 
                        hint, src_path, work_path, status
                    ) VALUES (
                        :bestellnummer, :name, :vorname, :uid, :feiertag, :feieruhrzeit,
                        :hint, :src_path, :work_path, :status
                    )
                    '''
                    self.cursor.execute(sql, data)
                    new_count += 1
            
            # Commit die Änderungen
            self.conn.commit()
            total_count = new_count + updated_count
            print(f"Import abgeschlossen: {total_count} Datensätze verarbeitet")
            print(f"  - {new_count} neue Datensätze eingefügt")
            print(f"  - {updated_count} bestehende Datensätze übersprungen (keine Änderungen vorgenommen)")
            if skipped_count > 0:
                print(f"  - {skipped_count} Datensätze wegen fehlender Pflichtfelder übersprungen")
            return (new_count, updated_count, skipped_count)
            
        except Exception as e:
            print(f"Fehler beim Importieren der Daten: {e}")
            if self.conn:
                self.conn.rollback()
            return (0, 0, 0)
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
    import_parser.add_argument('--limit', '-l', type=int, default=5, help='Anzahl der anzuzeigenden Einträge nach dem Import')
    
    # Stats-Kommando
    stats_parser = subparsers.add_parser('stats', help='Zeigt Statistiken über die Daten in der Datenbank')
    stats_parser.add_argument('--db-file', '-d', required=True, help='Pfad zur SQLite-Datenbankdatei')
    stats_parser.add_argument('--detail', action='store_true', help='Zeigt detailliertere Statistiken')
    
    return parser.parse_args()


def show_statistics(db_path, detailed=False):
    """
    Zeigt Statistiken über die Daten in der Datenbank.
    
    Args:
        db_path (str): Pfad zur SQLite-Datenbankdatei
        detailed (bool): Wenn True, werden detailliertere Statistiken angezeigt
    """
    db_manager = DatabaseManager(db_path)
    
    try:
        db_manager.connect()
        
        # Gesamtanzahl der Einträge
        db_manager.cursor.execute("SELECT COUNT(*) FROM anmeldungen")
        total_count = db_manager.cursor.fetchone()[0]
        print(f"\nGesamtanzahl der Einträge: {total_count}")
        
        # Anzahl nach Status
        db_manager.cursor.execute("SELECT status, COUNT(*) FROM anmeldungen GROUP BY status")
        status_counts = db_manager.cursor.fetchall()
        print("\nAnzahl nach Status:")
        for status, count in status_counts:
            print(f"  {status}: {count}")
        
        # Anzahl der Einträge mit Hinweisen
        db_manager.cursor.execute("SELECT COUNT(*) FROM anmeldungen WHERE hint != ''")
        hint_count = db_manager.cursor.fetchone()[0]
        print(f"\nAnzahl der Einträge mit Hinweisen: {hint_count}")
        
        # Anzahl der Einträge nach Feiertag
        db_manager.cursor.execute("SELECT feiertag, COUNT(*) FROM anmeldungen GROUP BY feiertag ORDER BY COUNT(*) DESC")
        feiertag_counts = db_manager.cursor.fetchall()
        print("\nAnzahl nach Feiertag:")
        for feiertag, count in feiertag_counts:
            print(f"  {feiertag}: {count}")
        
        if detailed:
            # Detailliertere Statistiken
            print("\nDetaillierte Statistiken:")
            
            # Die 10 häufigsten Namen
            db_manager.cursor.execute("SELECT name, COUNT(*) FROM anmeldungen GROUP BY name ORDER BY COUNT(*) DESC LIMIT 10")
            name_counts = db_manager.cursor.fetchall()
            print("\nDie 10 häufigsten Namen:")
            for name, count in name_counts:
                print(f"  {name}: {count}")
    
    except Exception as e:
        print(f"Fehler beim Abrufen der Statistiken: {e}")
    finally:
        db_manager.close()


if __name__ == "__main__":
    # Parse die Kommandozeilenargumente
    args = parse_arguments()
    
    if not args.command:
        print("Fehler: Kein Kommando angegeben. Verwende 'python db_manager.py -h' für Hilfe.")
        sys.exit(1)
    
    if args.command == 'import':
        # Initialisiere den Datenbankmanager mit dem angegebenen Pfad
        db_manager = DatabaseManager(args.db_file)
        
        # Erstelle die Tabellen und prüfe, ob die Datenbank bereits existiert
        db_exists = db_manager.create_tables()
        
        # Importiere die Daten aus der Excel-Datei
        new_count, updated_count, skipped_count = db_manager.import_excel_data(args.excel_file)
        
        print(f"\nImport in {args.db_file} abgeschlossen.")
    
    elif args.command == 'stats':
        # Zeige Statistiken
        show_statistics(args.db_file, args.detail)
    
