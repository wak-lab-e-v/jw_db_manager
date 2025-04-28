#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import base64
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from PIL import Image
import io
import uuid
import json

app = Flask(__name__)

# Ensure the templates directory exists
os.makedirs('templates', exist_ok=True)

@app.route('/')
def index():
    """Main page that allows image path input."""
    return render_template('img_edit_index.html')

@app.route('/edit', methods=['GET'])
def edit():
    """Edit page that displays and allows editing of the image."""
    image_path = request.args.get('path', '')
    encoded = request.args.get('encoded', 'false').lower() == 'true'
    
    if not image_path:
        return redirect(url_for('index'))
    
    # Handle base64 encoded path
    if encoded:
        try:
            image_path = base64.b64decode(image_path).decode('utf-8')
        except Exception as e:
            return f"Error decoding path: {str(e)}", 400
    else:
        # URL decode the path
        image_path = urllib.parse.unquote(image_path)
    
    # Validate that the file exists and is an image
    if not os.path.isfile(image_path):
        return f"Image not found: {image_path}", 404
    
    try:
        with Image.open(image_path) as img:
            # Get image info
            width, height = img.size
            format = img.format
            
            # Get directory and filename for saving
            directory = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            
            # Create a data URL for the image
            buffered = io.BytesIO()
            img.save(buffered, format=format)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            data_url = f"data:image/{format.lower()};base64,{img_str}"
            
            return render_template('img_edit.html', 
                                  image_data=data_url,
                                  image_path=image_path,
                                  width=width,
                                  height=height,
                                  filename=filename,
                                  directory=directory)
    except Exception as e:
        return f"Error processing image: {str(e)}", 500

@app.route('/save', methods=['POST'])
def save():
    """Save the edited image."""
    try:
        data = json.loads(request.data)
        image_data = data.get('imageData', '')
        original_path = data.get('originalPath', '')
        
        if not image_data or not original_path:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        
        # Remove the data URL prefix
        image_data = image_data.split(',')[1]
        
        # Decode the base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Get directory and filename for saving
        directory = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        
        # Create a new filename
        new_filename = f"{name}_edited{ext}"
        new_path = os.path.join(directory, new_filename)
        
        # Ensure we don't overwrite existing files
        counter = 1
        while os.path.exists(new_path):
            new_filename = f"{name}_edited_{counter}{ext}"
            new_path = os.path.join(directory, new_filename)
            counter += 1
        
        # Save the image
        with open(new_path, 'wb') as f:
            f.write(image_bytes)
        
        return jsonify({'success': True, 'path': new_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates if they don't exist
    app.run(debug=True, host='0.0.0.0', port=4455)
