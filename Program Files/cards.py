import os
import json
import glob

from config import EXCLUDED_SETS

CARDS_DATA = []
CARD_DATA_BY_ID = {}

# Construct the wildcard pattern in the current directory
default_files_pattern = 'default*.json'

# Find all files matching the pattern in the current directory
default_files = glob.glob(default_files_pattern)

# Sort files by modification time (newest first)
default_files.sort(key=os.path.getmtime, reverse=True)

# Check if any files were found
if default_files:
    # Get the path of the newest file
    newest_file_path = default_files[0]

    if os.path.exists(newest_file_path):
        try:
            with open(newest_file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                CARDS_DATA.extend(file_data)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {newest_file_path}: {e}")
        except Exception as e:
            print(f"An error occurred while reading {newest_file_path}: {e}")
    else:
        print(f"Error: The newest file path '{newest_file_path}' does not exist.")
else:
    print(f"No files matching the pattern '{default_files_pattern}' found.")


CARD_DATA_BY_ID = {c['id']: c for c in CARDS_DATA}
total_entries_loaded = len(CARDS_DATA)
print(f"Successfully loaded {total_entries_loaded} card entries from the newest default*.json file ({newest_file_path}).")

def extract_card_info(card_id):
    card = CARD_DATA_BY_ID.get(card_id)
    if not card:
        return None
    name = card.get('name', 'Unknown')
    set_code = card.get('set', '???')
    colors = card.get('colors', [])
    color_identity = card.get('color_identity', [])
    cmc = card.get('cmc')
    is_promo = card.get('Promo')
    usd_price = card.get('prices', {}).get('usd')
    price_str = "null"
    mana_cost = card.get('mana_cost', '???')
    if usd_price:
        try:
            price_str = f"${float(usd_price):.2f}"  # Simplified price formatting
        except (ValueError, TypeError):  # Handle potential errors
            pass
    types = [t for t in ["creature", "artifact", "enchantment", "instant", "sorcery", "battle", "planeswalker", "land", "token"]
             if t in card.get('type_line', '').lower()] # Simplified type extraction
    return {
        "Name": name,"Set": set_code,"Colors": colors,"Color Identity": color_identity,"CMC": cmc,"Types": types,"Price": price_str,"Promo": is_promo,"Mana Cost": mana_cost
    }

def card_is_allowed(card_id):
    card = CARD_DATA_BY_ID.get(card_id)
    if not card:
        return False
    set_code = card.get('set', '').lower()
    games = card.get('games', [])
    return 'paper' in games and set_code not in EXCLUDED_SETS  # Combined conditions

def get_illustration_id(card_id):
    card = CARD_DATA_BY_ID.get(card_id)
    return card.get('illustration_id') if card else None  # Simplified

def get_same_illustration_english_candidates(illustration_id):
    return [  # List comprehension with combined conditions
        c['id'] for c in CARDS_DATA
        if c.get('illustration_id') == illustration_id and c.get('lang') == 'en' and
           'paper' in c.get('games', []) and c.get('set', '').lower() not in EXCLUDED_SETS
    ]
