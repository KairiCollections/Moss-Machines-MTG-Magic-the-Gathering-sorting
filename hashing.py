import json
import os
import imagehash
from config import HASH_DB_PATH

HASH_DB = {}
if os.path.exists(HASH_DB_PATH):
    with open(HASH_DB_PATH, 'r', encoding='utf-8') as f:
        HASH_DB = json.load(f)

PRECOMPUTED_HASHES = []
for card_id, h in HASH_DB.items():
    r_phash = h.get('r_phash')
    g_phash = h.get('g_phash')
    b_phash = h.get('b_phash')
    if all([r_phash, g_phash, b_phash]):
        try:
            r = imagehash.hex_to_hash(r_phash)
            g = imagehash.hex_to_hash(g_phash)
            b = imagehash.hex_to_hash(b_phash)
            PRECOMPUTED_HASHES.append((card_id, r, g, b))
        except ValueError:
            print(f"Invalid hash for card {card_id}. Skipping.")

def hash_image_color(img, hash_size=16):
    img = img.convert('RGB')
    r, g, b = img.split()
    r_hash = imagehash.phash(r, hash_size)
    g_hash = imagehash.phash(g, hash_size)
    b_hash = imagehash.phash(b, hash_size)
    best_match_id = None
    min_distance = float('inf')
    for card_id, stored_r, stored_g, stored_b in PRECOMPUTED_HASHES:
        r_dist = r_hash - stored_r
        g_dist = g_hash - stored_g
        b_dist = b_hash - stored_b
        avg_dist = (r_dist + g_dist + b_dist) / 3.0
        if avg_dist < min_distance:
            min_distance = avg_dist
            best_match_id = card_id
    return best_match_id, min_distance

def compute_distances_for_image(img, hash_size=16):
    img = img.convert('RGB')
    r, g, b = img.split()
    r_hash = imagehash.phash(r, hash_size)
    g_hash = imagehash.phash(g, hash_size)
    b_hash = imagehash.phash(b, hash_size)
    distances = []
    for card_id, stored_r, stored_g, stored_b in PRECOMPUTED_HASHES:
        r_dist = r_hash - stored_r
        g_dist = g_hash - stored_g
        b_dist = b_hash - stored_b
        avg_dist = (r_dist + g_dist + b_dist) / 3.0
        distances.append((card_id, avg_dist))
    return distances