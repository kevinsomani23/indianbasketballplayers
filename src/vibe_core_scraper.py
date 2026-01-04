import requests
from bs4 import BeautifulSoup
import json
import os

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def scrape_raw(match_id):
    print(f"Phase 1: Scraping Match {match_id}...")
    urls = {
        "box": f"https://hosted.dcd.shared.geniussports.com/BIF/en/competition/37654/match/{match_id}/boxscore?",
        "pbp": f"https://hosted.dcd.shared.geniussports.com/BIF/en/competition/37654/match/{match_id}/playbyplay?"
    }
    
    data = {"MatchID": match_id, "OfficialPlayers": [], "RawPBPRows": []}
    
    # 1. Box Score (The source of truth for names/jerseys)
    r_box = requests.get(urls['box'], headers=HEADERS, verify=False)
    soup_box = BeautifulSoup(r_box.text, 'html.parser')
    
    t1_name = soup_box.select_one(".home-wrapper .name a").get_text(strip=True) if soup_box.select_one(".home-wrapper .name a") else "Home"
    t2_name = soup_box.select_one(".away-wrapper .name a").get_text(strip=True) if soup_box.select_one(".away-wrapper .name a") else "Away"
    data["Teams"] = {"t1": t1_name, "t2": t2_name}

    tables = soup_box.select("table.footable")
    for i, table in enumerate(tables):
        team_label = "t1" if i == 0 else "t2"
        headers = [th.get_text(strip=True) for th in table.select("thead th")]
        for row in table.select("tbody tr"):
            cells = row.select("td")
            if len(cells) < 2: continue
            
            p_stats = {"Team": team_label}
            for j, cell in enumerate(cells):
                h = headers[j] if j < len(headers) else f"col_{j}"
                p_stats[h] = cell.get_text(strip=True)
                
            data["OfficialPlayers"].append(p_stats)
            
    # 2. PBP (The raw events)
    r_pbp = requests.get(urls['pbp'], headers=HEADERS, verify=False)
    soup_pbp = BeautifulSoup(r_pbp.text, 'html.parser')
    
    events = soup_pbp.select("div.pbpa")
    for ev in events:
        cls = ev.get('class', [])
        acting_team = "t1" if "pbp-t1" in cls or "pbpt1" in cls else ("t2" if "pbp-t2" in cls or "pbpt2" in cls else "Other")
        
        clock_el = ev.find(class_="pbp-time")
        desc_el = ev.find(class_="pbp-action")
        
        if not clock_el or not desc_el: continue
        
        # Period detection
        period = 1
        has_specific = False
        for c in cls:
            if c.startswith("per_") and c[4:].isdigit():
                try:
                    period = int(c[4:])
                    has_specific = True
                except: pass
            elif c == "per_reg" and not has_specific:
                period = 4 # Fallback
                
        data["RawPBPRows"].append({
            "Classes": cls,
            "Team": acting_team,
            "Clock": clock_el.get_text(strip=True),
            "Period": period,
            "Description": desc_el.get_text(strip=True)
        })

    # 3. Summary (Official Advanced Comparison)
    sum_url = f"https://hosted.dcd.shared.geniussports.com/BIF/en/competition/37654/match/{match_id}/summary"
    try:
        r_sum = requests.get(sum_url, headers=HEADERS, timeout=10, verify=False)
        soup_sum = BeautifulSoup(r_sum.text, 'html.parser')
        
        sum_stats = {t1_name: {}, t2_name: {}}
        comp_rows = soup_sum.select("#BLOCK_SUMMARY_COMPARE .summary-compare-detail")
        key_map = {
            "points in the paint": "PITP",
            "fast break points": "FBPS",
            "points from turnovers": "OFF TO",
            "second chance points": "2ND PTS",
            "bench points": "PTS_Bench"
        }
        for row in comp_rows:
            label_el = row.select_one(".fieldName")
            if not label_el: continue
            label = label_el.get_text(strip=True).lower()
            if label in key_map:
                k = key_map[label]
                h_val = row.select_one(".fieldHomeStatNumber").get_text(strip=True)
                a_val = row.select_one(".fieldAwayStatNumber").get_text(strip=True)
                sum_stats[t1_name][k] = h_val
                sum_stats[t2_name][k] = a_val
        data["OfficialSummary"] = sum_stats
    except:
        data["OfficialSummary"] = {}
        
    return data

if __name__ == "__main__":
    raw_data = scrape_raw("2391613")
    print(f"\n--- PHASE 1 VERIFICATION ---")
    print(f"Official Players Found: {len(raw_data['OfficialPlayers'])}")
    print(f"PBP Rows Extracted: {len(raw_data['RawPBPRows'])}")
    
    # Show first few players
    print("\nFirst 5 Official Players:")
    for p in raw_data['OfficialPlayers'][:5]:
        print(f"  #{p.get('No','?')} {p.get('Player','Unknown')}")
        
    # Save for user inspect
    with open("phase1_raw_data.json", "w") as f:
        json.dump(raw_data, f, indent=2)
    print("\nFull raw data saved to phase1_raw_data.json")
