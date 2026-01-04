import json
from src.vibe_master_parser import VibeMasterParser

def verify_match(match_id):
    parser = VibeMasterParser(match_id)
    p_stats, t_stats, meta = parser.run()
    
    # Official Box Score is stored in raw_data['OfficialPlayers']
    official_players = parser.raw_data.get("OfficialPlayers", [])
    
    print(f"\n--- PLAYER-LEVEL AUDIT ---")
    metrics = ["Pts", "REB", "AST", "STL", "BLK", "TO"]
    key_map = {"Pts": "PTS", "REB": "REB", "AST": "AST", "STL": "STL", "BLK": "BLK", "TO": "TOV"}
    
    total_diffs = 0
    mismatched_players = []
    for off_p in official_players:
        name = off_p.get("Player", "Unknown")
        der_p = p_stats.get(name, {})
        for m_off in metrics:
            v_off = int(off_p.get(m_off, 0))
            v_der = int(der_p.get(key_map[m_off], 0))
            if v_off != v_der:
                total_diffs += abs(v_der - v_off)
                if name not in mismatched_players: mismatched_players.append(name)

    if total_diffs == 0:
        print("VERIFICATION: SUCCESS - All 24 Players Match 100% with Official Box Score.")
    else:
        print(f"VERIFICATION: FAILED - {total_diffs} stat diffs found for: {', '.join(mismatched_players)}")
        
    # Team Totals Check
    print(f"\n{'='*40}")
    print("TEAM TOTALS CHECK")
    print(f"{'='*40}")
    for tk in ["t1", "t2"]:
        name = meta["Teams"][tk]
        off_pts = sum(int(p.get("Pts", 0)) for p in official_players if p["TeamKey"] == tk)
        der_pts = t_stats[tk]["PTS"]
        print(f"{name:<20}: PBP={der_pts}, Official={off_pts} | Match={'OK' if der_pts==off_pts else 'MISMATCH'}")

if __name__ == "__main__":
    verify_match("2391613")
