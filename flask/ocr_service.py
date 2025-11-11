"""
OCR Service using OCR.Space API
Lightweight OCR solution that works well in Docker environments.
"""

import requests

OCR_API_URL = "https://api.ocr.space/parse/image"
OCR_API_KEY = "K86143460188957"  # your key


def extract_text_from_image(image_file):
    """
    Send image to OCR.Space and return extracted text.
    
    Args:
        image_file: File-like object or file path
        
    Returns:
        Extracted text string or error message
    """
    try:
        # If image_file is a string (file path), open it
        if isinstance(image_file, str):
            with open(image_file, 'rb') as f:
                files = {"file": f}
                response = requests.post(
                    OCR_API_URL,
                    files=files,
                    data={"apikey": OCR_API_KEY, "language": "eng"}
                )
        else:
            # If it's already a file-like object
            response = requests.post(
                OCR_API_URL,
                files={"file": image_file},
                data={"apikey": OCR_API_KEY, "language": "eng"}
            )
        
        result = response.json()
        
        # Check if OCR was successful
        if result.get("OCRExitCode") == 1 and result.get("ParsedResults"):
            return result["ParsedResults"][0]["ParsedText"].strip()
        else:
            error_message = result.get("ErrorMessage", ["Unknown error"])[0] if result.get("ErrorMessage") else "OCR failed"
            print(f"OCR.Space API error: {error_message}")
            return ""
            
    except Exception as e:
        print(f"Error in OCR service: {e}")
        import traceback
        traceback.print_exc()
        return ""

