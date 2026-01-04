import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

class VibeMasterParser:
    """
    Foolproof PBP Parser for Senior Nationals.
    Combines Scraping, Mapping, and Heuristic Rectification.
    """
    
    def __init__(self, match_id):
        self.match_id = match_id
        # Try Men's ID (37654) by default, but we'll probe for Women's (37658) if needed
        # Try 75th SN IDs (48039: Men, 48040: Women) first, then legacy
        self.comp_ids = ["48039", "48040", "37654", "37658"] 
        self.active_comp_id = "37654"
        self._set_urls(self.active_comp_id)

        self.raw_data = {}
        self.player_map = {} # (team_key, jersey) -> Official Name
        self.player_stats = {}
        self.period_stats = {} # period -> player_name -> stats
        self.team_stats = {"t1": {"PTS":0, "PITP":0, "FBPS":0, "OFF TO":0, "2ND PTS":0}, 
                          "t2": {"PTS":0, "PITP":0, "FBPS":0, "OFF TO":0, "2ND PTS":0}}
        self.metadata = {}

    def _set_urls(self, cid):
        self.urls = {
            "box": f"https://hosted.dcd.shared.geniussports.com/BIF/en/competition/{cid}/match/{self.match_id}/boxscore?",
            "pbp": f"https://hosted.dcd.shared.geniussports.com/BIF/en/competition/{cid}/match/{self.match_id}/playbyplay?",
            "sum": f"https://hosted.dcd.shared.geniussports.com/BIF/en/competition/{cid}/match/{self.match_id}/summary"
        }

    def run(self):
        print(f"Running Master Parser for {self.match_id}...")
        self._scrape_all()
        self._build_player_map()
        self._process_pbp()
        self._track_minutes()
        self._calculate_advanced_player_metrics()
        self._calculate_team_metrics()
        return self.player_stats, self.team_stats, self.metadata, self.period_stats

    def _fetch(self, url, retries=3, delay=2):
        """Robust fetch with retries and backoff."""
        for i in range(retries):
            try:
                r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
                r.raise_for_status()
                return r
            except Exception as e:
                print(f"  [Retry {i+1}/{retries}] Error fetching {url}: {e}")
                if i < retries - 1:
                    time.sleep(delay * (i + 1))
        # Final attempt
        return requests.get(url, headers=HEADERS, verify=False, timeout=20)

    def _scrape_all(self):
        # 1. Box Score (Ground Truth for Names/Team Labels)
        # Loop through competition IDs until we find a valid one
        found = False
        for cid in self.comp_ids:
            self.active_comp_id = cid
            self._set_urls(cid)
            try:
                r_box = self._fetch(self.urls['box'])
                soup_box = BeautifulSoup(r_box.text, 'html.parser')
                
                # Validation check: Can we find team names?
                t1 = soup_box.select_one(".home-wrapper .name a")
                t2 = soup_box.select_one(".away-wrapper .name a")
                
                if t1 and t2:
                    print(f"  > Valid competition ID found: {cid}")
                    found = True
                    break
                else:
                    print(f"  > Invalid competition ID {cid} (Names not found), retrying...")
            except Exception as e:
                print(f"  > Error with ID {cid}: {e}")
        
        if not found:
            print("  ! CRITICAL: Could not find valid data with any Competition ID. default to 37654")
            self._set_urls("37654")
            # Re-fetch for safety, though it likely failed
            r_box = self._fetch(self.urls['box'])
            soup_box = BeautifulSoup(r_box.text, 'html.parser')

        t1_name = soup_box.select_one(".home-wrapper .name a").get_text(strip=True) if soup_box.select_one(".home-wrapper .name a") else "Home"
        t2_name = soup_box.select_one(".away-wrapper .name a").get_text(strip=True) if soup_box.select_one(".away-wrapper .name a") else "Away"
        self.metadata["Teams"] = {"t1": t1_name, "t2": t2_name}
        
        # Scrape Category from League Header
        # Format: "75th Senior National... - Men"
        cat_header = soup_box.select_one(".leagueHeader h3")
        if cat_header:
            header_text = cat_header.get_text(strip=True)
            if "Men" in header_text and "Women" not in header_text:
                self.metadata["Category"] = "Men"
            elif "Women" in header_text:
                self.metadata["Category"] = "Women"
            else:
                self.metadata["Category"] = "Unknown"
        else:
            self.metadata["Category"] = "Unknown"
            print("  ! Warning: Could not find League Header for Category")
        
        players = []
        tables = soup_box.select("table.footable")
        for i, table in enumerate(tables):
            team_key = "t1" if i == 0 else "t2"
            headers = [th.get_text(strip=True) for th in table.select("thead th")]
            for row in table.select("tbody tr"):
                cells = row.select("td")
                if len(cells) < 2: continue
                p_obj = {"TeamKey": team_key}
                for j, cell in enumerate(cells):
                    h = headers[j] if j < len(headers) else f"col_{j}"
                    p_obj[h] = cell.get_text(strip=True)
                
                # Parse Minutes for later use
                mins_raw = p_obj.get("Min", "0:0")
                if ":" in mins_raw:
                    m_parts = mins_raw.split(":")
                    p_obj["MinutesDecimal"] = int(m_parts[0]) + int(m_parts[1])/60
                else: 
                    p_obj["MinutesDecimal"] = float(mins_raw) if mins_raw.replace('.','',1).isdigit() else 0.0
                
                players.append(p_obj)
        self.raw_data["OfficialPlayers"] = players

        # 2. Play By Play
        r_pbp = self._fetch(self.urls['pbp'])
        soup_pbp = BeautifulSoup(r_pbp.text, 'html.parser')
        rows = []
        for ev in soup_pbp.select("div.pbpa"):
            cls = ev.get('class', [])
            team = "t1" if any(x in cls for x in ["pbp-t1", "pbpt1"]) else ("t2" if any(x in cls for x in ["pbp-t2", "pbpt2"]) else "Other")
            
            # Foolproof selectors for time and action
            time_el = ev.find(class_=re.compile(r"pbp[-_]time|pbp[-_]clock"))
            act_el = ev.find(class_=re.compile(r"pbp[-_]action"))
            if not time_el or not act_el: continue
            
            # Period detection
            period = 1
            for c in cls:
                if c.startswith("per_") and c[4:].isdigit():
                    period = int(c[4:])
                    break
                elif c == "per_reg": period = 4

            rows.append({
                "Classes": cls, "Team": team, "Period": period,
                "Clock": time_el.get_text(strip=True),
                "Description": act_el.get_text(strip=True)
            })
        self.raw_data["PBPRows"] = rows

        # 3. Summary (For Verification)
        try:
            r_sum = self._fetch(self.urls['sum'])
            soup_sum = BeautifulSoup(r_sum.text, 'html.parser')
            sum_comp = {}
            for row in soup_sum.select("#BLOCK_SUMMARY_COMPARE .summary-compare-detail"):
                try:
                    lbl_el = row.select_one(".fieldName")
                    h_val_el = row.select_one(".fieldHomeStatNumber")
                    a_val_el = row.select_one(".fieldAwayStatNumber")
                    
                    if lbl_el and h_val_el and a_val_el:
                        lbl = lbl_el.get_text(strip=True).lower()
                        h_val = h_val_el.get_text(strip=True)
                        a_val = a_val_el.get_text(strip=True)
                        sum_comp[lbl] = (h_val, a_val)
                except: continue
            self.metadata["OfficialSummary"] = sum_comp
            
            # Extract match date from summary page
            date_elem = soup_sum.select_one(".details .match-time span")
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                print(f"  > Date found: {date_text}")
                # Format: "Dec 3, 2023, 8:30 AM" -> "Dec_3_2023"
                date_parts = date_text.split(',')
                if len(date_parts) >= 2:
                    self.metadata["MatchDate"] = date_parts[0].strip().replace(' ', '_') + '_' + date_parts[1].strip().split()[0]
                else:
                    self.metadata["MatchDate"] = date_text.replace(' ', '_').replace(',', '')
            else:
                print(f"  > Date element NOT found in summary page. URL: {self.urls['sum']}")
                print(f"  > content preview: {soup_sum.prettify()[:500]}")
                self.metadata["MatchDate"] = "Unknown"
        except Exception as e:
            print(f"  > Error extracting date/summary: {e}")
            self.metadata["MatchDate"] = "Unknown"

    def _build_player_map(self):
        for p in self.raw_data["OfficialPlayers"]:
            jr = p.get("No", "-")
            if jr.isdigit(): jr = str(int(jr))
            key = (p["TeamKey"], jr)
            self.player_map[key] = p.get("Player", "Unknown")
            # Initialize stats with official metadata
            name = p.get("Player", "Unknown")
            if name not in self.player_stats:
                self.player_stats[name] = {
                    "No": p.get("No", "-"),
                    "Player": name,
                    "Mins": p.get("Min", "0:0"),
                    "MIN_DEC": p.get("MinutesDecimal", 0.0),
                    "Team": self.metadata["Teams"][p["TeamKey"]],
                    "Jersey": p.get("No", "-"),
                    "PTS":0, "REB":0, "OREB":0, "DREB":0, "AST":0, "STL":0, "BLK":0, "TOV":0,
                    "FGM":0, "FGA":0, "2PM":0, "2PA":0, "3PM":0, "3PA":0, "FTM":0, "FTA":0,
                    "PF":0, "FD":0, "BLKR":0, "2CP":0, "+/-":0
                }

    def _get_abs_time(self, period, clock_str):
        try:
            m, s = map(int, clock_str.split(":"))
            return (period - 1) * 600 + (600 - (m * 60 + s))
        except: return 0

    def _is_paint(self, desc):
        d = desc.lower()
        return any(k in d for k in ["layup", "lay up", "dunk", "tip-in", "hook", "driving", "putback", "floating"])

    def _process_pbp(self):
        mstate = {
            "t1": {"last_oreb_time": -99, "last_tov_opp_time": -99, "trans_time": -99},
            "t2": {"last_oreb_time": -99, "last_tov_opp_time": -99, "trans_time": -99}
        }
        
        for row in self.raw_data["PBPRows"]:
            desc = row["Description"]
            cls = row["Classes"]
            team = row["Team"]
            if team == "Other": continue
            opp = "t2" if team == "t1" else "t1"
            abs_time = self._get_abs_time(row["Period"], row["Clock"])
            
            # State Updates
            if "pbptyturnover" in cls: mstate[opp]["last_tov_opp_time"] = abs_time
            if "pbptyrebound" in cls and "offensive" in desc.lower(): mstate[team]["last_oreb_time"] = abs_time
            if "pbptysteal" in cls: mstate[team]["trans_time"] = abs_time
            if "pbptyrebound" in cls and "defensive" in desc.lower(): mstate[team]["trans_time"] = abs_time

            # Entity Mapping
            m = re.search(r"^(\d+)[\s,]+(.*?)(?:,|$)", desc)
            if not m: continue
            
            jersey = m.group(1)
            if jersey.isdigit(): jersey = str(int(jersey))
            p_name = self.player_map.get((team, jersey))
            if not p_name: continue
            
            period_label = f"Q{row['Period']}"
            if period_label not in self.period_stats: self.period_stats[period_label] = {}
            
            for target_stats in [self.player_stats, self.period_stats[period_label]]:
                if p_name not in target_stats:
                    # This fallback should rarely hit if player_map is built from boxscore
                    target_stats[p_name] = {
                        "No": jersey, "Player": p_name, "Mins": "0:0", "MIN_DEC":0.0,
                        "PTS":0, "REB":0, "OREB":0, "DREB":0, "AST":0, "STL":0, "BLK":0, "TOV":0,
                        "FGM":0, "FGA":0, "2PM":0, "2PA":0, "3PM":0, "3PA":0, "FTM":0, "FTA":0,
                        "PF":0, "FD":0, "BLKR":0, "2CP":0, "+/-":0,
                        "Team": self.metadata["Teams"][team], "Jersey": jersey
                    }
            
            s = self.player_stats[p_name]
            sp = self.period_stats[period_label][p_name]
            made = "pbpmade" in cls or ("made" in desc.lower() and "miss" not in desc.lower())
            
            # Core Stats: Robust detection using Classes OR Description text fallbacks
            is_3pt = "pbpty3pt" in cls or any(x in desc.lower() for x in ["3pt", "3-pt", "3 pointer", "3-pointer"])
            is_2pt = "pbpty2pt" in cls or (not is_3pt and any(x in desc.lower() for x in ["2pt", "2-pt", "layup", "lay-up", "dunk", "jump shot", "jumper", "tip-in"]))
            is_ft = "pbptyfreethrow" in cls or "free throw" in desc.lower()

            if is_3pt:
                s["3PA"] += 1; s["FGA"] += 1
                sp["3PA"] += 1; sp["FGA"] += 1
                if made: 
                    s["3PM"] += 1; s["FGM"] += 1; s["PTS"] += 3
                    sp["3PM"] += 1; sp["FGM"] += 1; sp["PTS"] += 3
                    self.team_stats[team]["PTS"] += 3
            elif is_2pt:
                s["2PA"] += 1; s["FGA"] += 1
                sp["2PA"] += 1; sp["FGA"] += 1
                if made: 
                    s["2PM"] += 1; s["FGM"] += 1; s["PTS"] += 2
                    sp["2PM"] += 1; sp["FGM"] += 1; sp["PTS"] += 2
                    self.team_stats[team]["PTS"] += 2
            elif is_ft:
                s["FTA"] += 1; sp["FTA"] += 1
                if made: 
                    s["FTM"] += 1; s["PTS"] += 1
                    sp["FTM"] += 1; sp["PTS"] += 1
                    self.team_stats[team]["PTS"] += 1
            
            # Advanced Indicators (Team Totals)
            if made and ("pbpty3pt" in cls or "pbpty2pt" in cls):
                if self._is_paint(desc): self.team_stats[team]["PITP"] += 2
                
                # Consumable heuristics
                if (abs_time - mstate[team]["last_oreb_time"]) <= 4:
                    self.team_stats[team]["2ND PTS"] += 2
                    mstate[team]["last_oreb_time"] = -99
                if (abs_time - mstate[team]["last_tov_opp_time"]) <= 8:
                    self.team_stats[team]["OFF TO"] += 2
                    mstate[team]["last_tov_opp_time"] = -99
                if (abs_time - mstate[team]["trans_time"]) <= 5 or "fast break" in desc.lower():
                    self.team_stats[team]["FBPS"] += 2
                    mstate[team]["trans_time"] = -99

            if not made:
                if "pbptyrebound" in cls:
                    s["REB"] += 1; sp["REB"] += 1
                    if "offensive" in desc.lower(): s["OREB"] += 1; sp["OREB"] += 1
                    else: s["DREB"] += 1; sp["DREB"] += 1
                if "pbptyassist" in cls: s["AST"] += 1; sp["AST"] += 1
                if "pbptysteal" in cls: s["STL"] += 1; sp["STL"] += 1
                if "pbptyblock" in cls:
                    s["BLK"] += 1; sp["BLK"] += 1
                    # Blocked shooter (BLKR) - look at last non-Other event
                    # We'll handle this by scanning the PBPRows in a slightly smarter way or keeping track of the last shooter
                if "pbptyturnover" in cls: s["TOV"] += 1; sp["TOV"] += 1
                if "pbptyfoul" in cls:
                    s["PF"] += 1; sp["PF"] += 1
                if "pbptyfoulon" in cls:
                    s["FD"] += 1; sp["FD"] += 1

        # Second Pass for BLKR and Individual 2CP
        # We need a temporal scan to catch the "last shot" for BLKR and OREB timing for 2CP
        last_shot_info = None # (p_name, time)
        last_oreb_time = {"t1": -99, "t2": -99}

        for row in self.raw_data["PBPRows"]:
            desc = row["Description"]
            cls = row["Classes"]
            team = row["Team"]
            if team == "Other": continue
            abs_time = self._get_abs_time(row["Period"], row["Clock"])
            
            # Identify actor
            m = re.search(r"^(\d+)", desc)
            if not m: continue
            jersey = str(int(m.group(1)))
            p_name = self.player_map.get((team, jersey))
            if not p_name: continue
            
            s = self.player_stats[p_name]
            made = "pbpmade" in cls or ("made" in desc.lower() and "miss" not in desc.lower())
            
            # 1. BLKR Logic
            if "pbptyblock" in cls:
                if last_shot_info:
                    shooter_name, shot_time = last_shot_info
                    # If block is within 3 seconds of a missed shot by opponent
                    if abs_time - shot_time <= 3 and shooter_name in self.player_stats:
                        self.player_stats[shooter_name]["BLKR"] += 1
            
            # 2. Individual 2CP Logic
            if made and ("pbpty3pt" in cls or "pbpty2pt" in cls or "pbptyfreethrow" in cls):
                pts = 3 if "pbpty3pt" in cls else (2 if "pbpty2pt" in cls else 1)
                if (abs_time - last_oreb_time.get(team, -99)) <= 24:
                    s["2CP"] += pts
                    # Note: We don't reset last_oreb_time here because multiple scores can occur in one possession (putbacks)
            
            # Update state for next loops
            if ("pbpty3pt" in cls or "pbpty2pt" in cls) and not made:
                last_shot_info = (p_name, abs_time)
            
            if "pbptyrebound" in cls and "offensive" in desc.lower():
                last_oreb_time[team] = abs_time

    def _track_minutes(self):
        """
        Process PBP to track Minutes AND Lineup/Advanced Stats
        (OffPTS, DefPTS, TeamFGA, TeamFTA, TeamTOV, TeamOREB while on court)
        """
        
        # --- Helpers ---
        def parse_clock_robust(period, clock_str):
            try:
                if not clock_str or clock_str == "0-0": return 0
                import re
                # P{p}{mm}:{ss}
                m = re.match(r"P(\d)(\d{2}):(\d{2})", clock_str)
                if m:
                    p, mins, secs = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    elapsed = (10 * 60) - (mins * 60 + secs)
                    return (p - 1) * 600 + elapsed
                
                # MM:SS
                m = re.match(r"(\d+):(\d{2})", clock_str)
                if m:
                    mins, secs = int(m.group(1)), int(m.group(2))
                    elapsed = (10 * 60) - (mins * 60 + secs)
                    return (period - 1) * 600 + elapsed
                return 0
            except:
                return 0

        def add_period_stat(p_name, key, val, time_sec):
            # Q1=0-600, Q2=600-1200...
            p = int(time_sec // 600) + 1
            if p > 4: q_key = f"OT{p-4}"
            else: q_key = f"Q{p}"
            
            if q_key not in self.period_stats: self.period_stats[q_key] = {}
            if p_name not in self.period_stats[q_key]: self.period_stats[q_key][p_name] = {}
            if key not in self.period_stats[q_key][p_name]: self.period_stats[q_key][p_name][key] = 0.0
            self.period_stats[q_key][p_name][key] += val

        def add_global_stat(p_name, key, val):
            if p_name not in self.player_stats: return
            if key not in self.player_stats[p_name]: self.player_stats[p_name][key] = 0.0
            self.player_stats[p_name][key] += val

        # --- Initialization ---
        on_court = {"t1": set(), "t2": set()}
        stint_start = {"t1": {}, "t2": {}}
        player_minutes = {}
        
        # 1. First Sub Time Scan
        first_sub_time = {"t1": 9999, "t2": 9999}
        for row in self.raw_data.get("PBPRows", []):
            if "pbptysubstitution" in row["Classes"]:
                t = row["Team"]
                if t in ["t1", "t2"]:
                    tm = parse_clock_robust(row["Period"], row["Clock"])
                    first_sub_time[t] = min(first_sub_time[t], tm)
                    
        # 2. Starters Identification
        import re
        for row in self.raw_data.get("PBPRows", []):
            t = row["Team"]
            if t not in ["t1", "t2"]: continue
            tm = parse_clock_robust(row["Period"], row["Clock"])
            m = re.search(r"^(\d+)", row["Description"])
            if not m: continue
            
            jersey = str(int(m.group(1))) # Normalize
            p_name = self.player_map.get((t, jersey))
            if not p_name: continue
            
            # If identified before first sub, assume starter
            if tm < first_sub_time[t] and p_name not in on_court[t]:
                on_court[t].add(p_name)
                stint_start[t][p_name] = 0
                if p_name not in player_minutes: player_minutes[p_name] = 0.0
                
        # 3. Iterate ALL Events
        last_oreb_ts = {"t1": -999, "t2": -999}
        import re

        for row in self.raw_data.get("PBPRows", []):
            t = row["Team"]
            # If team unknown, skip
            
            desc = row["Description"]
            cls = row["Classes"]
            tm = parse_clock_robust(row["Period"], row["Clock"])
            
            # --- Substitution Handling ---
            if "pbptysubstitution" in cls and t in ["t1", "t2"]:
                m = re.search(r"^(\d+).*?Substitution\s+(in|out)", desc, re.IGNORECASE)
                if m:
                    jersey = str(int(m.group(1)))
                    sub_type = m.group(2).lower()
                    p_name = self.player_map.get((t, jersey))
                    
                    if p_name:
                        if p_name not in player_minutes: player_minutes[p_name] = 0.0
                        
                        if sub_type == "out" and p_name in on_court[t]:
                            s_time = stint_start[t].get(p_name, 0)
                            dur = (tm - s_time) / 60.0
                            if 0 < dur < 60:
                                player_minutes[p_name] += dur
                                add_period_stat(p_name, "MIN_CALC", dur, tm)
                            
                            on_court[t].remove(p_name)
                            if p_name in stint_start[t]: del stint_start[t][p_name]
                            
                        elif sub_type == "in" and p_name not in on_court[t]:
                            on_court[t].add(p_name)
                            stint_start[t][p_name] = tm
            
            # --- Advanced Stats Handling ---
            active_t = t
            if active_t == "t1": opp_t = "t2"
            elif active_t == "t2": opp_t = "t1"
            else: continue
            
            def update_lineup(team_key, stat_key, value):
                for p in on_court[team_key]:
                    add_global_stat(p, stat_key, value)
                    add_period_stat(p, stat_key, value, tm)
            
            # Logic Helpers
            made = "pbpmade" in cls or ("made" in desc.lower() and "miss" not in desc.lower())
            is_2pt = "pbpty2pt" in cls
            is_3pt = "pbpty3pt" in cls
            is_ft = "pbptyfreethrow" in cls
            is_reb = "pbptyrebound" in cls
            is_tov = "pbptyturnover" in cls
            is_ast = "pbptyassist" in cls
            is_stl = "pbptysteal" in cls
            is_blk = "pbptyblock" in cls
            is_pf = "pbptyfoul" in cls
            
            # 1. Scoring & 2CP
            pts = 0
            if made:
                if is_2pt: pts = 2
                elif is_3pt: pts = 3
                elif is_ft: pts = 1
                
            if pts > 0:
                update_lineup(active_t, "OffPTS", pts)
                update_lineup(opp_t, "DefPTS", pts)
                
            # 2. Possession Components
            if made:
                if is_2pt or is_3pt:
                    update_lineup(active_t, "TmFGM", 1)
                    update_lineup(opp_t, "OppFGM", 1)
                if is_3pt:
                    update_lineup(active_t, "Tm3PM", 1)
                    update_lineup(opp_t, "Opp3PM", 1)
                if is_ft:
                    update_lineup(active_t, "TmFTM", 1)
                    update_lineup(opp_t, "OppFTM", 1)

            # FGA
            if is_2pt or is_3pt:
                update_lineup(active_t, "TmFGA", 1)
                update_lineup(opp_t, "OppFGA", 1)
            
            # FTA
            if is_ft:
                update_lineup(active_t, "TmFTA", 1)
                update_lineup(opp_t, "OppFTA", 1)
                
            # TOV
            if is_tov:
                update_lineup(active_t, "TmTOV", 1)
                update_lineup(opp_t, "OppTOV", 1)
            
            # AST
            if is_ast:
                update_lineup(active_t, "TmAST", 1)
                update_lineup(opp_t, "OppAST", 1)
                
            # STL
            if is_stl:
                update_lineup(active_t, "TmSTL", 1)
                update_lineup(opp_t, "OppSTL", 1)
                
            # BLK
            if is_blk:
                update_lineup(active_t, "TmBLK", 1)
                update_lineup(opp_t, "OppBLK", 1)
                
            # PF & FD
            if is_pf:
                update_lineup(active_t, "TmPF", 1)
                update_lineup(opp_t, "OppPF", 1)
                # Parsed FD (Fouls Drawn)
                # Look for "on X"
                m_fd = re.search(r"\son\s+(\d+)", desc)
                if m_fd:
                    vic_jersey = str(int(m_fd.group(1)))
                    # Victim is usually on Opponent Team (opp_t)
                    vic_name = self.player_map.get((opp_t, vic_jersey))
                    if vic_name:
                        add_global_stat(vic_name, "FD", 1)
                        add_period_stat(vic_name, "FD", 1, tm)

            # Rebounds & OREB State
            if is_reb:
                if "offensive" in desc.lower():
                    update_lineup(active_t, "TmOREB", 1)
                    update_lineup(opp_t, "OppOREB", 1)
                    last_oreb_ts[active_t] = tm
                else: # Defensive
                    update_lineup(active_t, "TmDREB", 1)
                    update_lineup(opp_t, "OppDREB", 1)

        # 4. Close Open Stints
        game_end = 40 * 60
        for t in ["t1", "t2"]:
            for p_name in on_court[t]:
                s_time = stint_start[t].get(p_name, 0)
                dur = (game_end - s_time) / 60.0
                if 0 < dur < 60:
                    if p_name not in player_minutes: player_minutes[p_name] = 0.0
                    player_minutes[p_name] += dur
                    add_period_stat(p_name, "MIN_CALC", dur, game_end)
                    
        # 5. Finalize Strings
        for p_name, mins_decimal in player_minutes.items():
            if p_name in self.player_stats:
                mins = int(mins_decimal)
                secs = int((mins_decimal - mins) * 60)
                self.player_stats[p_name]["Mins"] = f"{mins}:{secs:02d}"
                self.player_stats[p_name]["MIN_DEC"] = round(mins_decimal, 1)

        for q, p_dict in self.period_stats.items():
            for p_name, s in p_dict.items():
                 calc_min = s.get("MIN_CALC", 0.0)
                 if calc_min > 0:
                     mins = int(calc_min)
                     secs = int((calc_min - mins) * 60)
                     s["Mins"] = f"{mins}:{secs:02d}"
                     s["MIN_DEC"] = round(calc_min, 1)

    def _calculate_advanced_player_metrics(self):
        """Calculate Advanced Metrics for Global and Period Stats"""
        
        def calc_metrics(s):
            # Basic Shooting
            fga = s.get("FGA", 0); fgm = s.get("FGM", 0)
            pm3 = s.get("3PM", 0); fta = s.get("FTA", 0); ftm = s.get("FTM", 0)
            tov = s.get("TOV", 0); ast = s.get("AST", 0)
            oreb = s.get("OREB", 0); dreb = s.get("DREB", 0); reb = s.get("REB", 0)
            pts = s.get("PTS", 0)
            
            s["FG%"] = (fgm / fga * 100) if fga > 0 else 0
            s["2P%"] = (s.get("2PM", 0) / s.get("2PA", 0) * 100) if s.get("2PA", 0) > 0 else 0
            s["3P%"] = (pm3 / s.get("3PA", 0) * 100) if s.get("3PA", 0) > 0 else 0
            s["FT%"] = (ftm / fta * 100) if fta > 0 else 0
            s["eFG%"] = ((fgm + 0.5 * pm3) / fga * 100) if fga > 0 else 0
            s["TS%"] = (pts / (2 * (fga + 0.44 * fta)) * 100) if (fga + 0.44 * fta) > 0 else 0
            
            # Lineup Context
            tm_fga = s.get("TmFGA", 0); tm_fta = s.get("TmFTA", 0)
            tm_tov = s.get("TmTOV", 0); tm_oreb = s.get("TmOREB", 0)
            tm_dreb = s.get("TmDREB", 0); tm_fgm = s.get("TmFGM", 0)
            
            opp_fga = s.get("OppFGA", 0); opp_fta = s.get("OppFTA", 0)
            opp_tov = s.get("OppTOV", 0); opp_oreb = s.get("OppOREB", 0)
            opp_dreb = s.get("OppDREB", 0)
            
            # Possessions
            tm_poss = tm_fga + 0.44 * tm_fta - tm_oreb + tm_tov
            opp_poss = opp_fga + 0.44 * opp_fta - opp_oreb + opp_tov
            
            # 1. OFFRTG (Points per 100 Poss)
            off_pts = s.get("OffPTS", 0)
            s["OFFRTG"] = round((off_pts / tm_poss * 100), 1) if tm_poss > 0 else 0.0
            
            # 2. DEFRTG (Opp Points per 100 Poss)
            def_pts = s.get("DefPTS", 0)
            s["DEFRTG"] = round((def_pts / opp_poss * 100), 1) if opp_poss > 0 else 0.0
            
            s["+/-"] = int(off_pts - def_pts)
            s["NETRTG"] = round(s["OFFRTG"] - s["DEFRTG"], 1)
            
            # 3. USG% (Player Poss / Team Poss)
            p_poss = fga + 0.44 * fta + tov
            s["USG%"] = round((p_poss / tm_poss * 100), 1) if tm_poss > 0 else 0.0
            
            # 4. AST% (AST / (TmFGM - FGM))
            # Denominator = Teammate FGM
            bgmx = tm_fgm - fgm
            s["AST%"] = round((ast / bgmx * 100), 1) if bgmx > 0 else 0.0
            
            # 5. Rebounding %
            s["OREB%"] = round((oreb / (tm_oreb + opp_dreb) * 100), 1) if (tm_oreb + opp_dreb) > 0 else 0.0
            s["DREB%"] = round((dreb / (tm_dreb + opp_oreb) * 100), 1) if (tm_dreb + opp_oreb) > 0 else 0.0
            total_reb_opp = tm_oreb + tm_dreb + opp_oreb + opp_dreb
            s["REB%"] = round((reb / total_reb_opp * 100), 1) if total_reb_opp > 0 else 0.0
            
            # 6. Ratios
            s["AST/TO"] = round(ast / tov, 2) if tov > 0 else float(ast)
            s["TO RATIO"] = round((tov / p_poss * 100), 1) if p_poss > 0 else 0.0
            s["AST RATIO"] = round((ast / p_poss * 100), 1) if p_poss > 0 else 0.0
            
            # 7. PIE (Player Impact Estimate)
            # Numerator
            p_pts = s.get("PTS", 0); p_fgm = s.get("FGM", 0); p_ftm = s.get("FTM", 0)
            p_fga = s.get("FGA", 0); p_fta = s.get("FTA", 0)
            p_dreb = s.get("DREB", 0); p_oreb = s.get("OREB", 0)
            p_ast = s.get("AST", 0); p_stl = s.get("STL", 0); p_blk = s.get("BLK", 0)
            p_pf = s.get("PF", 0); p_tov = s.get("TOV", 0)
            
            pie_num = p_pts + p_fgm + p_ftm - p_fga - p_fta + p_dreb + (0.5 * p_oreb) + p_ast + p_stl + (0.5 * p_blk) - p_pf - p_tov
            
            # Denominator (Game Totals)
            gm_pts = s.get("OffPTS", 0) + s.get("DefPTS", 0) 
            gm_fgm = s.get("TmFGM", 0) + s.get("OppFGM", 0)
            gm_ftm = s.get("TmFTM", 0) + s.get("OppFTM", 0)
            gm_fga = s.get("TmFGA", 0) + s.get("OppFGA", 0)
            gm_fta = s.get("TmFTA", 0) + s.get("OppFTA", 0)
            gm_dreb = s.get("TmDREB", 0) + s.get("OppDREB", 0)
            gm_oreb = s.get("TmOREB", 0) + s.get("OppOREB", 0)
            gm_ast = s.get("TmAST", 0) + s.get("OppAST", 0)
            gm_stl = s.get("TmSTL", 0) + s.get("OppSTL", 0)
            gm_blk = s.get("TmBLK", 0) + s.get("OppBLK", 0)
            gm_pf = s.get("TmPF", 0) + s.get("OppPF", 0)
            gm_tov = s.get("TmTOV", 0) + s.get("OppTOV", 0)
            
            pie_den = gm_pts + gm_fgm + gm_ftm - gm_fga - gm_fta + gm_dreb + (0.5 * gm_oreb) + gm_ast + gm_stl + (0.5 * gm_blk) - gm_pf - gm_tov
            
            s["PIE"] = round((pie_num / pie_den * 100), 1) if pie_den > 0 else 0.0
            s["PACE"] = 0 # Placeholder if needed, or implement full
            
            # 8. Other
            s["Eff"] = (pts + reb + ast + s.get("STL",0) + s.get("BLK",0)) - ((fga - fgm) + (fta - ftm) + tov)
            s["GmScr"] = pts + 0.4*fgm - 0.7*fga - 0.4*(fta-ftm) + 0.7*oreb + 0.3*dreb + s.get("STL",0) + 0.7*ast + 0.7*s.get("BLK",0) - 0.4*s.get("PF",0) - tov
            s["FIC"] = pts + 0.8*oreb + 1.4*dreb + ast + s.get("STL",0) + s.get("BLK",0) - 0.7*fga - 0.8*fta - 1.4*tov - s.get("PF",0)

        # Global
        for p_name, s in self.player_stats.items():
            calc_metrics(s)
            
        # Period
        for q, p_dict in self.period_stats.items():
            for p_name, s in p_dict.items():
                calc_metrics(s)
                # Rounding
                for k in ["FG%", "2P%", "3P%", "FT%", "eFG%", "TS%", "GmScr", "FIC"]:
                    s[k] = round(s.get(k, 0), 1)

    def _calculate_team_metrics(self):
        # 1. Aggregate Player Stats
        for team_key in ["t1", "t2"]:
            team_name = self.metadata["Teams"][team_key]
            d = self.team_stats[team_key]
            # Bases
            agg = {"FGM":0, "FGA":0, "2PM":0, "2PA":0, "3PM":0, "3PA":0, "FTM":0, "FTA":0, "OREB":0, "DREB":0, "TOV":0, "AST":0, "STL":0, "BLK":0, "PF":0}
            
            for p_name, s in self.player_stats.items():
                if s["Team"] == team_name:
                    for k in agg:
                        agg[k] += s.get(k, 0)
            
            d.update(agg)
            d["REB"] = d["OREB"] + d["DREB"]

        # 2. Advanced Team Stats
        for team_key in ["t1", "t2"]:
            opp_key = "t2" if team_key == "t1" else "t1"
            d = self.team_stats[team_key]
            o = self.team_stats[opp_key]
            
            tm_poss = d["FGA"] + 0.44*d["FTA"] - d["OREB"] + d["TOV"]
            opp_poss = o["FGA"] + 0.44*o["FTA"] - o["OREB"] + o["TOV"]
            
            d["OFFRTG"] = round(d["PTS"] / tm_poss * 100, 1) if tm_poss > 0 else 0.0
            d["DEFRTG"] = round(o["PTS"] / opp_poss * 100, 1) if opp_poss > 0 else 0.0
            d["NETRTG"] = round(d["OFFRTG"] - d["DEFRTG"], 1)
            
            d["eFG%"] = round((d["FGM"] + 0.5*d["3PM"]) / d["FGA"] * 100, 1) if d["FGA"] > 0 else 0.0
            d["TS%"] = round(d["PTS"] / (2*(d["FGA"] + 0.44*d["FTA"])) * 100, 1) if (d["FGA"]+0.44*d["FTA"]) > 0 else 0.0
            d["AST%"] = round(d["AST"] / d["FGM"] * 100, 1) if d["FGM"] > 0 else 0.0
            d["AST RATIO"] = round(d["AST"] / tm_poss * 100, 1) if tm_poss > 0 else 0.0
            d["TO RATIO"] = round(d["TOV"] / tm_poss * 100, 1) if tm_poss > 0 else 0.0
            
            d["OREB%"] = round(d["OREB"] / (d["OREB"] + o["DREB"]) * 100, 1) if (d["OREB"] + o["DREB"]) > 0 else 0.0
            d["DREB%"] = round(d["DREB"] / (d["DREB"] + o["OREB"]) * 100, 1) if (d["DREB"] + o["OREB"]) > 0 else 0.0
            d["REB%"] = round(d["REB"] / (d["REB"] + o["REB"]) * 100, 1) if (d["REB"] + o["REB"]) > 0 else 0.0


if __name__ == "__main__":
    parser = VibeMasterParser("2391613")
    p_stats, t_stats, meta = parser.run()
    
    print("\n--- MASTER CODE VERIFICATION (Match 2391613) ---")
    sum_off = meta.get("OfficialSummary", {})
    t_names = meta.get("Teams", {})
    
    for tk in ["t1", "t2"]:
        name = t_names.get(tk, tk)
        off = sum_off.get(name.lower(), ("0", "0")) # Summary handles Home/Away tuple?
        # Re-check how summary stats were stored
        print(f"\nTeam: {name}")
        d = t_stats[tk]
        print(f"  PTS: {d['PTS']}")
        print(f"  PITP: {d['PITP']}")
        print(f"  FBPS: {d['FBPS']}")
        print(f"  OFF TO: {d['OFF TO']}")
        print(f"  2ND PTS: {d['2ND PTS']}")
