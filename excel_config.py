"""
Konfigurationsdatei für Excel-Header-Mapping.
Diese Datei definiert die Zuordnung zwischen den Spaltennamen in der Excel-Datei
und den Variablennamen, die im Code verwendet werden.
"""

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
    
    # Mapping von normalisierten Spaltennamen (lowercase, ohne Leerzeichen)
    # auf interne Variablennamen. Mehrere Varianten pro Feld erlaubt, um
    # Tippfehler und Umbenennungen in der Excel-Datei abzufangen.
    column_aliases = {
        "BESTELLNUMMER":     ["bestellnummer", "bestellnumer"],
        "NAME":              ["name"],
        "VORNAME":           ["vorname"],
        "FEIERTAG":          ["feiertag"],
        "FEIERUHRZEIT":      ["feieruhrzeit"],
        "BILDER_DA":         ["bilderda"],
        "BILDERABGABE_WIE":  ["bilderabgabewie"],
        "LOCATION":          ["location", "feierort"],
    }

    def normalize(value):
        if value is None:
            return ""
        return "".join(str(value).lower().split())

    # Suche nach den benötigten Spalten
    for col_idx, col_name in enumerate(header_row):
        norm = normalize(col_name)
        if not norm:
            continue
        for var_name, aliases in column_aliases.items():
            if var_name in updated_mapping:
                continue
            if norm in aliases:
                updated_mapping[var_name] = col_idx
                break

    return updated_mapping
