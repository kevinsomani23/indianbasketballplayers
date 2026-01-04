import json
import os

print("--- DIAGNOSTIC START ---")

try:
    with open("data/raw/match_category_map.json", "r", encoding='utf-8-sig') as f:
        cmap = json.load(f)
        print(f"Category Map Loaded: {len(cmap)} entries")
        print(f"2797383 -> {cmap.get('2797383')}")
        print(f"2797392 -> {cmap.get('2797392')}")
except Exception as e:
    print(f"Error loading category map: {e}")
    cmap = {}

try:
    with open("data/processed/data.json", "r", encoding='utf-8-sig') as f:
        data = json.load(f)
        print(f"Data Loaded: {len(data)} matches")
        
        target_ids = ["2797383", "2797392"]
        
        for m in data:
            mid = str(m.get("MatchID"))
            if mid in target_ids:
                print(f"\nMatch {mid}:")
                # Simulate the category merge logic
                cat_original = m.get("Category")
                cat_merged = cmap.get(mid, cat_original)
                
                t1 = m['Teams']['t1']
                t2 = m['Teams']['t2']
                
                print(f"  Category (Original): {cat_original}")
                print(f"  Category (Merged):   {cat_merged}")
                print(f"  Teams: '{t1}' vs '{t2}'")
                print(f"  Scores: {m['TeamStats']['t1']['PTS']} - {m['TeamStats']['t2']['PTS']}")
                
                # Check label generation key
                label = f"{t1} vs {t2} ({cat_merged})"
                print(f"  Generated Label: '{label}'")

except Exception as e:
    print(f"Error loading data: {e}")

print("--- DIAGNOSTIC END ---")
