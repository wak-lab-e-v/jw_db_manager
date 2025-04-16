"""
Implementierung des CheckPic-Befehls für den Datenbankmanager.
Sucht nach Bildern im src_path, die den Vor- und Nachnamen enthalten,
wobei der Vorname am Anfang stehen muss.
"""

import os
import shutil

def execute_checkpic(db_manager, target_path=None, operation=None):
    """
    Führt den CheckPic-Befehl aus.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        target_path (str, optional): Wenn angegeben, werden gefundene Bilder in diesen Pfad verschoben oder kopiert
        operation (str, optional): 'move' zum Verschieben, 'copy' zum Kopieren der Bilder
        
    Returns:
        tuple: (Erfolg (bool), Nachricht (str))
    """
    check_pictures(db_manager, target_path, operation)
    return True, "Prüfung der Bilder abgeschlossen."

def check_pictures(db_manager, target_path=None, operation=None):
    """
    Sucht nach Bildern im src_path, die den Vor- und Nachnamen enthalten,
    wobei der Vorname am Anfang stehen muss.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        target_path (str, optional): Wenn angegeben, werden gefundene Bilder in diesen Pfad verschoben oder kopiert
        operation (str, optional): 'move' zum Verschieben, 'copy' zum Kopieren der Bilder
    """
    try:
        db_manager.connect()
        
        # Hole alle Einträge mit nicht-leerem src_path
        db_manager.cursor.execute("SELECT id, name, vorname, src_path, feiertag, feieruhrzeit, bestellnummer FROM anmeldungen WHERE src_path != '' AND src_path IS NOT NULL")
        entries = db_manager.cursor.fetchall()
        
        if not entries:
            print("Keine Einträge mit src_path gefunden.")
            return
        
        print(f"\nPrüfe {len(entries)} Einträge auf vorhandene Bilder...")
        
        # Zähler für gefundene und nicht gefundene Bilder
        found_count = 0
        not_found_count = 0
        
        # Zähler für verschobene/kopierte und nicht verschobene/kopierte Bilder
        processed_count = 0
        not_processed_count = 0
        
        # Bestimme die Operation (verschieben oder kopieren)
        is_move_operation = operation == 'move'
        
        # Bildendungen
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff']
        
        # Iteriere über alle Einträge
        for entry_id, name, vorname, src_path, feiertag, feieruhrzeit, bestellnummer in entries:
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
                
                # Wenn target_path angegeben ist, verschiebe oder kopiere die Bilder
                if target_path:
                    # Erstelle die Verzeichnisstruktur
                    # Feiertag/Feieruhrzeit/Vorname_Nachname_Bestellnummer
                    feiertag_dir = feiertag.replace('/', '-').replace('\\', '-') if feiertag else "Unbekannt"
                    feieruhrzeit_dir = feieruhrzeit.replace('/', '-').replace('\\', '-') if feieruhrzeit else "Unbekannt"
                    person_dir = f"{vorname}_{name}_{bestellnummer}".replace('/', '-').replace('\\', '-')
                    
                    # Erstelle den vollständigen Zielpfad
                    target_dir = os.path.join(target_path, feiertag_dir, feieruhrzeit_dir, person_dir)
                    
                    # Stelle sicher, dass das Zielverzeichnis existiert
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Erstelle den relativen Pfad für work_path (relativ zum move_path)
                    rel_path = os.path.join(feiertag_dir, feieruhrzeit_dir, person_dir)
                    
                    # Verschiebe die Bilder
                    for image_path in found_images:
                        try:
                            # Extrahiere den Dateinamen aus dem Pfad
                            image_name = os.path.basename(image_path)
                            # Erstelle den Zielpfad für das Bild
                            dest_path = os.path.join(target_dir, image_name)
                            
                            # Verschiebe oder kopiere das Bild
                            if is_move_operation:
                                shutil.move(image_path, dest_path)  # Verschiebe das Bild (Original wird entfernt)
                                print(f"  Bild verschoben: {image_name} -> {target_dir}")
                            else:
                                shutil.copy2(image_path, dest_path)  # Kopiere das Bild (Original bleibt erhalten)
                                print(f"  Bild kopiert: {image_name} -> {target_dir}")
                            processed_count += 1
                            
                            # Setze das work_path in der Datenbank, wenn es das erste Bild ist
                            if processed_count == 1:
                                try:
                                    db_manager.cursor.execute("UPDATE anmeldungen SET work_path = ? WHERE id = ?", (rel_path, entry_id))
                                    db_manager.conn.commit()
                                    print(f"  Work_path in Datenbank aktualisiert: {rel_path}")
                                except Exception as e:
                                    print(f"  Fehler beim Aktualisieren des work_path in der Datenbank: {e}")
                        except Exception as e:
                            print(f"  Fehler beim Kopieren von {image_path}: {e}")
                            not_processed_count += 1
            else:
                print(f"Keine Bilder gefunden: ID {entry_id}, {vorname} {name}")
                not_found_count += 1
        
        print(f"\nErgebnis der Prüfung:")
        print(f"  - {found_count} Einträge mit passenden Bildern gefunden")
        print(f"  - {not_found_count} Einträge ohne passende Bilder")
        
        # Wenn target_path angegeben ist, zeige auch die Statistik zum Verschieben/Kopieren an
        if target_path:
            operation_text = "Verschiebens" if is_move_operation else "Kopierens"
            success_text = "verschoben" if is_move_operation else "kopiert"
            print(f"\nErgebnis des {operation_text}:")
            print(f"  - {processed_count} Bilder erfolgreich {success_text}")
            print(f"  - {not_processed_count} Bilder konnten nicht {success_text} werden")
    
    except Exception as e:
        print(f"Fehler bei der Prüfung der Bilder: {e}")
        if db_manager.conn:
            db_manager.conn.rollback()
    finally:
        db_manager.close()
