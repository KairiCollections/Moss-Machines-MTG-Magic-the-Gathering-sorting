# config.py
# Configuration settings for the card sorting application.

# Image and Processing Settings
CROP_SIZE = 745          # Size of the image crop for hashing
WIDTH = 745              # Width of the perspective-corrected card image
HEIGHT = 1043            # Height of the perspective-corrected card image
MAX_DISTANCE_THRESHOLD = 100  # Hashing match threshold

# Data Paths (Consider making these relative to the script's location)
CARDS_JSON_PATH = "default-cards-20241206100658.json"
HASH_DB_PATH = "card_hashes.json"  # If you are using one
IMAGES_DIR = "downloaded_cards"      # If you are using one
LAYOUT_SIGNATURES_JSON = "layout_signatures.json" # If you are using one

# Card Set Exclusion
EXCLUDED_SETS = {"30a", "lea", "leb", "fbb", "ced", "cei", "4bb", "ptc", "sum"}

# Sorting Options
SORTING_MODES = {
    "1": "color",
    "2": "mana_value",
    "3": "set",
    "4": "price",
    "5": "type",  # Add "type" if you intend to use it
    "6": "buy"
}

# Serial Communication
SERIAL_PORT = "COM3"  # Your serial port
BAUD_RATE = 9600
START_MARKER = 60
END_MARKER = 62

# Name Detection
MAX_ATTEMPTS_NAME = 5
TIMEOUT_NAME = 10  # seconds

# Model
MODEL_PATH = "mana_v14.pt"
