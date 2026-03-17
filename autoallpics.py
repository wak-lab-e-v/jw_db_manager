#!/usr/bin/env python3
"""
autoallpics.py - Skript zur Überprüfung und automatischen Konvertierung von Bildern

Prüft in der Datenbank, ob:
1. Der work_path gesetzt ist
2. In diesem Pfad 3 Bilder liegen, die auf _1, _2 und _3 enden
3. Die Spalten final_picture_1, final_picture_2, final_picture_3 leer sind

Wenn alle Bedingungen erfüllt sind:
- Konvertiert die Bilder mit dbv_autoimgcov.py (fügt Namen hinzu)
- Speichert als _1_auto.jpg, _2_auto.jpg, _3_auto.jpg
- Aktualisiert die Datenbank mit den final_picture Pfaden
"""

import os
import sqlite3
import sys
from pathlib import Path

# Importiere die Konvertierungsfunktion
from dbv_autoimgcov import execute_autoconvert

# Datenbankpfad (relativ zum Skript-Verzeichnis)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anmeldungen.db")


def get_entries_with_work_path():
    """
    Holt alle Einträge aus der Datenbank, die einen work_path haben
    und bei denen die final_picture-Spalten leer sind.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, work_path, final_picture_1, final_picture_2, final_picture_3, vorname, name
        FROM anmeldungen
        WHERE work_path IS NOT NULL
          AND work_path != ''
          AND (final_picture_1 IS NULL OR final_picture_1 = '')
          AND (final_picture_2 IS NULL OR final_picture_2 = '')
          AND (final_picture_3 IS NULL OR final_picture_3 = '')
    """)
    
    entries = cursor.fetchall()
    conn.close()
    
    return entries


def get_image_files_in_path(work_path):
    """
    Findet die Bilder _1, _2, _3 im angegebenen Pfad.
    
    Args:
        work_path: Der zu prüfende Pfad
        
    Returns:
        tuple: (pfad_zu_bild_1, pfad_zu_bild_2, pfad_zu_bild_3) oder (None, None, None)
    """
    # Unterstützte Bildformate
    image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif'}
    
    # Prüfe, ob der Pfad existiert
    if not os.path.isdir(work_path):
        return None, None, None
    
    # Suche nach Bildern mit den Endungen _1, _2, _3
    img_1 = None
    img_2 = None
    img_3 = None
    
    try:
        for file in os.listdir(work_path):
            file_lower = file.lower()
            file_path = os.path.join(work_path, file)
            
            # Nur Dateien (keine Verzeichnisse)
            if not os.path.isfile(file_path):
                continue
            
            # Prüfe, ob es ein Bild ist
            ext = os.path.splitext(file_lower)[1]
            if ext not in image_extensions:
                continue
            
            # Prüfe auf _1, _2, _3 vor der Dateiendung
            name_without_ext = os.path.splitext(file_lower)[0]
            if name_without_ext.endswith('_1'):
                img_1 = file_path
            elif name_without_ext.endswith('_2'):
                img_2 = file_path
            elif name_without_ext.endswith('_3'):
                img_3 = file_path
    except Exception as e:
        print(f"Fehler beim Durchsuchen von {work_path}: {e}", file=sys.stderr)
        return None, None, None
    
    if img_1 and img_2 and img_3:
        return img_1, img_2, img_3
    return None, None, None


def check_images_in_path(work_path):
    """
    Prüft, ob im angegebenen Pfad 3 Bilder liegen, die auf _1, _2 und _3 enden.
    
    Args:
        work_path: Der zu prüfende Pfad
        
    Returns:
        bool: True wenn alle 3 Bilder (_1, _2, _3) gefunden wurden
    """
    img_1, img_2, img_3 = get_image_files_in_path(work_path)
    return img_1 is not None and img_2 is not None and img_3 is not None


def update_database_final_pictures(entry_id, final_paths):
    """
    Aktualisiert die final_picture Spalten in der Datenbank.
    
    Args:
        entry_id: ID des Eintrags
        final_paths: Liste mit 3 Pfaden für final_picture_1, _2, _3
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE anmeldungen
        SET final_picture_1 = ?,
            final_picture_2 = ?,
            final_picture_3 = ?
        WHERE id = ?
    """, (final_paths[0], final_paths[1], final_paths[2], entry_id))
    
    conn.commit()
    conn.close()
    print(f"  Datenbank aktualisiert für ID {entry_id}")


def main():
    """Hauptfunktion des Skripts."""
    # Prüfe, ob die Datenbank existiert
    if not os.path.exists(DB_PATH):
        print(f"Fehler: Datenbank nicht gefunden: {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    
    # Hole Einträge mit work_path und leeren final_picture-Spalten
    entries = get_entries_with_work_path()
    
    if not entries:
        print("Keine Einträge mit work_path und leeren final_picture-Spalten gefunden.")
        return
    
    # Basis-Verzeichnis für work_path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    processed_count = 0
    
    for entry in entries:
        entry_id, work_path, fp1, fp2, fp3, vorname, name = entry
        
        # Konvertiere relativen Pfad zu absolutem Pfad falls nötig
        if not os.path.isabs(work_path):
            full_path = os.path.join(base_dir, work_path)
        else:
            full_path = work_path
        
        # Normalisiere den Pfad
        full_path = os.path.normpath(full_path)
        
        # Prüfe, ob alle 3 Bilder vorhanden sind
        img_1, img_2, img_3 = get_image_files_in_path(full_path)
        if not img_1:
            continue
        
        print(f"\nVerarbeite ID {entry_id}: {vorname} {name}")
        print(f"  Pfad: {full_path}")
        
        # Konvertiere die Bilder
        final_paths = []
        person_name = f"{vorname} {name}" if vorname and name else (vorname or name or "Unbekannt")
        
        for i, img_path in enumerate([img_1, img_2, img_3], 1):
            # Erstelle Zieldateiname mit _auto Suffix
            dir_name = os.path.dirname(img_path)
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            ext = os.path.splitext(img_path)[1]
            # Ersetze Endung _1, _2, _3 durch _auto
            dest_base = base_name[:-2] + "auto"  # Entfernt _1/_2/_3 und fügt _auto hinzu
            dest_path = os.path.join(dir_name, dest_base + ".jpg")  # Immer als JPG speichern
            
            print(f"  Konvertiere Bild {i}: {os.path.basename(img_path)} -> {os.path.basename(dest_path)}")
            
            # Konvertiere das Bild
            success, message = execute_autoconvert(img_path, dest_path, person_name)
            
            if success:
                final_paths.append(dest_path)
                print(f"    ✓ Erfolgreich konvertiert")
            else:
                print(f"    ✗ Fehler: {message}")
                final_paths.append(None)
        
        # Aktualisiere die Datenbank, wenn alle 3 Bilder konvertiert wurden
        if all(final_paths):
            update_database_final_pictures(entry_id, final_paths)
            processed_count += 1
        else:
            print(f"  ✗ Nicht alle Bilder konnten konvertiert werden, Datenbank nicht aktualisiert.")
    
    if processed_count == 0:
        print("\nKeine Einträge verarbeitet.")
    else:
        print(f"\n{processed_count} Eintrag/Einträge erfolgreich verarbeitet.")


if __name__ == "__main__":
    main()
