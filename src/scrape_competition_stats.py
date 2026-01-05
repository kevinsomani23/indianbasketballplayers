import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
import urllib3
import sys

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def scrape_url_to_csv(url, output_name, category):
    print(f"Scraping {category} stats from {url}...")
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables:
            print(f"❌ No tables found for {category}")
            return
            
        # Usually multiple tables (Average, Shooting, Total). 
        # We want to save all of them or combine them.
        # Let's save each table found with a suffix.
        
        save_dir = f"data/competition_stats/{category}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        print(f"  Found {len(tables)} tables.")
        
        for idx, table in enumerate(tables):
            # Parse table
            # Pandas read_html is easiest if simple structure
            try:
                dfs = pd.read_html(str(table))
                if dfs:
                    df = dfs[0]
                    # Clean columns
                    table_name = f"Table_{idx+1}"
                    # Check headers to guess type
                    if "PTS" in df.columns: table_name = "Stats"
                    
                    csv_path = f"{save_dir}/{output_name}_{table_name}.csv"
                    df.to_csv(csv_path, index=False)
                    print(f"  ✅ Saved {csv_path} ({len(df)} rows)")
            except Exception as e:
                print(f"  ⚠️ Error parsing table {idx}: {e}")

    except Exception as e:
        print(f"❌ Critical Error fetching {url}: {e}")

def run_stats_scrape():
    # Men's Player Stats
    men_url = "https://hosted.dcd.shared.geniussports.com/BIF/en/competition/48039/statistics/player?"
    scrape_url_to_csv(men_url, "Men_Player_Stats", "Men")
    
    # Women's Team Stats
    women_url = "https://hosted.dcd.shared.geniussports.com/BIF/en/competition/48040/statistics/team?"
    scrape_url_to_csv(women_url, "Women_Team_Stats", "Women")

if __name__ == "__main__":
    run_stats_scrape()
