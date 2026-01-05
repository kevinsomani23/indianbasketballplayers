import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from src.tournament_engine import run_tournament

def recover_data():
    ids = []
    cat_map = {}
    
    files = {
        "Men": "data/links/2025_75th_SN_Men_GameLinks.txt",
        "Women": "data/links/2025_75th_SN_Women_GameLinks.txt"
    }

    print("Reading link files...")
    for category, filepath in files.items():
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if "/match/" in line:
                        # Extract ID: .../match/2797387/preview?
                        try:
                            parts = line.split("/match/")
                            if len(parts) > 1:
                                mid = parts[1].split("/")[0]
                                if mid.isdigit():
                                    ids.append(mid)
                                    cat_map[mid] = category
                        except:
                            pass
                            
    print(f"Found {len(ids)} unique matches to recover from link files.")
    
    # Run Tournament Engine (re-scrapes or re-links)
    run_tournament(ids, category_map=cat_map)

if __name__ == "__main__":
    recover_data()
