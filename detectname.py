import cv2
import pytesseract
import numpy as np
from difflib import SequenceMatcher

# Set Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Replace with your path

def find_text(frame, card_contour):
    try:
        if card_contour is None:
            return None
        x_card, y_card, w_card, h_card = cv2.boundingRect(card_contour)
        roi_top_start = int(y_card + h_card * 0.05)
        roi_top_end = int(y_card + h_card * 0.11)
        roi = frame[roi_top_start:roi_top_end, x_card:x_card + w_card]
        new_h = int(roi.shape[0] * 4)
        new_w = int(roi.shape[1] * 4)
        magnified = cv2.resize(roi, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(magnified, cv2.COLOR_BGR2GRAY)
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        thresh = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        kernel = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=3)
        text = pytesseract.image_to_string(dilated, config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        extracted_text = text.strip()
        cv2.imshow("Processed Area", dilated)
        if extracted_text:
            return extracted_text
        return None
    except Exception:
        return None

def compare_strings(string1, string2):
    if not isinstance(string1, str) or not isinstance(string2, str):
        return 0
    return float(SequenceMatcher(0, string1.lower(), string2.lower()).ratio())
