"""
German License Plate Extraction Module
Handles plate detection, OCR, and formatting for German license plates using OCR.Space API.
"""

import re
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from ocr_service import extract_text_from_image

# German license plate regex pattern
GERMAN_PLATE_REGEX = r"[A-Z]{1,3}-[A-Z]{1,2}\s?[0-9]{1,4}"


def clean_ocr_text(text):
    """
    Clean OCR output and normalize for German plate format.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Cleaned uppercase text with only alphanumeric and dash
    """
    if not text:
        return ""
    
    # Convert to uppercase
    text = text.upper()
    
    # Remove all non-alphanumeric except dash and space
    text = re.sub(r'[^A-Z0-9\-\s]', '', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def format_german_plate(text):
    """
    Format cleaned text into German plate format: REGION-LETTERS NUMBERS
    
    Args:
        text: Cleaned OCR text
        
    Returns:
        Formatted plate string or None if invalid
    """
    if not text:
        return None
    
    # Remove all spaces and normalize
    text_no_spaces = text.replace(' ', '').replace('-', '')
    
    # Try multiple patterns to match German plate format
    patterns = [
        # Pattern 1: REGION-LETTERS NUMBERS (with dash)
        r'^([A-Z]{1,3})-([A-Z]{1,2})([0-9]{1,4})$',
        # Pattern 2: REGION LETTERS NUMBERS (with space)
        r'^([A-Z]{1,3})\s([A-Z]{1,2})([0-9]{1,4})$',
        # Pattern 3: REGIONLETTERSNUMBERS (no separator, need to split)
        r'^([A-Z]{1,3})([A-Z]{1,2})([0-9]{1,4})$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            region, letters, numbers = match.groups()
            return f"{region}-{letters} {numbers}"
    
    # Try to extract components from text without separators
    flexible_pattern = r'^([A-Z]{1,3})([A-Z]{1,2})([0-9]{1,4})'
    match = re.match(flexible_pattern, text_no_spaces)
    if match:
        region, letters, numbers = match.groups()
        return f"{region}-{letters} {numbers}"
    
    # Try reverse: find numbers first, then letters, then region
    reverse_match = re.search(r'([0-9]{1,4})([A-Z]{1,2})([A-Z]{1,3})$', text_no_spaces)
    if reverse_match:
        numbers, letters, region = reverse_match.groups()
        return f"{region}-{letters} {numbers}"
    
    return None


def extract_german_plate(image_path):
    """
    Main function to extract vehicle license plate number from image using OCR.Space API.
    
    Args:
        image_path: Path to vehicle image file
        
    Returns:
        Formatted plate string (e.g., "B-MA 1234") or "NO VALID GERMAN PLATE DETECTED"
    """
    try:
        # Extract text using OCR.Space API
        raw_text = extract_text_from_image(image_path)
        
        if not raw_text:
            return "NO VALID GERMAN PLATE DETECTED"
        
        # Clean the OCR text
        cleaned = clean_ocr_text(raw_text)
        
        if not cleaned:
            return "NO VALID GERMAN PLATE DETECTED"
        
        # Try to format as German plate
        formatted = format_german_plate(cleaned)
        if formatted and re.match(GERMAN_PLATE_REGEX, formatted):
            return formatted
        
        # If formatting failed, try direct regex match
        if re.match(GERMAN_PLATE_REGEX, cleaned):
            # Format it properly
            match = re.match(r'([A-Z]{1,3})-?([A-Z]{1,2})([0-9]{1,4})', cleaned)
            if match:
                region, letters, numbers = match.groups()
                return f"{region}-{letters} {numbers}"
            return cleaned
        
        # Try without spaces
        cleaned_no_space = cleaned.replace(' ', '')
        formatted = format_german_plate(cleaned_no_space)
        if formatted and re.match(GERMAN_PLATE_REGEX, formatted):
            return formatted
        
        if re.match(GERMAN_PLATE_REGEX, cleaned_no_space):
            match = re.match(r'([A-Z]{1,3})-?([A-Z]{1,2})([0-9]{1,4})', cleaned_no_space)
            if match:
                region, letters, numbers = match.groups()
                return f"{region}-{letters} {numbers}"
            return cleaned_no_space
        
        return "NO VALID GERMAN PLATE DETECTED"
        
    except Exception as e:
        print(f"Error in plate extraction: {e}")
        import traceback
        traceback.print_exc()
        return "NO VALID GERMAN PLATE DETECTED"


def register_plate_extraction_routes(app):
    """
    Register plate extraction routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.route("/extract-plate", methods=["POST"])
    def extract_plate():
        """
        POST: Extract German license plate from uploaded image.
        
        Accepts:
            - Form data with field "image" containing image file
            
        Returns:
            JSON: {"plate_number": "B-MA 1234"} or {"plate_number": "NO VALID GERMAN PLATE DETECTED"}
        """
        # POST method - process image
        try:
            # Check if image file is present
            if 'image' not in request.files:
                return jsonify({"error": "No image file provided"}), 400
            
            file = request.files['image']
            
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            # Check file extension
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
            if not ('.' in file.filename and 
                   file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                return jsonify({"error": "Invalid file type. Only images are allowed."}), 400
            
            # Check file size (max 1MB)
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            max_size = 1 * 1024 * 1024  # 1MB
            if file_size > max_size:
                return jsonify({"error": "File too large. Maximum size is 1MB."}), 400
            
            # Save temporary file
            temp_dir = os.path.join(os.path.dirname(__file__), 'static', 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            filename = secure_filename(file.filename)
            temp_path = os.path.join(temp_dir, f"plate_{os.urandom(8).hex()}_{filename}")
            file.save(temp_path)
            
            try:
                # Extract plate using OCR.Space API
                plate_number = extract_german_plate(temp_path)
                
                return jsonify({
                    "plate_number": plate_number
                }), 200
                
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error in extract_plate route: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
