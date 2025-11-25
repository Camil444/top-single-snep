
import json
import re
import os

CACHE_FILE = "../song_cache_v2.json"

def get_key(title, artist):
    """Normalise titre et artiste pour créer une clé unique"""
    title_clean = re.sub(r'[^\w\s]', '', title.lower().strip())
    artist_clean = re.sub(r'[^\w\s]', '', artist.lower().strip())
    return f"{title_clean}|{artist_clean}"

if not os.path.exists(CACHE_FILE):
    print(f"File not found: {CACHE_FILE}")
    exit(1)

with open(CACHE_FILE, 'r', encoding='utf-8') as f:
    cache = json.load(f)

print(f"Cache size: {len(cache)}")

# Test case from logs
title = "NE REVIENS PAS"
artist = "GRADUR"
key = get_key(title, artist)
print(f"Generated key: '{key}'")

if key in cache:
    print("✅ Found in cache")
else:
    print("❌ Not found in cache")
    # Try to find partial matches
    for k in cache.keys():
        if "ne reviens pas" in k:
            print(f"Partial match: '{k}'")
