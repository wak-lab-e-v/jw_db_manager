"""
Implementierung des CheckSrc-Befehls für den Datenbankmanager.
Prüft, ob für Einträge mit leerem src_path ein Verzeichnis existiert, das den Feiertag im Namen enthält.
"""

import os

def execute_checksrc(db_manager, path_prefix):
    """
    Führt den CheckSrc-Befehl aus.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        path_prefix (str): Pfad-Präfix, in dem nach Verzeichnissen gesucht wird
        
    Returns:
        tuple: (Erfolg (bool), Nachricht (str))
    """
    check_source_directories(db_manager, path_prefix)
    return True, "Prüfung der Quellverzeichnisse abgeschlossen."

def check_source_directories(db_manager, path_prefix):
    """
    Prüft, ob für Einträge mit leerem src_path ein Verzeichnis existiert, das den Feiertag im Namen enthält.
    Wenn ja, wird src_path auf den vollständigen Pfad gesetzt.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        path_prefix (str): Pfad-Präfix, in dem nach Verzeichnissen gesucht wird
    """
    try:
        db_manager.connect()
        
        # Hole alle Einträge mit leerem src_path, einschließlich der Location-Spalte
        db_manager.cursor.execute("SELECT id, feiertag, name, vorname, location FROM anmeldungen WHERE src_path = '' OR src_path IS NULL")
        entries = db_manager.cursor.fetchall()
        
        if not entries:
            print("Keine Einträge mit leerem src_path gefunden.")
            return
        
        print(f"\nPrüfe {len(entries)} Einträge auf vorhandene Quellverzeichnisse...")
        
        # Zähler für gefundene und nicht gefundene Verzeichnisse
        found_count = 0
        not_found_count = 0
        
        # Iteriere über alle Einträge
        for entry_id, feiertag, name, vorname, location in entries:
            # Extrahiere nur das Datum aus dem Feiertag (falls es ein Datum mit Uhrzeit ist)
            if feiertag and ' ' in feiertag:
                feiertag = feiertag.split(' ')[0]
            
            # Konvertiere das Datum in ein Format, das wahrscheinlich im Verzeichnisnamen verwendet wird
            # z.B. von "24.05.2025" zu "2025-05-24" oder ähnlich
            if feiertag and '.' in feiertag:
                day, month, year = feiertag.split('.')
                
                # Behandle kurze und lange Jahresangaben
                short_year = year
                if len(year) == 4 and year.startswith('20'):
                    short_year = year[2:]  # z.B. 2025 -> 25
                elif len(year) == 2:
                    full_year = f"20{year}"  # z.B. 25 -> 2025
                    year = full_year
                
                date_formats = [
                    # Lange Jahresformate (YYYY)
                    f"{year}-{month}-{day}",  # YYYY-MM-DD
                    f"{day}.{month}.{year}",  # DD.MM.YYYY
                    f"{day}-{month}-{year}",  # DD-MM-YYYY
                    f"{year}{month}{day}",    # YYYYMMDD
                    
                    # Kurze Jahresformate (YY)
                    f"{short_year}-{month}-{day}",  # YY-MM-DD
                    f"{day}.{month}.{short_year}",  # DD.MM.YY
                    f"{day}-{month}-{short_year}",  # DD-MM-YY
                    f"{short_year}{month}{day}"     # YYMMDD
                ]
            else:
                # Wenn kein gültiges Datum vorhanden ist, verwende den Feiertag direkt
                date_formats = [feiertag] if feiertag else []
            
            # Extrahiere das letzte Wort aus der Location, falls vorhanden
            location_keyword = ""
            if location and isinstance(location, str) and location.strip():
                # Teile die Location an Leerzeichen und nimm das letzte Wort
                location_words = location.strip().split()
                if location_words:
                    location_keyword = location_words[-1].lower()
            
            # Suche nach Verzeichnissen, die sowohl das Datum als auch das letzte Wort der Location im Namen enthalten
            found_dir = None
            
            if date_formats:
                # Durchsuche das Verzeichnis nach Unterverzeichnissen
                try:
                    for root, dirs, _ in os.walk(path_prefix):
                        for dir_name in dirs:
                            dir_name_lower = dir_name.lower()
                            # Prüfe, ob eines der Datumsformate im Verzeichnisnamen enthalten ist
                            for date_format in date_formats:
                                # Wenn Location-Keyword vorhanden ist, prüfe ob sowohl Datum als auch Location im Namen enthalten sind
                                if date_format and date_format in dir_name:
                                    if not location_keyword or location_keyword in dir_name_lower:
                                        found_dir = os.path.join(root, dir_name)
                                        break
                            if found_dir:
                                break
                        if found_dir:
                            break
                except Exception as e:
                    print(f"Fehler beim Durchsuchen des Verzeichnisses: {e}")
            
            # Wenn ein Verzeichnis gefunden wurde, aktualisiere src_path
            if found_dir:
                db_manager.cursor.execute("UPDATE anmeldungen SET src_path = ? WHERE id = ?", (found_dir, entry_id))
                print(f"Gefunden: ID {entry_id}, {name} {vorname}, Feiertag: {feiertag}, Location: {location} -> {found_dir}")
                found_count += 1
            else:
                print(f"Nicht gefunden: ID {entry_id}, {name} {vorname}, Feiertag: {feiertag}, Location: {location}")
                not_found_count += 1
        
        # Commit die Änderungen
        db_manager.conn.commit()
        
        print(f"\nErgebnis der Prüfung:")
        print(f"  - {found_count} Quellverzeichnisse gefunden und aktualisiert")
        print(f"  - {not_found_count} Quellverzeichnisse nicht gefunden")
    
    except Exception as e:
        print(f"Fehler bei der Prüfung der Quellverzeichnisse: {e}")
        if db_manager.conn:
            db_manager.conn.rollback()
    finally:
        db_manager.close()
