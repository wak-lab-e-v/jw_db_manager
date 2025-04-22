#!/usr/bin/env python3
import argparse
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import numpy as np

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
        else:
            # For horizontal images, place text at the bottom
            # Calculate background dimensions for bottom placement
            text_bg_height = text_height + padding_vertical*2
            
            # Position the background at the bottom
            bg_y_position = 1080 - text_bg_height
            text_y = bg_y_position + padding_vertical - 20  # Move text up a bit
            
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
    
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process an image and add a name overlay.')
    parser.add_argument('image_path', type=str, help='Full path to the input image')
    parser.add_argument('person_name', type=str, help='Name to overlay on the image')
    parser.add_argument('--shift', type=str, choices=['left', 'right'], default='right',
                        help='Direction to shift vertical images (default: right)')
    parser.add_argument('--output', type=str, help='Output file path (default: adds "_processed" to the input filename)')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.isfile(args.image_path):
        print(f"Error: Input file '{args.image_path}' does not exist.")
        return 1
    
    # Process the image
    processed_img = process_image(
        args.image_path, 
        args.person_name, 
        shift_right=(args.shift == 'right')
    )
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        filename, ext = os.path.splitext(args.image_path)
        output_path = f"{filename}_processed{ext}"
    
    # Save the processed image
    processed_img.save(output_path)
    print(f"Processed image saved to: {output_path}")
    
    return 0

if __name__ == "__main__":
    exit(main())
