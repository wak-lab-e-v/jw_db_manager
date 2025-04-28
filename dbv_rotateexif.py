import os
import argparse
import piexif
from PIL import Image

def get_current_orientation(exif_dict):
    """Lese die aktuelle Exif-Orientierung."""
    return exif_dict['0th'].get(274, 1)  # Standardwert ist 1 (keine Drehung)

def rotate_exif(image_path, output_path, angle):
    # Überprüfen, ob die Bilddatei existiert
    if not os.path.isfile(image_path):
        return 1, f"Fehler: Die Datei '{image_path}' wurde nicht gefunden."

    # Versuche, die Exif-Daten zu laden
    try:
        exif_dict = piexif.load(image_path)
    except Exception:
        # Wenn keine Exif-Daten vorhanden sind, erstelle ein neues Exif-Dictionary
        exif_dict = {
            "0th": {},
            "Exif": {},
            "GPS": {},
            "1st": {}
        }

    # Aktuelle Orientierung lesen
    current_orientation = get_current_orientation(exif_dict)

    # Exif-Daten anpassen (Orientierung)
    if (angle is None) or (angle == 0):
        new_orientation = current_orientation
    else:
        if current_orientation == 1:  # Keine Drehung
            new_orientation = 6 if angle == 90 else (3 if angle == 180 else 8)
        elif current_orientation == 6:  # 90 Grad
            new_orientation = 3 if angle == 90 else (8 if angle == 180 else 1)
        elif current_orientation == 3:  # 180 Grad
            new_orientation = 8 if angle == 90 else (1 if angle == 180 else 6)
        elif current_orientation == 8:  # 270 Grad
            new_orientation = 1 if angle == 90 else (6 if angle == 180 else 3)

    exif_dict['0th'][274] = new_orientation  # Setze die neue Orientierung

    # Exif-Daten in Bytes umwandeln
    exif_bytes = piexif.dump(exif_dict)

    # Bild speichern mit aktualisierten Exif-Daten
    piexif.insert(exif_bytes, image_path, output_path)
    return 0, f"Exif-Orientierung erfolgreich geändert und Bild gespeichert als '{output_path}'."

def main():
    # Argumente parsen
    parser = argparse.ArgumentParser(description='Drehe ein Bild und speichere es oder ändere die Exif-Orientierung eines JPG-Bildes.')
    parser.add_argument('image_file', type=str, help='Der Pfad zur Bilddatei.')
    parser.add_argument('output_image', type=str, help='Der Pfad zur Ausgabedatei.')
    parser.add_argument('angle', type=int, choices=[0, 90, 180, 270], help='Der Drehwinkel (0, 90, 180, 270 Grad).')

    args = parser.parse_args()

    # Bestimme den Dateityp
    file_extension = os.path.splitext(args.image_file)[1].lower()

    # Exif-Drehung für JPG und TIFF, sonst mit Pillow drehen
    if file_extension in ['.jpg', '.jpeg', '.tiff', '.tif']:
        status, message = rotate_exif(args.image_file, args.output_image, args.angle)
    else:
        status, message = rotate_image(args.image_file, args.output_image, args.angle)

    print(message)
    exit(status)

if __name__ == '__main__':
    #rotate_exif("../source/h.jpg", "../source/hr.jpg", 90)
    main()

