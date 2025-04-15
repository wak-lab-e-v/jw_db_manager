"""
Implementierung des CheckPic-Befehls für den Datenbankmanager.
Sucht nach Bildern im src_path, die den Vor- und Nachnamen enthalten,
wobei der Vorname am Anfang stehen muss.
"""

import os

def execute_checkpic(db_manager):
    """
    Führt den CheckPic-Befehl aus.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        
    Returns:
        tuple: (Erfolg (bool), Nachricht (str))
    """
    check_pictures(db_manager)
    return True, "Prüfung der Bilder abgeschlossen."

def check_pictures(db_manager):
    """
    Sucht nach Bildern im src_path, die den Vor- und Nachnamen enthalten,
    wobei der Vorname am Anfang stehen muss.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
    """
    try:
        db_manager.connect()
        
        # Hole alle Einträge mit nicht-leerem src_path
        db_manager.cursor.execute("SELECT id, name, vorname, src_path FROM anmeldungen WHERE src_path != '' AND src_path IS NOT NULL")
        entries = db_manager.cursor.fetchall()
        
        if not entries:
            print("Keine Einträge mit src_path gefunden.")
            return
        
        print(f"\nPrüfe {len(entries)} Einträge auf vorhandene Bilder...")
        
        # Zähler für gefundene und nicht gefundene Bilder
        found_count = 0
        not_found_count = 0
        
        # Bildendungen
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff']
        
        # Iteriere über alle Einträge
        for entry_id, name, vorname, src_path in entries:
            # Prüfe, ob das Verzeichnis existiert
            if not os.path.exists(src_path):
                print(f"Verzeichnis nicht gefunden: ID {entry_id}, {vorname} {name}, Pfad: {src_path}")
                not_found_count += 1
                continue
            
            # Suche nach Bildern im Verzeichnis
            found_images = []
            try:
                for root, _, files in os.walk(src_path):
                    for file in files:
                        # Prüfe, ob es sich um ein Bild handelt
                        if any(file.lower().endswith(ext) for ext in image_extensions):
                            # Ignoriere Dateien, die "nachgefordert" im Namen enthalten
                            if "nachgefordert" in file.lower():
                                continue
                                
                            # Prüfe, ob der Dateiname mit dem Vornamen beginnt und den Nachnamen enthält
                            if file.lower().startswith(vorname.lower()) and name.lower() in file.lower():
                                found_images.append(os.path.join(root, file))
            except Exception as e:
                print(f"Fehler beim Durchsuchen des Verzeichnisses {src_path}: {e}")
                continue
            
            # Wenn Bilder gefunden wurden
            if found_images:
                print(f"Gefunden: ID {entry_id}, {vorname} {name}, {len(found_images)} Bilder")
                found_count += 1
            else:
                print(f"Keine Bilder gefunden: ID {entry_id}, {vorname} {name}")
                not_found_count += 1
        
        print(f"\nErgebnis der Prüfung:")
        print(f"  - {found_count} Einträge mit passenden Bildern gefunden")
        print(f"  - {not_found_count} Einträge ohne passende Bilder")
    
    except Exception as e:
        print(f"Fehler bei der Prüfung der Bilder: {e}")
        if db_manager.conn:
            db_manager.conn.rollback()
    finally:
        db_manager.close()
