import os
from PIL import Image , ImageDraw, ImageFont
import subprocess

# Verzeichnisse
input_dir = r'Person'  # Pfad zu deinem Eingangsverzeichnis
output_dir = r'output'  # Pfad zu deinem Ausgangsverzeichnis

# Stelle sicher, dass das Ausgangsverzeichnis existiert
os.makedirs(output_dir, exist_ok=True)

# Funktion zum Formatieren der Bilder
def format_image(image_path, name):
    with Image.open(image_path) as img:
        # Berechne die neue Höhe, um das Bild auf 1080 zu skalieren
        scale_factor = 1080 / img.height
        new_height = 1080
        new_width = int(img.width * scale_factor)
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Erstelle ein neues Bild mit schwarzem Rand
        final_image = Image.new('RGB', (1920, 1080), (0, 0, 0))

        # Berechne die Position für den goldenen Schnitt
        left_margin = int(1920 * 0.618)  # 61,8% der Breite
        img_x = left_margin - (new_width // 2)  # Positioniere das Bild im goldenen Schnitt
        final_image.paste(img, (img_x, 0))

        # Füge den Text in einem separaten Layer hinzu
        text_layer = Image.new('RGBA', final_image.size, (0, 0, 0, 0))  # Transparenter Hintergrund
        draw = ImageDraw.Draw(text_layer)
        font_size = 125  # Setze die Schriftgröße
        font_path = "arabella.regular.ttf"  # Pfad zur Schriftartdatei
        font = ImageFont.truetype(font_path, font_size)

        text_bbox = draw.textbbox((0, 0), name, font=font)  # Berechne die Bounding-Box
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Positioniere den Text im schwarzen Rand links
        text_x = 10  # Ein kleiner Abstand vom linken Rand
        text_y = (1080 - text_height) // 2  # Vertikal zentriert
        draw.text((text_x, text_y), name, fill=(255, 255, 0), font=font)  # Gelber Text

        # Speichere das Bild und den Textlayer als separate TIFF-Dateien
        output_image_path = os.path.join(output_dir, os.path.basename(image_path).replace('.jpg', '.tiff').replace('.jpeg', '.tiff').replace('.png', '.tiff'))
        output_text_path = os.path.join(output_dir, f"{name}_text.tiff")
        output_psd_path = os.path.join(output_dir, f"{name}_.tiff")

        # Speichere das finale Bild
        final_image.save(output_image_path, format='TIFF')

        # Speichere den Textlayer
        text_layer.save(output_text_path, format='TIFF')
        
        tiffconvert([output_image_path, output_text_path],output_tif_path) 
        
def tiffconvert(input_images, output_file):
    # Erstelle den ImageMagick-Befehl
    command = ['convert'] + input_images + [ output_file]  # '-layers', 'flatten',
    print(command)
    # Führe den Befehl aus
    subprocess.run(command)

# Durchlaufe alle Bilder im Eingangsverzeichnis
for filename in os.listdir(input_dir):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        name = os.path.splitext(filename)[0]  # Nimm den Dateinamen ohne Erweiterung
        format_image(os.path.join(input_dir, filename), name)

print("Bilder wurden erfolgreich formatiert und als TIFF gespeichert.")

