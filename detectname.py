import cv2
import pytesseract
import numpy as np
from difflib import SequenceMatcher

# Set Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def is_reasonable_text(text):
    """Check if text looks like a plausible word/name without being too strict"""
    text = text.lower().strip()
    if len(text) < 2:  # Too short
        return False
    
    # Very unlikely letter combinations
    forbidden_combos = ['zx', 'xj', 'qj', 'jq', 'qz', 'vw', 'vv', 'jk', 'kj']
    for combo in forbidden_combos:
        if combo in text:
            return False
    
    # Should have at least one vowel (unless it's a very short abbreviation)
    vowels = {'a', 'e', 'i', 'o', 'u'}
    if len(text) > 3 and not any(vowel in text for vowel in vowels):
        return False
    
    return True

def find_text(frame, card_contour):
    try:
        if card_contour is None:
            return None
            
        x_card, y_card, w_card, h_card = cv2.boundingRect(card_contour)
        
        # Expanded ROI to capture more of the text area
        roi_top_start = max(0, int(y_card + h_card * 0.05))
        roi_top_end = min(frame.shape[0], int(y_card + h_card * 0.13))  # Increased from 0.13 to 0.2
        roi_left = max(0, x_card)
        roi_right = min(frame.shape[1], x_card + w_card)
        
        roi = frame[roi_top_start:roi_top_end, roi_left:roi_right]
        
        if roi.size == 0:
            return None
        
        # More balanced preprocessing
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Try multiple preprocessing methods and pick the clearest one
        processed_images = []
        
        # Method 1: Simple threshold
        _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(thresh1)
        
        # Method 2: Adaptive threshold
        thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        processed_images.append(thresh2)
        
        # Method 3: Denoising + threshold
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, thresh3 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(thresh3)
        
        best_text = ""
        for img in processed_images:
            # Moderate scaling
            scaled = cv2.resize(img, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # Try different OCR configurations
            configs = [
                "--psm 7",  # Single text line
                "--psm 8",  # Single word
                "--psm 10"  # Single character
            ]
            
            for config in configs:
                text = pytesseract.image_to_string(
                    scaled, 
                    config=config + " -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                ).strip()
                
                if len(text) > len(best_text):
                    best_text = text
        
        # Clean up the text
        clean_text = ''.join(c for c in best_text if c.isalpha())
        
        # Basic validation
        if len(clean_text) >= 2 and is_reasonable_text(clean_text):
            return clean_text.title()
        
        return None
        
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None

def compare_strings(string1, string2):
    if not string1 or not string2:
        return 0.0
        
    string1 = str(string1).lower()
    string2 = str(string2).lower()
    
    # Use sequence matching with some flexibility
    matcher = SequenceMatcher(None, string1, string2)
    return matcher.ratio()
