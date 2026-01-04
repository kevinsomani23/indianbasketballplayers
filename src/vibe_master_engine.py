import json
import re

def _get_abs_time(period, clock_str):
    try:
        pts = clock_str.split(":")
        m, s = int(pts[0]), int(pts[1])
        return (period - 1) * 600 + (600 - (m * 60 + s))
    except: return 0

def _is_paint(desc):
    d = desc.lower()
    return any(k in d for k in ["layup", "lay up", "dunk", "tip-in", "hook", "driving", "putback"])

def sum_stats(raw_data_path, mapping_path):
    with open(raw_data_path, "r") as f:
        raw = json.load(f)
    with open(mapping_path, "r") as f:
        mapping = json.load(f)["report"]
        
    map_dict = {entry["PBP_Raw"]: entry["Resolved"] for entry in mapping}
    player_stats = {}
    team_stats = {t: {"PITP":0, "FBPS":0, "OFF TO":0, "2ND PTS":0} for t in ["t1", "t2"]}
    
    mstate = {
        "t1": {"last_oreb_time": -99, "last_tov_opp_time": -99, "trans_time": -99},
        "t2": {"last_oreb_time": -99, "last_tov_opp_time": -99, "trans_time": -99}
    }
    
    official = {p["Player"]: p for p in raw["OfficialPlayers"]}
    logs = []
    
    for row in raw["RawPBPRows"]:
        desc = row["Description"]
        cls = row["Classes"]
        team = row["Team"]
        if team == "Other": continue
        opp = "t2" if team == "t1" else "t1"
        clock = row["Clock"]
        abs_time = _get_abs_time(row["Period"], clock)
        
        # State Updates
        if "pbptyturnover" in cls: mstate[opp]["last_tov_opp_time"] = abs_time
        if "pbptyrebound" in cls and "offensive" in desc.lower(): mstate[team]["last_oreb_time"] = abs_time
        if "pbptysteal" in cls: mstate[team]["trans_time"] = abs_time
        if "pbptyrebound" in cls and "defensive" in desc.lower(): mstate[team]["trans_time"] = abs_time

        # Player Extraction
        m = re.search(r"^(\d+)[\s,]+(.*?)(?:,|$)", desc)
        if not m: continue
        
        p_id = f"{m.group(1)}, {m.group(2).strip()}"
        res_name = map_dict.get(p_id)
        if not res_name or res_name == "MISSING": continue
        
        if res_name not in player_stats:
            player_stats[res_name] = {"PTS":0, "REB":0, "AST":0, "STL":0, "BLK":0, "TOV":0}
        
        s = player_stats[res_name]
        made = "pbpmade" in cls or ("made" in desc.lower() and "miss" not in desc.lower())
        pts = 0
        if made:
            if "pbpty3pt" in cls: pts = 3
            elif "pbptyfreethrow" in cls: pts = 1
            else: pts = 2
            
            s["PTS"] += pts
            
            if pts > 1:
                # PITP
                if _is_paint(desc): 
                    team_stats[team]["PITP"] += pts
                    logs.append(f"[{clock}] {team} PITP: {desc}")
                
                # 2ND PTS (4s)
                if (abs_time - mstate[team]["last_oreb_time"]) <= 4:
                    team_stats[team]["2ND PTS"] += pts
                    logs.append(f"[{clock}] {team} 2ND_PTS: {desc}")
                    mstate[team]["last_oreb_time"] = -99
                
                # OFF TO (8s)
                if (abs_time - mstate[team]["last_tov_opp_time"]) <= 8:
                    team_stats[team]["OFF TO"] += pts
                    logs.append(f"[{clock}] {team} OFF_TO: {desc}")
                    mstate[team]["last_tov_opp_time"] = -99
                    
                # FBPS (5s)
                if (abs_time - mstate[team]["trans_time"]) <= 5 or "fast break" in desc.lower():
                    team_stats[team]["FBPS"] += pts
                    logs.append(f"[{clock}] {team} FBPS: {desc}")
                    mstate[team]["trans_time"] = -99

        if not made:
            if "pbptyrebound" in cls: s["REB"] += 1
            if "pbptyassist" in cls: s["AST"] += 1
            if "pbptysteal" in cls: s["STL"] += 1
            if "pbptyblock" in cls: s["BLK"] += 1
            if "pbptyturnover" in cls: s["TOV"] += 1

    return player_stats, official, team_stats, raw.get("OfficialSummary", {}), raw.get("Teams", {}), logs

if __name__ == "__main__":
    derived, official, t_der, t_off, t_names, logs = sum_stats("phase1_raw_data.json", "phase2_mapping_report.json")
    
    print("\n--- PHASE 4 AUDIT ---")
    for tk in ["t1", "t2"]:
        n = t_names.get(tk, tk)
        o = t_off.get(n, {})
        d = t_der[tk]
        print(f"Team: {n}")
        for m in ["PITP", "FBPS", "OFF TO", "2ND PTS"]:
            ov = int(o.get(m, 0))
            dv = d[m]
            print(f"  {m:10}: Derived={dv:<5} Official={ov:<5} Diff={dv-ov}")

    print("\nSample Attribution Log (Last 10):")
    for l in logs[-10:]: print(l)
