"""
Implementierung des Stats-Befehls für den Datenbankmanager.
Zeigt Statistiken über die Daten in der SQLite-Datenbank an.
"""

def execute_stats(db_manager, detailed=False):
    """
    Führt den Stats-Befehl aus.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        detailed (bool): Wenn True, werden detailliertere Statistiken angezeigt
        
    Returns:
        tuple: (Erfolg (bool), Nachricht (str))
    """
    show_statistics(db_manager, detailed)
    return True, "Statistiken wurden angezeigt."

def show_statistics(db_manager, detailed=False):
    """
    Zeigt Statistiken über die Daten in der Datenbank.
    
    Args:
        db_manager: Eine Instanz des DatabaseManager
        detailed (bool): Wenn True, werden detailliertere Statistiken angezeigt
    """
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
