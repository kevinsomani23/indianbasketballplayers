import pandas as pd
import json
import os

# Data extracted manually from the "Day 1 Results" image
IMAGE_DATA = [
    {"num": 1, "t1": "INDIAN RAILWAYS", "t2": "DELHI", "g": "WOMEN", "s1": 101, "s2": 51},
    {"num": 2, "t1": "KERALA", "t2": "GUJARAT", "g": "WOMEN", "s1": 91, "s2": 22},
    {"num": 3, "t1": "KARNATAKA", "t2": "GUJARAT", "g": "MEN", "s1": 104, "s2": 69},
    {"num": 4, "t1": "PUNJAB", "t2": "UTTAR PRADESH", "g": "MEN", "s1": 100, "s2": 112},
    {"num": 5, "t1": "MAHARASHTRA", "t2": "KARNATAKA", "g": "WOMEN", "s1": 71, "s2": 91},
    {"num": 6, "t1": "TAMIL NADU", "t2": "MADHYA PRADESH", "g": "WOMEN", "s1": 72, "s2": 65},
    {"num": 7, "t1": "TAMIL NADU", "t2": "RAJASTHAN", "g": "MEN", "s1": 101, "s2": 68},
    {"num": 8, "t1": "INDIAN RAILWAYS", "t2": "DELHI", "g": "MEN", "s1": 101, "s2": 78},
    
    {"num": 9, "t1": "KERALA", "t2": "WEST BENGAL", "g": "MEN", "s1": 80, "s2": 79},
    {"num": 10, "t1": "MADHYA PRADESH", "t2": "UTTARAKHAND", "g": "MEN", "s1": 108, "s2": 45},
    {"num": 11, "t1": "PUNJAB", "t2": "UTTARAKHAND", "g": "WOMEN", "s1": 72, "s2": 28},
    {"num": 12, "t1": "UTTAR PRADESH", "t2": "TELANGANA", "g": "WOMEN", "s1": 42, "s2": 41},
    {"num": 13, "t1": "HIMACHAL PRADESH", "t2": "PUDUCHERRY", "g": "WOMEN", "s1": 52, "s2": 64},
    {"num": 14, "t1": "ANDHRA PRADESH", "t2": "ASSAM", "g": "WOMEN", "s1": 43, "s2": 58},
    {"num": 15, "t1": "MEGHALAYA", "t2": "ODISHA", "g": "WOMEN", "s1": 56, "s2": 44},
    
    {"num": 16, "t1": "BIHAR", "t2": "MIZORAM", "g": "MEN", "s1": 68, "s2": 60},
    {"num": 17, "t1": "HIMACHAL PRADESH", "t2": "TELANGANA", "g": "MEN", "s1": 72, "s2": 73},
    {"num": 18, "t1": "ANDAMAN & NICOBAR", "t2": "SIKKIM", "g": "MEN", "s1": 32, "s2": 60},
    {"num": 19, "t1": "ASSAM", "t2": "NAGALAND", "g": "MEN", "s1": 50, "s2": 41},
    {"num": 20, "t1": "ANDHRA PRADESH", "t2": "PUDUCHERRY", "g": "MEN", "s1": 79, "s2": 67},
    {"num": 21, "t1": "ARUNACHAL PRADESH", "t2": "ODISHA", "g": "MEN", "s1": 39, "s2": 115},
    {"num": 22, "t1": "RAJASTHAN", "t2": "SIKKIM", "g": "WOMEN", "s1": 58, "s2": 35},
    
    {"num": 23, "t1": "JAMMU & KASHMIR", "t2": "JHARKHAND", "g": "MEN", "s1": 69, "s2": 71},
    {"num": 24, "t1": "GOA", "t2": "MAHARASHTRA", "g": "MEN", "s1": 67, "s2": 68},
    {"num": 25, "t1": "CHHATTISGARH", "t2": "MEGHALAYA", "g": "MEN", "s1": 73, "s2": 48},
    {"num": 26, "t1": "HARYANA", "t2": "TRIPURA", "g": "MEN", "s1": 98, "s2": 22},
    {"num": 27, "t1": "BIHAR", "t2": "JHARKHAND", "g": "WOMEN", "s1": 48, "s2": 12},
    {"num": 28, "t1": "HARYANA", "t2": "GOA", "g": "WOMEN", "s1": 45, "s2": 35},
    {"num": 29, "t1": "ARUNACHAL PRADESH", "t2": "MANIPUR", "g": "WOMEN", "s1": 44, "s2": 15},
]

def normalize_name(n):
    return str(n).strip().upper().replace("  ", " ")

