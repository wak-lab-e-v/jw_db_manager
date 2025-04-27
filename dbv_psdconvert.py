import argparse
import os
from psd_tools import PSDImage

def psd_to_png(psd_file, output_image):
    # Überprüfen, ob die PSD-Datei existiert
    if not os.path.isfile(psd_file):
        return 1, f"Fehler: Die Datei '{psd_file}' wurde nicht gefunden."

    try:
        # PSD-Datei öffnen
        psd = PSDImage.open(psd_file)

        # PSD in PNG umwandeln und speichern
        psd.save(output_image)
        return 0, f"Bild erfolgreich gespeichert als '{output_image}'."
    except Exception as e:
        return 1, f"Fehler beim Verarbeiten der Datei: {str(e)}"

def main():
    # Argumente parsen
    parser = argparse.ArgumentParser(description='Konvertiere eine PSD-Datei in ein PNG-Bild.')
    parser.add_argument('psd_file', type=str, help='Der Pfad zur PSD-Datei.')
    parser.add_argument('output_image', type=str, help='Der Pfad zur Ausgabedatei (PNG).')

    args = parser.parse_args()

    # PSD in PNG umwandeln
    status, message = psd_to_png(args.psd_file, args.output_image)
    print(message)
    exit(status)

if __name__ == '__main__':
    main()
