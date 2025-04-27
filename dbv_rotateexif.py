import os
import argparse
import piexif

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

    # Exif-Daten anpassen (Orientierung)
    if angle == 90:
        exif_dict['0th'][274] = 6  # 6 = 90 Grad im Uhrzeigersinn
    elif angle == 180:
        exif_dict['0th'][274] = 3  # 3 = 180 Grad
    elif angle == 270:
        exif_dict['0th'][274] = 8  # 8 = 270 Grad im Uhrzeigersinn
    else:
        exif_dict['0th'][274] = 1  # 1 = keine Drehung

    # Exif-Daten in Bytes umwandeln
    exif_bytes = piexif.dump(exif_dict)

    # Bild speichern mit aktualisierten Exif-Daten
    piexif.insert(exif_bytes, image_path, output_path)
    return 0, f"Exif-Orientierung erfolgreich geändert und Bild gespeichert als '{output_path}'."

def main():
    # Argumente parsen
    parser = argparse.ArgumentParser(description='Ändere die Exif-Orientierung eines JPG-Bildes.')
    parser.add_argument('image_file', type=str, help='Der Pfad zur JPG-Datei.')
    parser.add_argument('output_image', type=str, help='Der Pfad zur Ausgabedatei (JPG).')
    parser.add_argument('angle', type=int, choices=[0, 90, 180, 270], help='Der Drehwinkel (0, 90, 180, 270 Grad).')

    args = parser.parse_args()

    # Exif-Orientierung ändern
    status, message = rotate_exif(args.image_file, args.output_image, args.angle)
    print(message)
    exit(status)

if __name__ == '__main__':
    main()