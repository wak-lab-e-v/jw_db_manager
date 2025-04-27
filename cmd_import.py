"""
Implementierung des Import-Befehls für den Datenbankmanager.
Importiert Daten aus einer Excel-Datei in die SQLite-Datenbank.
"""

import os
import pandas as pd
import zlib
from excel_config import update_indices

def read_excel_data(file_path):
    """
    Liest die Excel-Datei und extrahiert die benötigten Spalten.
    
    Args:
        file_path (str): Pfad zur Excel-Datei
        
    Returns:
        pandas.DataFrame: DataFrame mit den extrahierten Daten
    """
    # Excel-Datei ohne Header einlesen und Datumskonvertierung deaktivieren
    df = pd.read_excel(file_path, header=None, parse_dates=False, sheet_name=1)
    
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

def execute_import(db_manager, excel_file):
    """
    Führt den Import-Befehl aus.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        excel_file (str): Pfad zur Excel-Datei
        
    Returns:
        tuple: (Erfolg (bool), Nachricht (str))
    """
    # Erstelle die Tabellen und prüfe, ob die Datenbank bereits existiert
    db_exists = db_manager.create_tables()
    
    # Importiere die Daten aus der Excel-Datei
    new_count, updated_count, skipped_count = import_excel_data(db_manager, excel_file)
    
    return True, f"Import abgeschlossen: {new_count + updated_count} Datensätze verarbeitet\n  - {new_count} neue Datensätze eingefügt\n  - {updated_count} bestehende Datensätze übersprungen (keine Änderungen vorgenommen)\n  - {skipped_count} Datensätze wegen fehlender Pflichtfelder übersprungen"

def import_excel_data(db_manager, excel_path):
    """
    Importiert Daten aus der Excel-Datei in die Datenbank.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        excel_path (str): Pfad zur Excel-Datei
    
    Returns:
        tuple: (Anzahl der neuen Einträge, Anzahl der aktualisierten Einträge, Anzahl der übersprungenen Einträge)
    """
    try:
        # Lese die Excel-Daten
        df = read_excel_data(excel_path)
        if df is None or df.empty:
            print("Keine Daten zum Importieren gefunden.")
            return (0, 0, 0)
        
        # Verbinde zur Datenbank
        db_manager.connect()
        
        # Zähle die importierten Datensätze
        new_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Iteriere über die Zeilen und füge sie in die Datenbank ein
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
            db_manager.cursor.execute("SELECT id FROM anmeldungen WHERE uid = ?", (uid,))
            existing_entry = db_manager.cursor.fetchone()
            
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
                # Eintrag existiert bereits, prüfe ob feiertag oder feieruhrzeit geändert wurden
                db_manager.cursor.execute("SELECT feiertag, feieruhrzeit FROM anmeldungen WHERE uid = ?", (uid,))
                db_entry = db_manager.cursor.fetchone()
                
                if db_entry and (db_entry[0] != feiertag or db_entry[1] != feieruhrzeit):
                    # Feierzeit oder Feiertag haben sich geändert
                    warning_message = f"WARNUNG: Für {name} {vorname} (Bestellnr. {bestellnummer}) hat sich die Feierzeit im XLS geändert!"
                    print(warning_message)
                    
                    # Update den Hint in der Datenbank
                    hint_message = "Achtung, Feierzeit im XLS verändert!"
                    db_manager.cursor.execute("UPDATE anmeldungen SET hint = ? WHERE uid = ?", (hint_message, uid))
                    
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
                db_manager.cursor.execute(sql, data)
                new_count += 1
        
        # Commit die Änderungen
        db_manager.conn.commit()
        
        print(f"Import abgeschlossen: {new_count + updated_count} Datensätze verarbeitet")
        print(f"  - {new_count} neue Datensätze eingefügt")
        print(f"  - {updated_count} bestehende Datensätze übersprungen (keine Änderungen vorgenommen)")
        if skipped_count > 0:
            print(f"  - {skipped_count} Datensätze wegen fehlender Pflichtfelder übersprungen")
        
        return (new_count, updated_count, skipped_count)
        
    except Exception as e:
        print(f"Fehler beim Importieren der Daten: {e}")
        if db_manager.conn:
            db_manager.conn.rollback()
        return (0, 0, 0)
    finally:
        db_manager.close()
