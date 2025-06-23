import json
import cv2

def print_sorting_options():
    print("Choose your sorting method:")
    print("1 - Color:")
    print("2 - CMC:")
    print("3 - Set:")
    print("4 - Price:")
    print("5 - Type:")
    print("6 - Buy mode:")
    print()

def draw_info_as_json(frame, info, start_x=10, start_y=30, line_height=20):
    json_str = json.dumps(info, indent=2)
    lines = json_str.split('\n')
    for i, line in enumerate(lines):
        y = start_y + i * line_height
        cv2.putText(frame, line, (start_x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

# Functions for determining the bin number based on card attributes
def is_basic_land(name):
    return name.lower() in {"plains", "island", "swamp", "mountain", "forest", "wastes"}  # Use a set

def is_land_card(types):
    return "land" in types

def get_bin_color(info):  # More descriptive name
    types = info.get("Types", [])
    if is_land_card(types):
        return "Basic land" if is_basic_land(info.get("Name", "")) else "Nonbasic land"  # Ternary operator
    colors = info.get("Colors", [])
    if not colors:
        return "Colorless"
    return "Multicolor" if len(colors) > 1 else colors[0] or "Colorless"  # Simplified multicolor/color logic


def get_bin_mana(info):
    mv = info.get("CMC", 0)
    if mv <= 1: return "One"
    elif mv <= 8: return str(mv).capitalize() # Simplified for mana values 1-8
    else: return "RejectCard"  # Consistent rejection

def get_bin_set(info):
    set_code = info.get("Set", "???").lower()
    types = info.get("Types", [])
    return "token" if "token" in types else set_code or "RejectCard"

def get_bin_price(info, threshold):
    price_str = info.get("Price", "null")
    if price_str == "null":
        return "RejectCard"
    try:
        price = float(price_str.strip('$'))
    except (ValueError, TypeError): # Catch both value error and type error
        return "RejectCard"

    # Price binning (can be further simplified if needed)
    bins = { # Dictionary for price ranges and bins
        0.02: "tray1",
        0.05: "tray7",
        0.10: "tray14",
        0.25: "tray18",
        0.50: "tray21",
        1.0: "tray24",
        2.0: "tray25",
        4.0: "tray26",
        8.0: "tray27",
        16.0: "tray28",
        32.0: "tray29",
        64.0: "tray30",
        128.0: "tray31",
        float('inf'): "tray32" # Infinity for the upper limit
    }
    for upper_limit, bin_name in bins.items():
        if price <= upper_limit and price <= threshold:
            return bin_name
    return "RejectCard"

def get_bin_type(info):
    types = info.get("Types", [])
    type_mapping = {  # Type mapping for bins
        "creature": "creature","artifact": "artifact","enchantment": "enchantment","instant": "instant","sorcery": "sorcery",
        "battle": "battle","planeswalker": "planeswalker","land": "land","token": "token"
    }
    for card_type in types:
        if card_type in type_mapping:
            return type_mapping[card_type]
    return "RejectCard"

def get_bin_number(info, mode, threshold):
    if not info:
        return "RejectCard"  # Error bin
    if info == "RejectCard":
        return "Rejectcard"
    elif mode == "color":
        return get_bin_color(info)
    elif mode == "mana_value":
        return get_bin_mana(info)
    elif mode == "set":
        return get_bin_set(info)
    elif mode == "price":
        return get_bin_price(info,1000000)
    elif mode == "type":
        return get_bin_type(info)
    elif mode == "buy":
        return get_bin_price(info,threshold)
    else:
        return "RejectCard"

def get_mana_cost(info):
    cost = info.get("Mana Cost", "???").upper()
    return cost.replace("{", "").replace("}", "")  # Chained replace

def get_promo(info):
    return info.get("Promo")  
    
def get_name(info):
    return info.get("Name", "???") 
