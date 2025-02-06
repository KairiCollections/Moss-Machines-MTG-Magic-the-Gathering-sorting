import json
import os
from config import CARDS_JSON_PATH, EXCLUDED_SETS

CARDS_DATA = []
CARD_DATA_BY_ID = {}
if os.path.exists(CARDS_JSON_PATH):
    with open(CARDS_JSON_PATH, 'r', encoding='utf-8') as f:
        CARDS_DATA = json.load(f)
        CARD_DATA_BY_ID = {c['id']: c for c in CARDS_DATA} # Directly create the dictionary

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