#!/usr/bin/env python3
"""
autoallpics.py - Skript zur Überprüfung von Arbeitsverzeichnissen mit Bildern

Prüft in der Datenbank, ob:
1. Der work_path gesetzt ist
2. In diesem Pfad 3 Bilder liegen, die auf _1, _2 und _3 enden
3. Die Spalten final_picture_1, final_picture_2, final_picture_3 leer sind

Wenn alle Bedingungen erfüllt sind, wird der work_path ausgegeben.
"""

import os
import sqlite3
import sys
from pathlib import Path

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
        SELECT id, work_path, final_picture_1, final_picture_2, final_picture_3
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


def check_images_in_path(work_path):
    """
    Prüft, ob im angegebenen Pfad 3 Bilder liegen, die auf _1, _2 und _3 enden.
    
    Args:
        work_path: Der zu prüfende Pfad
        
    Returns:
        bool: True wenn alle 3 Bilder (_1, _2, _3) gefunden wurden
    """
    # Unterstützte Bildformate
    image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif'}
    
    # Prüfe, ob der Pfad existiert
    if not os.path.isdir(work_path):
        return False
    
    # Suche nach Bildern mit den Endungen _1, _2, _3
    found_1 = False
    found_2 = False
    found_3 = False
    
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
                found_1 = True
            elif name_without_ext.endswith('_2'):
                found_2 = True
            elif name_without_ext.endswith('_3'):
                found_3 = True
    except Exception as e:
        print(f"Fehler beim Durchsuchen von {work_path}: {e}", file=sys.stderr)
        return False
    
    return found_1 and found_2 and found_3


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
    
    # Basis-Verzeichnis für work_path (wahrscheinlich der move_path aus der Konfiguration)
    # Wir nehmen an, dass work_path entweder absolut oder relativ zum Projektverzeichnis ist
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    found_count = 0
    
    for entry in entries:
        entry_id, work_path, fp1, fp2, fp3 = entry
        
        # Konvertiere relativen Pfad zu absolutem Pfad falls nötig
        if not os.path.isabs(work_path):
            full_path = os.path.join(base_dir, work_path)
        else:
            full_path = work_path
        
        # Normalisiere den Pfad
        full_path = os.path.normpath(full_path)
        
        # Prüfe, ob alle 3 Bilder vorhanden sind
        if check_images_in_path(full_path):
            print(full_path)
            found_count += 1
    
    if found_count == 0:
        print("Keine passenden Verzeichnisse mit allen 3 Bildern (_1, _2, _3) gefunden.")
    else:
        print(f"\n{found_count} Verzeichnis(se) gefunden.", file=sys.stderr)


if __name__ == "__main__":
    main()
