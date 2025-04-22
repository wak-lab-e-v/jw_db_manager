import argparse
import sys
import os
from PIL import Image, ImageDraw, ImageFont, ExifTags

def get_image_orientation(image_path):
    """
    Get the orientation of the image based on EXIF data.
    
    Args:
        image_path (str): Path to the input image.
    
    Returns:
        int: Rotation angle in degrees (0, 90, 180, 270).
    """
    try:
        img = Image.open(image_path)
        # Get EXIF data
        exif = img._getexif()
        
        if exif is not None:
            for tag, value in exif.items():
                if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                    if value == 1:
                        return 0
                    elif value == 3:
                        return 180
                    elif value == 6:
                        return 270
                    elif value == 8:
                        return 90
        
        # Default rotation if no EXIF data or orientation is not found
        return 0
    
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
        return 0  # Default rotation

def process_image(image_path, person_name, shift_right=True):
    """
    Process an image by:
    1. Resizing to Full HD (1920x1080)
    2. If vertical, shift 25% to left/right and add name on the other side
    3. If horizontal, add name at the bottom
    4. Add semi-transparent gray background behind the name
    
    Args:
        image_path (str): Path to the input image
        person_name (str): Name to overlay on the image
        shift_right (bool): If True, shift vertical images to the right, else to the left
    
    Returns:
        PIL.Image: Processed image
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Get original dimensions
        width, height = img.size

        # Get the rotation angle based on EXIF data
        rotation_angle = get_image_orientation(image_path)
        
        # Rotate the image if necessary
        if rotation_angle != 0:
            img = img.rotate(rotation_angle, expand=True)
            width, height = img.size  # Update dimensions after rotation    
        
        # Determine if the image is vertical or horizontal
        is_vertical = height > width
        
        # Create a black canvas with Full HD resolution (1920x1080)
        canvas = Image.new('RGB', (1920, 1080), (0, 0, 0))
        
        # Resize the image while maintaining aspect ratio
        if is_vertical:
            # For vertical images, resize to fit height
            ratio = 1080 / height
            new_width = int(width * ratio)
            new_height = 1080
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Calculate the position to paste the image (35% shift - increased from 25%)
            shift_amount = int(1920 * 0.35)  # More room for text
            
            if shift_right:
                # Shift image to the right with margin, text will be on the left
                paste_position = (1920 - new_width - 80, 0)  # 80px margin from right edge
                text_position = (1920 // 2, 1080 - 80)  # Position closer to bottom
                text_align = "center"
            else:
                # Shift image to the left with margin, text will be on the right
                paste_position = (80, 0)  # 80px margin from left edge
                text_position = (1920 // 2, 1080 - 80)  # Position closer to bottom
                text_align = "center"
        else:
            # For horizontal images, resize to fit width
            ratio = 1920 / width
            new_width = 1920
            new_height = int(height * ratio)
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Center the image vertically
            paste_position = (0, (1080 - new_height) // 2)
            text_position = (1920 // 2, 1080 - 80)  # Position closer to bottom
            text_align = "center"
        
        # Paste the resized image onto the canvas
        canvas.paste(resized_img, paste_position)
        
        # Add text with semi-transparent background
        draw = ImageDraw.Draw(canvas)
        
        # Try to load a nice font with a MUCH larger size
        font_size = 150  # Extremely large font size
        try:
            # Try several common fonts
            try:
                font = ImageFont.truetype("Arial", font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("DejaVuSans", font_size)
                except IOError:
                    try:
                        font = ImageFont.truetype("FreeSans", font_size)
                    except IOError:
                        # Last resort - use default but still make it large
                        default_font = ImageFont.load_default()
                        # The default font is typically very small, so we'll create a larger version
                        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except Exception as e:
            print(f"Warning: Could not load desired font: {e}")
            # Absolute fallback - use default
            font = ImageFont.load_default()
            font_size = 150  # Still try to make it as large as possible
        
        # Calculate text size (compatible with newer Pillow versions)
        try:
            # For newer Pillow versions
            bbox = font.getbbox(person_name)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            try:
                # For older Pillow versions
                text_width, text_height = draw.textsize(person_name, font=font)
            except AttributeError:
                # Fallback method
                text_width = font_size * len(person_name) * 0.6  # Rough estimate
                text_height = font_size * 1.2
        
        # Adjust text position based on alignment
        if text_align == "center":
            text_x = text_position[0] - text_width // 2
        elif text_align == "right":
            text_x = text_position[0] - text_width
        else:  # left
            text_x = text_position[0]
        
        text_y = text_position[1] - text_height // 2
        
        # Create a semi-transparent gray background for text
        padding_vertical = 10  # Vertical padding
        padding_horizontal = 20  # Horizontal padding for side text
        
        # Create a darker gray background color
        darker_gray = (80, 80, 80, 168)  # Darker gray with higher opacity
        
        if is_vertical:
            # For vertical images, place text on the side (opposite to the image shift) without a gray bar
            
            # Wrap the name by inserting newlines at spaces
            wrapped_name = ""
            max_chars_per_line = 10  # Adjust based on font size
            words = person_name.split()
            current_line = words[0]
            
            for word in words[1:]:
                if len(current_line) + len(word) + 1 <= max_chars_per_line:
                    current_line += " " + word
                else:
                    wrapped_name += current_line + "\n"
                    current_line = word
            
            wrapped_name += current_line
            
            # Use the wrapped name instead of the original
            person_name = wrapped_name
            
            # Recalculate text dimensions with wrapped text
            lines = wrapped_name.count("\n") + 1
            try:
                # For newer Pillow versions
                bbox = font.getbbox(wrapped_name)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1] * lines  # Approximate height for wrapped text
            except AttributeError:
                # Fallback method
                text_width = font_size * max([len(line) for line in wrapped_name.split("\n")]) * 0.6
                text_height = font_size * 1.2 * lines
            
            if shift_right:
                # Image is on the right with margin, so text goes on the left side
                text_x = 200  # Left margin
            else:
                # Image is on the left with margin, so text goes on the right side
                text_x = 1920 - text_width - 200  # Right margin
            
            # Center text vertically
            text_y = (1080 - text_height) // 2
            
            # Create a semi-transparent background for the text
            text_bg_height = int(text_height + padding_vertical*2 - font_size * 0.2) # Height of the background
            text_bg_width = int(text_width + padding_horizontal * 2)    # Width of the background
            text_bg = Image.new('RGBA', (text_bg_width, text_bg_height), (80, 80, 80, 168))  # Darker gray with opacity
            canvas.paste(text_bg, (text_x - padding_horizontal, text_y + padding_vertical), text_bg)
            
        else: # QUER
            # For horizontal images, place text at the bottom
            # Calculate background dimensions for bottom placement
            text_bg_height = int(text_height + padding_vertical*2) #  - font_size * 0.2)
            
            # Position the background at the bottom
            bg_y_position = 1080 - text_bg_height
            text_y = bg_y_position + padding_vertical - 30  # Move text up a bit
            
            # Create and paste the full-width background
            text_bg = Image.new('RGBA', (1920, text_bg_height), darker_gray)
            canvas.paste(text_bg, (0, bg_y_position), text_bg)
        
        # Draw the text in sun yellow color
        sun_yellow = (255, 215, 0)  # RGB value for sun yellow
        
        # Use align parameter for multiline text
        draw.text((text_x, text_y), person_name, fill=sun_yellow, font=font, align=text_align)
        
        return canvas
    
    except Exception as e:
        print(f"Error processing image: {e}")
        raise  
    
def execute_autoconvert(source, dest, text):
    # Überprüfen, ob die Quelldatei existiert
    if not os.path.isfile(source):
        return False, f"Error: The source file '{source}' does not exist."
    
    try:
        # Verarbeite das Bild
        processed_image = process_image(source, text)
        
        # Speichere das bearbeitete Bild im Zielpfad
        processed_image.save(dest)
        return True, "Conversion successful"
    
    except Exception as e:
        return False, f"Error during image processing: {e}"


def parse_arguments():
    """
    Parses the command line arguments.
    
    Returns:
        argparse.Namespace: The parsed arguments
    """
    parser = argparse.ArgumentParser(description='Convert images')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Auto command
    import_parser = subparsers.add_parser('auto', help='Automatically convert images')
    import_parser.add_argument('--source-file', '-s', required=True, help='Path to the source image')
    import_parser.add_argument('--destination-file', '-d', required=True, help='Path to the output image')
    import_parser.add_argument('--text', '-t', required=True, help='Caption for the image')
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse the command line arguments
    args = parse_arguments()
    
    if not args.command:
        print("Error: No command specified. Use 'python dbv_autoimgcov.py -h' for help.")
        sys.exit(1)
        # print(execute_autoconvert('../source/h.jpg', '../source/h1.jpg', "Hallo Text"))
        # print(execute_autoconvert('../source/q.jpg', '../source/q1.jpg', "Hallo Text"))
        
        
    if args.command == 'auto':
        # Use the parsed arguments
        source_file = args.source_file
        destination_file = args.destination_file
        text = args.text
        
        success, message = execute_autoconvert(source_file, destination_file, text)
        print(message)
