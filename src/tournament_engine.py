import json
import os
import pandas as pd
import time
from src.vibe_master_parser import VibeMasterParser

def run_tournament(match_ids, subfolder="75TH SN", category_map=None):
    data_path = "data/processed/data.json"
    if not os.path.exists("data/processed"):
        os.makedirs("data/processed")

    # Load existing data to support incremental scraping/skipping
    existing_ids = set()
    if os.path.exists(data_path):
        try:
            with open(data_path, "r") as f:
                all_data = json.load(f)
                existing_ids = {str(m.get("MatchID")) for m in all_data}
                print(f"Loaded {len(all_data)} existing matches from {data_path}")
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
            all_data = []
    else:
        all_data = []

    for idx, mid in enumerate(match_ids):
        # Sanitize ID
        mid = mid.strip().replace('\ufeff', '')
        if not mid: continue

        if mid in existing_ids:
            print(f"[{idx+1}/{len(match_ids)}] Skipping {mid} - Already scraped.")
            continue
        
        print(f"[{idx+1}/{len(match_ids)}] Running Master Parser for {mid}...")
        try:
            parser = VibeMasterParser(mid)
            p_stats, t_stats, meta, q_stats = parser.run()
            
            # Override Category if map provided
            if category_map and mid in category_map:
                meta["Category"] = category_map[mid]
                print(f"  > Overriding Category from Map: {meta['Category']}")
            
            # Add a small delay
            time.sleep(1.5)
            
            # Structure for Hub App
            meta["OfficialPlayers"] = parser.raw_data.get("OfficialPlayers", [])
            match_entry = {
                "MatchID": mid,
                "Category": meta.get("Category", "Unknown"),
                "Teams": meta.get("Teams", {}),
                "PlayerStats": p_stats,
                "TeamStats": t_stats,
                "PeriodStats": q_stats,
                "Metadata": meta
            }
            all_data.append(match_entry)
            
            # Save every 5 matches
            if (len(all_data)) % 5 == 0 or (idx + 1) == len(match_ids):
                with open(data_path, "w") as f:
                    json.dump(all_data, f, indent=2)
                print(f"  [Progress] Saved {len(all_data)} matches to {data_path}")
                
        except Exception as e:
            print(f"Error processing {mid}: {e}")
            continue
        
        # Create properly named folder: Date_TeamA_vs_TeamB_MatchID
        t1 = meta['Teams'].get('t1', 'TeamA').replace(' ', '_').replace('/', '_')
        t2 = meta['Teams'].get('t2', 'TeamB').replace(' ', '_').replace('/', '_')
        match_date = meta.get('MatchDate', 'Unknown').replace(' ', '_').replace('/', '_').replace(',', '')
        
        if subfolder:
            # Add Gender Category to path
            cat_dir = meta.get("Category", "Unknown")
            match_dir = f"matches/{subfolder}/{cat_dir}/{match_date}_{t1}_vs_{t2}_{mid}"
        else:
            match_dir = f"matches/{match_date}_{t1}_vs_{t2}_{mid}"
            
        if not os.path.exists(match_dir):
            os.makedirs(match_dir)
            
        # Create file name prefix
        file_prefix = f"{match_date}_{t1}_vs_{t2}_{mid}"
            
        # 1. PBP Rows
        pbp_df = pd.DataFrame(parser.raw_data.get("PBPRows", []))
        pbp_df.to_csv(f"{match_dir}/{file_prefix}_pbprows.csv", index=False)
            
        # 2. Box Score (Standard)
        std_cols = ["No", "Player", "Mins", "PTS", "FGM", "FGA", "FG%", "2PM", "2PA", "2P%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "BLKR", "PF", "FD", "2CP", "+/-", "Eff"]
        std_row_list = []
        for p_name, s in p_stats.items():
            row = {c: s.get(c, 0) for c in std_cols}
            row["Player"] = p_name
            # Rename for display
            display_row = {
                "No": s.get("No"), "Player": p_name, "Mins": s.get("Mins"), "Pts": s.get("PTS"),
                "FGM": s.get("FGM"), "FGA": s.get("FGA"), "FG%": s.get("FG%"), "2PM": s.get("2PM"), "2PA": s.get("2PA"), "2P%": s.get("2P%"),
                "3PM": s.get("3PM"), "3PA": s.get("3PA"), "3P%": s.get("3P%"), "FTM": s.get("FTM"), "FTA": s.get("FTA"), "FT%": s.get("FT%"),
                "OFF": s.get("OREB"), "DEF": s.get("DREB"), "REB": s.get("REB"), "AST": s.get("AST"), "TO": s.get("TOV"),
                "STL": s.get("STL"), "BLK": s.get("BLK"), "BLKR": s.get("BLKR"), "PF": s.get("PF"), "Fls on": s.get("FD"),
                "2CP": s.get("2CP"), "+/-": s.get("+/-"), "Eff": s.get("Eff")
            }
            std_row_list.append(display_row)
        pd.DataFrame(std_row_list).to_csv(f"{match_dir}/{file_prefix}_boxscore_standard.csv", index=False)
            
        # 3. Box Score (Advanced)
        adv_cols = ["PLAYER", "MIN", "OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", "AST RATIO", "OREB%", "DREB%", "REB%", "TO RATIO", "EFG%", "TS%", "USG%", "PACE", "PIE", "GmScr", "FIC"]
        adv_row_list = []
        for p_name, s in p_stats.items():
            adv_row_list.append({
                "PLAYER": p_name, "MIN": s.get("Mins"), "OFFRTG": s.get("OFFRTG"), "DEFRTG": s.get("DEFRTG"), "NETRTG": s.get("NETRTG"),
                "AST%": s.get("AST%"), "AST/TO": s.get("AST/TO"), "AST RATIO": s.get("AST RATIO"), "OREB%": s.get("OREB%"), "DREB%": s.get("DREB%"),
                "REB%": s.get("REB%"), "TO RATIO": s.get("TO RATIO"), "EFG%": s.get("eFG%"), "TS%": s.get("TS%"), "USG%": s.get("USG%"),
                "PACE": s.get("PACE"), "PIE": s.get("PIE"), "GmScr": s.get("GmScr"), "FIC": s.get("FIC")
            })
        pd.DataFrame(adv_row_list).to_csv(f"{match_dir}/{file_prefix}_boxscore_advanced.csv", index=False)
            
        # 4. Official Box Score (for validation)
        official_players = meta.get("OfficialPlayers", [])
        if official_players:
            pd.DataFrame(official_players).to_csv(f"{match_dir}/{file_prefix}_official_boxscore.csv", index=False)
            
        # 5. Advanced Team Stats
        team_rows = []
        for tk, t_vals in t_stats.items():
            row = t_vals.copy()
            row['TeamKey'] = tk
            row['TeamName'] = meta['Teams'].get(tk, tk)
            team_rows.append(row)
        pd.DataFrame(team_rows).to_csv(f"{match_dir}/{file_prefix}_advanced_team.csv", index=False)
            
        print(f"  - Match {mid} data exported to {match_dir}/ as CSV (Standard & Advanced)")
        
    with open(data_path, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"\nTournament data saved for {len(match_ids)} matches.")

if __name__ == "__main__":
    links_file = "all_game_links.txt"
    if os.path.exists(links_file):
        with open(links_file, "r") as f:
            # Read IDs, ignore empty lines
            match_ids = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(match_ids)} matches from {links_file}")
        run_tournament(match_ids)
    else:
        # Fallback to test matches if file not found
        print(f"{links_file} not found. Running test matches.")
        test_matches = ["2388522", "2389829", "2391613"]
        run_tournament(test_matches)
