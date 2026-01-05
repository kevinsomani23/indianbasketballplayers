import sys
import os

# Add src to path
sys.path.append(os.path.abspath("src"))

from src.tournament_engine import run_tournament

def scrape_jan5():
    # Men's IDs (Excluding 2797635 from line 11)
    men_ids = ["2797632", "2797633", "2797634"]
    
    # Women's IDs (Excluding 2797639 from line 11)
    women_ids = ["2797636", "2797637", "2797638"]
    
    all_ids = men_ids + women_ids
    
    # Category Map
    cat_map = {}
    for mid in men_ids:
        cat_map[mid] = "Men"
    for mid in women_ids:
        cat_map[mid] = "Women"
        
    print(f"Scraping {len(all_ids)} matches for Jan 5th...")
    run_tournament(all_ids, category_map=cat_map)

if __name__ == "__main__":
    scrape_jan5()
