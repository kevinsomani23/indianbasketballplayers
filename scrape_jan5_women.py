import sys
import os

# Add src to path
sys.path.append(os.path.abspath("src"))

from src.tournament_engine import run_tournament

def scrape_jan5_women():
    # Women's IDs (Excluding 2797639 from line 11)
    women_ids = ["2797636", "2797637", "2797638"]
    
    # Category Map
    cat_map = {}
    for mid in women_ids:
        cat_map[mid] = "Women"
        
    print(f"Scraping {len(women_ids)} Women's matches for Jan 5th...")
    run_tournament(women_ids, category_map=cat_map)

if __name__ == "__main__":
    scrape_jan5_women()
