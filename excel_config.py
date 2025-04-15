"""
Konfigurationsdatei für Excel-Header-Mapping.
Diese Datei definiert die Zuordnung zwischen den Spaltennamen in der Excel-Datei
und den Variablennamen, die im Code verwendet werden.
"""

# Mapping von Spaltenindizes zu Namen (basierend auf der aktuellen Excel-Datei)
EXCEL_HEADER_MAPPING = {
    "BESTELLNUMMER": 3,       # "Bestellnumer" in der Excel-Datei
    "NAME": 6,                # "Name" in der Excel-Datei
    "VORNAME": 7,             # "Vorname" in der Excel-Datei
    "FEIERTAG": 17,           # "Feiertag" in der Excel-Datei
    "FEIERUHRZEIT": 18,       # "Feieruhrzeit" in der Excel-Datei
    "BILDER_DA": 31,          # "Bilder da" in der Excel-Datei
    "BILDERABGABE_WIE": 32,   # "Bilderabgabe wie" in der Excel-Datei
}

# Umgekehrtes Mapping (von Namen zu Spaltenindizes)
EXCEL_COLUMN_INDICES = {v: k for k, v in EXCEL_HEADER_MAPPING.items()}

# Funktion zum Aktualisieren der Indizes, falls sich die Spaltenreihenfolge ändert
def update_indices(df):
    """
    Aktualisiert die Spaltenindizes basierend auf den tatsächlichen Header-Namen in der Datei.
    
    Args:
        df (pandas.DataFrame): Das DataFrame mit den Daten aus der Excel-Datei
    
    Returns:
        dict: Aktualisiertes Mapping von Variablennamen zu Spaltenindizes
    """
    # Erste Zeile als Header verwenden
    header_row = df.iloc[0]
    
    # Mapping für die benötigten Spalten erstellen
    updated_mapping = {}
    
    # Suche nach den benötigten Spalten
    for col_idx, col_name in enumerate(header_row):
        if col_name == "Bestellnumer":
            updated_mapping["BESTELLNUMMER"] = col_idx
        elif col_name == "Name":
            updated_mapping["NAME"] = col_idx
        elif col_name == "Vorname":
            updated_mapping["VORNAME"] = col_idx
        elif col_name == "Feiertag":
            updated_mapping["FEIERTAG"] = col_idx
        elif col_name == "Feieruhrzeit":
            updated_mapping["FEIERUHRZEIT"] = col_idx
        elif col_name == "Bilder da":
            updated_mapping["BILDER_DA"] = col_idx
        elif col_name == "Bilderabgabe wie":
            updated_mapping["BILDERABGABE_WIE"] = col_idx
    
    return updated_mapping
