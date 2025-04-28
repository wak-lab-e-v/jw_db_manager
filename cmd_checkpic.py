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
        
        # Hole alle Einträge mit nicht-leerem src_path, einschließlich der Location-Spalte
        db_manager.cursor.execute("SELECT id, name, vorname, src_path, feiertag, feieruhrzeit, bestellnummer, location FROM anmeldungen WHERE src_path != '' AND src_path IS NOT NULL")
        entries = db_manager.cursor.fetchall()
        
        if not entries:
            print("Keine Einträge mit src_path gefunden.")
            return
        
        print(f"\nPrüfe {len(entries)} Einträge auf vorhandene Bilder...")
        
        # Zähler für gefundene und nicht gefundene Bilder
        found_count = 0
        not_found_count = 0
        
        # Zähler für verschobene/kopierte und nicht verschobene/kopierte Bilder (für alle Einträge)
        processed_count = 0
        not_processed_count = 0
        
        # Bestimme die Operation (verschieben oder kopieren)
        is_move_operation = operation == 'move'
        
        # Bildendungen
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.jfif']
        
        # Iteriere über alle Einträge
        for entry_id, name, vorname, src_path, feiertag, feieruhrzeit, bestellnummer, location in entries:
            # Prüfe, ob das Verzeichnis existiert
            if not os.path.exists(src_path):
                print(f"Verzeichnis nicht gefunden: ID {entry_id}, {vorname} {name}, Pfad: {src_path}")
                not_found_count += 1
                continue
            
            # Suche nach Bildern im Verzeichnis
            found_images = []
            try:
                # Vorbereitung der Suchbegriffe
                # Teile den Vornamen in einzelne Vornamen auf (falls mehrere vorhanden sind)
                vornamen = [v.strip() for v in vorname.split() if v.strip()]
                
                # Erstelle alternative Schreibweisen für Umlaute
                name_variants = [name]
                vorname_variants = []
                
                # Für jeden Vornamen alternative Schreibweisen erstellen
                for v in vornamen:
                    variants = [v]
                    # Umlaute-Ersetzungen
                    if 'ä' in v.lower():
                        variants.append(v.lower().replace('ä', 'ae').title())
                    if 'ö' in v.lower():
                        variants.append(v.lower().replace('ö', 'oe').title())
                    if 'ü' in v.lower():
                        variants.append(v.lower().replace('ü', 'ue').title())
                    if 'ß' in v.lower():
                        variants.append(v.lower().replace('ß', 'ss').title())
                    vorname_variants.append(variants)
                
                # Auch für den Nachnamen alternative Schreibweisen erstellen
                # Von Umlaut zu Umschreibung
                if 'ä' in name.lower():
                    name_variants.append(name.lower().replace('ä', 'ae').title())
                if 'ö' in name.lower():
                    name_variants.append(name.lower().replace('ö', 'oe').title())
                if 'ü' in name.lower():
                    name_variants.append(name.lower().replace('ü', 'ue').title())
                if 'ß' in name.lower():
                    name_variants.append(name.lower().replace('ß', 'ss').title())
                
                # Von Umschreibung zu Umlaut (umgekehrte Richtung)
                if 'ae' in name.lower():
                    name_variants.append(name.lower().replace('ae', 'ä').title())
                if 'oe' in name.lower():
                    name_variants.append(name.lower().replace('oe', 'ö').title())
                if 'ue' in name.lower():
                    name_variants.append(name.lower().replace('ue', 'ü').title())
                if 'ss' in name.lower():
                    name_variants.append(name.lower().replace('ss', 'ß').title())
                    
                # Spezialfall: uess -> üß (wie in Schüßler -> Schuessler)
                if 'uess' in name.lower():
                    name_variants.append(name.lower().replace('uess', 'üß').title())
                
                # Spezialfall: üß -> uess (wie in Schüßler -> Schuessler)
                if 'üß' in name.lower():
                    name_variants.append(name.lower().replace('üß', 'uess').title())
                # Auch ü und ß einzeln berücksichtigen
                if 'ü' in name.lower() and 'ß' in name.lower():
                    temp = name.lower().replace('ü', 'ue')
                    name_variants.append(temp.replace('ß', 'ss').title())
                
                
                for root, _, files in os.walk(src_path):
                    for file in files:
                        file_lower = file.lower()
                        # Prüfe, ob es sich um ein Bild handelt
                        if any(file_lower.endswith(ext) for ext in image_extensions):
                            # Prüfe, ob der Dateiname mit einem der Vornamen beginnt und den Nachnamen enthält
                            match_found = False
                            
                            # Prüfe alle Vornamen-Varianten
                            for vorname_list in vorname_variants:
                                for v in vorname_list:
                                    # Prüfe alle Nachnamen-Varianten
                                    for n in name_variants:
                                        # Prüfe, ob der Dateiname mit dem Vornamen beginnt und den Nachnamen enthält
                                        if file_lower.startswith(v.lower()) and n.lower() in file_lower:
                                            # Debug-Ausgabe für Schüßler
                                            if 'schüßler' in n.lower() or 'schuessler' in n.lower() or 'schüßler' in file_lower or 'schuessler' in file_lower:
                                                print(f"DEBUG: Datei gefunden: {file_lower}")
                                                print(f"DEBUG: Vorname: {v.lower()}, Nachname: {n.lower()}")
                                            found_images.append(os.path.join(root, file))
                                            match_found = True
                                            break
                                    if match_found:
                                        break
                                if match_found:
                                    break
            except Exception as e:
                print(f"Fehler beim Durchsuchen des Verzeichnisses {src_path}: {e}")
                continue
            
            # Wenn Bilder gefunden wurden
            if found_images:
                print(f"Gefunden: ID {entry_id}, {vorname} {name}, {len(found_images)} Bilder")
                found_count += 1
                
                # Zähler für die Bilder dieses Eintrags zurücksetzen
                entry_processed_count = 0
                
                # Wenn target_path angegeben ist, verschiebe oder kopiere die Bilder
                if target_path:
                    # Erstelle die Verzeichnisstruktur
                    # Feiertag_Location/Feieruhrzeit/Vorname_Nachname_Bestellnummer
                    
                    # Bereinige die Location (falls vorhanden) für die Verwendung im Verzeichnisnamen
                    location_clean = location.replace('/', '-').replace('\\', '-') if location else ""
                    
                    # Erstelle den Feiertag-Verzeichnisnamen mit Location
                    if feiertag and location_clean:
                        feiertag_dir = f"{feiertag.replace('/', '-').replace('\\', '-')}_{location_clean}"
                    else:
                        feiertag_dir = feiertag.replace('/', '-').replace('\\', '-') if feiertag else "Unbekannt"
                    feieruhrzeit_dir = feieruhrzeit.replace('/', '-').replace('\\', '-') if feieruhrzeit else "Unbekannt"
                    person_dir = f"{vorname}_{name}_{bestellnummer}".replace('/', '-').replace('\\', '-')
                    
                    # Erstelle den vollständigen Zielpfad
                    target_dir = os.path.join(target_path, feiertag_dir, feieruhrzeit_dir, person_dir)
                    
                    # Stelle sicher, dass das Zielverzeichnis existiert
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Erstelle den relativen Pfad für work_path (relativ zum move_path)
                    rel_path = os.path.join(feiertag_dir, feieruhrzeit_dir, person_dir)
                    
                    # Erstelle den vollständigen Pfad für work_path
                    full_path = os.path.abspath(target_dir)
                    
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
                            entry_processed_count += 1
                            
                            # Setze das work_path in der Datenbank, wenn es das erste Bild dieses Eintrags ist
                            if entry_processed_count == 1:
                                try:
                                    db_manager.cursor.execute("UPDATE anmeldungen SET work_path = ? WHERE id = ?", (full_path, entry_id))
                                    db_manager.conn.commit()
                                    print(f"  Work_path in Datenbank aktualisiert: {full_path}")
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
