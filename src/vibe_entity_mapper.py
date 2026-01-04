import json
import re

def build_map(raw_data_path):
    with open(raw_data_path, "r") as f:
        data = json.load(f)
    
    # 1. Official Map: (Team, Jersey) -> Name
    off_map = {}
    for p in data["OfficialPlayers"]:
        key = (p["Team"], p["Jersey"])
        off_map[key] = p["Name"]
        
    # 2. Extract PBP Entities and verify against Map
    mapping_report = []
    unmapped = []
    
    for row in data["RawPBPRows"]:
        desc = row["Description"]
        team = row["Team"]
        
        # Regex to find jersey in PBP: "5, Sahil Kalyan" or "5 Sahil Kalyan"
        # Usually "Number, Name" or "Number Name" at the start
        m = re.search(r"^(\d+)[\s,]+(.*?)(?:,|$)", desc)
        if m:
            p_jersey = m.group(1)
            p_raw_name = m.group(2).strip()
            
            key = (team, p_jersey)
            official_name = off_map.get(key, "MISSING")
            
            mapping_report.append({
                "PBP_Raw": f"{p_jersey}, {p_raw_name}",
                "Team": team,
                "Resolved": official_name
            })
            
            if official_name == "MISSING":
                unmapped.append(f"{team} #{p_jersey} {p_raw_name}")
        else:
            # Might be a team action or timeout
            pass
            
    return mapping_report, list(set(unmapped))

if __name__ == "__main__":
    report, missing = build_map("phase1_raw_data.json")
    
    print("\n--- PHASE 2: ENTITY MAPPING REPORT ---")
    print(f"Total Actions Mapped: {len(report)}")
    print(f"Unmapped Actions: {len(missing)}")
    
    if missing:
        print("\nUNMAPPED PLAYERS FOUND:")
        for m in missing:
            print(f"  ❌ {m}")
    else:
        print("\n✅ ALL PBP ACTIONS SUCCESSFULLY MAPPED TO OFFICIAL PLAYERS.")
        
    print("\nTop 5 Mappings:")
    for m in report[:5]:
        print(f"  {m['PBP_Raw']} ({m['Team']}) -> {m['Resolved']}")

    with open("phase2_mapping_report.json", "w") as f:
        json.dump({"report": report, "unmapped": missing}, f, indent=2)