def run_update():
    # Load Schedule
    try:
        df_sch = pd.read_csv("compiled_schedule.csv")
    except:
        print("Could not load compiled_schedule.csv")
        return

    # Load Scores
    scores_path = "data/processed/manual_scores.json"
    if os.path.exists(scores_path):
        with open(scores_path, "r") as f:
            scores = json.load(f)
    else:
        scores = {}

    exact_matches = 0
    fuzzy_matches = 0
    missing_matches = 0
    
    # Iterate Image Data
    for item in IMAGE_DATA:
        t1 = normalize_name(item['t1'])
        t2 = normalize_name(item['t2'])
        cat = normalize_name(item['g'])
        
        match_found = None
        match_type = None # "exact" or "fuzzy"
        
        # 1. Try Exact Match
        for idx, row in df_sch.iterrows():
            rt1 = normalize_name(row['Team A'])
            rt2 = normalize_name(row['Team B'])
            rg = normalize_name(row['Gender'])
            
            if rg == cat:
                if (rt1 == t1 and rt2 == t2) or (rt1 == t2 and rt2 == t1):
                    match_found = row
                    match_type = "exact"
                    break
        
        # 2. Try Fuzzy Match (Ignore Gender)
        if match_found is None:
            for idx, row in df_sch.iterrows():
                rt1 = normalize_name(row['Team A'])
                rt2 = normalize_name(row['Team B'])
                # ry ignoring gender
                if (rt1 == t1 and rt2 == t2) or (rt1 == t2 and rt2 == t1):
                    match_found = row
                    match_type = "fuzzy (gender mismatch)"
                    break
        
        if match_found is not None:
            # Found in schedule. Key by the SCHEDULE'S keys so it actually shows up.
            s_t1 = str(match_found['Team A']).strip().upper()
            s_t2 = str(match_found['Team B']).strip().upper()
            s_gen = str(match_found['Gender']).strip().upper()
            
            # The app likely constructs the key as T1_VS_T2_GENDER 
            # We should probably also insert the REVERSE key to be safe, 
            # or rely on the app checking both. The app checks T1_VS_T2 then T2_VS_T1.
            
            # Key using CSV names
            k1 = f"{s_t1}_VS_{s_t2}_{s_gen}"
            
            # Always update score
            scores[k1] = {
                "s1": item['s1'], # Careful: if teams are swapped in CSV vs Image?
                "s2": item['s2'],
                "id": str(match_found['Match ID'])
            }
            
            # Handle Team Swapping for Scores
            # If CSV has T2 vs T1, we should conceptually map score s1 to T1 and s2 to T2.
            # But here we just dump s1/s2.
            # Let's be precise:
            # Image: T1 score s1, T2 score s2.
            # CSV: matches T1 vs T2. -> s1 is s1.
            # CSV: matches T2 vs T1. -> s1 (Image T1) is actually the "second" team score for that key?
            # Actually, `manual_scores` stores "s1" and "s2".
            # If the Key is T1_VS_T2, then "s1" corresponds to T1.
            # So we must ensure k1 is built such that the first team in the key gets s1.
            
            # Currently k1 = s_t1_VS_s_t2
            # If s_t1 corresponds to item['t1'], then scores['s1'] should be item['s1'].
            # If s_t1 corresponds to item['t2'], then scores['s1'] should be item['s2'].
            
            is_swapped = False
            if normalize_name(s_t1) == t2:
                is_swapped = True
                
            if is_swapped:
                scores[k1]['s1'] = item['s2']
                scores[k1]['s2'] = item['s1']
            else:
                scores[k1]['s1'] = item['s1']
                scores[k1]['s2'] = item['s2']

            if match_type == "exact":
                exact_matches += 1
                print(f"✅ Exact Match: Image #{item['num']} mapped to CSV ID {match_found['Match ID']} ({s_t1} vs {s_t2})")
            else:
                fuzzy_matches += 1
                print(f"⚠️ Fuzzy Match: Image #{item['num']} mapped to CSV ID {match_found['Match ID']} ({s_t1} vs {s_t2} - {s_gen})")
                
        else:
            missing_matches += 1
            print(f"❌ No Match: Image #{item['num']} ({t1} vs {t2}) NOT found in CSV.")
            # Still add to scores for completeness, using Image Key
            k_img = f"{t1}_VS_{t2}_{cat}"
            scores[k_img] = {
                "s1": item['s1'],
                "s2": item['s2'],
                "id": f"IMG_{item['num']}"
            }

    # Save
    with open(scores_path, "w") as f:
        json.dump(scores, f, indent=2)
        
    print(f"\nSummary:\nExact Matches: {exact_matches}\nFuzzy Matches: {fuzzy_matches}\nMissing Matches: {missing_matches}")

if __name__ == "__main__":
    run_update()
