import json

with open('data/processed/data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Checking Karnataka Players:")
for m in data:
    mid = m.get("MatchID")
    teams = m.get("Teams", {}).values()
    if "Karnataka" in teams:
        print(f"\nMatch {mid}:")
        for p, s in m.get("PlayerStats", {}).items():
            if s.get("Team") == "Karnataka":
                print(f"  {p}: No='{s.get('No')}' (PTS: {s.get('PTS')})")
