import pandas as pd
import numpy as np

def apply_stat_rounding(df, mode="totals"):
    """
    Apply consistent rounding to all statistics in a DataFrame.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing statistics
    mode : str
        Display mode - "totals", "per_game", or "per_36"
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with properly rounded statistics
    """
    df = df.copy()
    
    # Percentages - always 1 decimal
    pct_cols = ["FG%", "3P%", "FT%", "eFG%", "TS%", "USG%", "AST%", 
                "OREB%", "DREB%", "REB%", "TO RATIO", "AST RATIO",
                "%FGM", "%FGA", "%3PM", "%3PA", "%FTM", "%FTA",
                "%OREB", "%DREB", "%REB", "%AST", "%TOV", "%STL", "%BLK",
                "%BLKA", "%PF", "%PFD", "%PTS",
                "%FGA 2PT", "%FGA 3PT", "%PTS 2PT", "%PTS 2PT MR", "%PTS 3PT",
                "%PTS FBPS", "%PTS FT", "%PTS OFFTO", "%PTS PITP",
                "2FGM %AST", "2FGM %UAST", "3FGM %AST", "3FGM %UAST",
                "FGM %AST", "FGM %UAST"]
    
    for col in pct_cols:
        if col in df.columns:
            # Try to convert to numeric first, coercing errors to NaN
            # This handles cases where data might be strings "50.5" or similar
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].round(1)
    
    # Advanced metrics - always 1 decimal
    adv_cols = ["OFFRTG", "DEFRTG", "NETRTG", "PIE", "PACE", "PPoss",
                "AST/TO", "GmScr", "FIC"]
    
    for col in adv_cols:
        if col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].round(1)
    
    # MIN - check if numeric before rounding to avoid breaking "MM:SS" strings
    for col in ["MIN", "Min", "MIN_CALC", "Mins"]:
        if col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].round(1)
            # If it's not numeric (e.g. "35:20"), leave it alone
    
    # Counting stats - depends on mode
    count_cols = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA",
                  "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK",
                  "PF", "FD", "DD2", "TD3"]
    
    if mode in ["per_game", "per_36"]:
        # Per-game/per-36: 1 decimal
        for col in count_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].round(1)
    else:
        # Totals: integers
        for col in count_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                # Fill NaNs with 0 before int conversion if needed, but safe round(0) keeps NaNs as NaNs
                # To be safe for display:
                df[col] = df[col].fillna(0).round(0).astype(int)
    
    # +/- - always 1 decimal (can be negative)
    if "+/-" in df.columns:
        if not pd.api.types.is_numeric_dtype(df["+/-"]):
             df["+/-"] = pd.to_numeric(df["+/-"], errors='coerce')
        df["+/-"] = df["+/-"].round(1)
    
    return df

# Canonical Schema Mappings (Display -> Internal or Internal -> Display)
TOTALS_MAP = {
    "GP": "G",
    "MIN_CALC": "Mins",
    "PTS": "Pts",
    "FGM": "FGM",
    "FGA": "FGA",
    "FG%": "FG%",
    "2PM": "2PM",
    "2PA": "2PA",
    "2P%": "2P%",
    "3PM": "3PM",
    "3PA": "3PA",
    "3P%": "3P%",
    "FTM": "FTM",
    "FTA": "FTA",
    "FT%": "FT%",
    "OREB": "OR",
    "DREB": "DR",
    "REB": "REB",
    "AST": "AST",
    "STL": "STL",
    "TOV": "TO",
    "BLK": "BLK",
    "PF": "PF",
    "FD": "FD",
    "Eff": "EFF",
    "eFG%": "eFG%",
    "TS%": "TS%",
    "TSA": "TSA",
    "AST/TO": "A/TO",
    "OFFRTG": "Off Rat"
}

PER_GAME_MAP = {
    "GP": "G",
    "MIN_CALC": "MPG",
    "PTS": "PPG",
    "FGM": "FGMPG",
    "FGA": "FGAPG",
    "FG%": "FG%",
    "2PM": "2PMPG",
    "2PA": "2PAPG",
    "2P%": "2P%",
    "3PM": "3PMPG",
    "3PA": "3PAPG",
    "3P%": "3P%",
    "FTM": "FTMPG",
    "FTA": "FTAPG",
    "FT%": "FT%",
    "OREB": "ORPG",
    "DREB": "DRPG",
    "REB": "RPG",
    "AST": "APG",
    "STL": "STPG",
    "TOV": "TOPG",
    "BLK": "BLKPG",
    "PF": "PFPG",
    "FD": "FOPG",
    "Eff": "EFF",
    "eFG%": "eFG%",
    "TS%": "TS%",
    "TSA": "TSAPG",
    "AST/TO": "A/TO",
    "OFFRTG": "Off Rat"
}

def normalize_stats(df):
    """Ensure dataframe has all necessary numeric columns filled with 0."""
    cols = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "2PM", "2PA", 
            "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "FD", "BLKR", "2CP", "MIN_CALC",
            "OffPTS", "DefPTS", "TmFGA", "TmFTA", "TmTOV", "TmOREB", "TmDREB", "TmFGM", "TmPF", "TmFTM", "TmBLK", "TmAST", "TmSTL",
            "OppFGA", "OppFTA", "OppTOV", "OppOREB", "OppDREB", "OppFGM", "OppFTM", "OppAST", "OppSTL", "OppBLK", "OppPF", "OppPTS", "Opp3PM"]
    
    for c in cols:
        if c not in df.columns:
            df[c] = 0
            
    # Sync MIN_CALC from MIN_DEC if available
    if "MIN_DEC" in df.columns:
        df["MIN_CALC"] = df["MIN_CALC"].where(df["MIN_CALC"] > 0, df["MIN_DEC"])
            
    df[cols] = df[cols].fillna(0)
    return df

def calculate_derived_stats(df):
    """Vectorized calculation of advanced stats for players."""
    if df.empty: return df
    
    # Ensure all columns exist (defensive)
    df = normalize_stats(df)
    
    
    # --- DATA INTEGRITY & INFERENCE ---
    # Only calculate 2PM/2PA if they are missing or zero
    # The parser provides accurate 2PM/2PA from actual game data, don't overwrite it
    mask_2p_missing = (df["2PM"].fillna(0) == 0) & (df["2PA"].fillna(0) == 0)
    df.loc[mask_2p_missing, "2PM"] = df.loc[mask_2p_missing, "FGM"] - df.loc[mask_2p_missing, "3PM"]
    df.loc[mask_2p_missing, "2PA"] = df.loc[mask_2p_missing, "FGA"] - df.loc[mask_2p_missing, "3PA"]
    
    
    # 1. Percentages
    df["FG%"] = (df["FGM"] / df["FGA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["2P%"] = (df["2PM"] / df["2PA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["3P%"] = (df["3PM"] / df["3PA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["FT%"] = (df["FTM"] / df["FTA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["eFG%"] = ((df["FGM"] + 0.5 * df["3PM"]) / df["FGA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    ts_denom = 2 * (df["FGA"] + 0.44 * df["FTA"])
    df["TS%"] = (df["PTS"] / ts_denom * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    # 2. Efficiency (NBA)
    missed_fg = df["FGA"] - df["FGM"]
    missed_ft = df["FTA"] - df["FTM"]
    df["Eff"] = (df["PTS"] + df["REB"] + df["AST"] + df["STL"] + df["BLK"]) - (missed_fg + missed_ft + df["TOV"])
    
    # 3. Advanced Context (Possessions)
    # Only calculate TmPoss/OppPoss if they don't exist or are all zeros
    # For tournament stats, these are summed from game-level values and should be preserved
    if "TmPoss" not in df.columns or (df["TmPoss"] == 0).all():
        df["TmPoss"] = df["TmFGA"] + 0.44 * df["TmFTA"] - df["TmOREB"] + df["TmTOV"]
    
    if "OppPoss" not in df.columns or (df["OppPoss"] == 0).all():
        df["OppPoss"] = df["OppFGA"] + 0.44 * df["OppFTA"] - df["OppOREB"] + df["OppTOV"]
    
    df["PPoss"] = df["FGA"] + 0.44 * df["FTA"] + df["TOV"]
    df["TSA"] = df["FGA"] + 0.44 * df["FTA"]
    
    # 4. Advanced Metrics
    # USG% = 100 * ((FGA + 0.44 * FTA + TOV) * (TmMin / 5)) / (Min * (TmFGA + 0.44 * TmFTA + TmTOV))
    # _TmMin should be the total team minutes across all games/periods
    # For tournament stats: GP × minutes_per_period
    # Need to infer period type from the data since we don't have explicit period info here
    
    if "GP" in df.columns and "MIN_CALC" in df.columns:
        # Infer period type from average minutes per game
        avg_min_per_game = df["MIN_CALC"] / df["GP"]
        
        # Determine minutes per period based on average player minutes
        # The avg_min_per_game represents minutes per PERIOD (not per full game)
        # Full game: ~10-40 min per game per player (median ~15-20)
        # Half: ~5-20 min per half per player (median ~7-10)
        # Quarter: ~2-10 min per quarter per player (median ~3-5)
        
        # Use median to avoid outliers (bench players with low minutes)
        median_mpg = avg_min_per_game.median()
        
        if median_mpg > 12:
            # Likely full game stats (median player plays 12+ min per game)
            minutes_per_period = 200  # 5 players × 40 min
        elif median_mpg > 4:
            # Likely half stats (median player plays 4-12 min per half)
            minutes_per_period = 100  # 5 players × 20 min
        else:
            # Likely quarter stats (median player plays <4 min per quarter)
            minutes_per_period = 50   # 5 players × 10 min
        
        df["_TmMin"] = df["GP"] * minutes_per_period
    elif "Team" in df.columns and not df.empty:
        # Fallback: try to infer from player minutes
        # This is less accurate but better than nothing
        team_mins = df.groupby("Team")["MIN_CALC"].transform("sum")
        df["_TmMin"] = team_mins
    else:
        # Last resort fallback
        df["_TmMin"] = 200
    
    tm_min = df["_TmMin"]
    p_poss = df["FGA"] + 0.44 * df["FTA"] + df["TOV"]
    
    # Safe denominators
    safe_min = df["MIN_CALC"].clip(lower=0.1)
    safe_tm_poss = df["TmPoss"].clip(lower=1.0)
    safe_opp_poss = df["OppPoss"].clip(lower=1.0)
    
    # USG% calculation
    # For tournament stats, use TmFGA/TmFTA/TmTOV instead of TmPoss
    # TmPoss is a context value (possessions while player on court), not total team possessions
    tm_poss_for_usg = df["TmFGA"] + 0.44 * df["TmFTA"] + df["TmTOV"]
    safe_tm_poss_usg = tm_poss_for_usg.clip(lower=1.0)
    
    usg_num = p_poss * (tm_min / 5)
    usg_den = safe_min * safe_tm_poss_usg
    df["USG%"] = (100 * usg_num / usg_den).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["USG%"] = df["USG%"].clip(0, 100.0)
    
    # AST% = 100 * AST / (((Min / (TmMin / 5)) * TmFGM) - FGM)
    # Standard AST% can be noisy. We'll floor the denominator at 1.0.
    # For period stats, this can be unreliable, so we add extra safety
    ast_den = ((safe_min / (tm_min / 5)) * df["TmFGM"]) - df["FGM"]
    # Only calculate AST% if denominator is reasonable (at least 2 FGM by teammates)
    df["AST%"] = 0.0
    valid_ast = ast_den >= 2.0
    df.loc[valid_ast, "AST%"] = (100 * df.loc[valid_ast, "AST"] / ast_den[valid_ast]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["AST%"] = df["AST%"].clip(0, 100.0)
    
    df["OFFRTG"] = (df["OffPTS"] / safe_tm_poss * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(upper=300.0)
    df["DEFRTG"] = (df["DefPTS"] / safe_opp_poss * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(upper=300.0)
    df["NETRTG"] = df["OFFRTG"] - df["DEFRTG"]
    df["+/-"] = df["OffPTS"] - df["DefPTS"]
    
    # 6. Ratios
    # Use floor of 1.0 for TOV to avoid '30.0' ratio for 3 assists (3/0.1). 
    # This treats 0 TOV as 1 TOV for ratio purposes, which is a standard safeguard.
    df["AST/TO"] = (df["AST"] / df["TOV"].clip(lower=1.0)).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    # --- COMPLEX METRICS ---
    # FIC (Floor Impact Counter)
    df["FIC"] = (df["PTS"] + df["OREB"] + 0.75 * df["DREB"] + df["AST"] + df["STL"] + df["BLK"] - 
                 0.75 * df["FGA"] - 0.375 * df["FTA"] - df["TOV"] - 0.5 * df["PF"])

    # PIE (Player Impact Estimate)
    pie_num = df["PTS"] + df["FGM"] + df["FTM"] - df["FGA"] - df["FTA"] + df["DREB"] + (0.5 * df["OREB"]) + \
              df["AST"] + df["STL"] + (0.5 * df["BLK"]) - df["PF"] - df["TOV"]
              
    gm_pts = df["OffPTS"] + df["DefPTS"]
    gm_fgm = df["TmFGM"] + df["OppFGM"]
    gm_ftm = df["TmFTM"] + df["OppFTM"]
    gm_fga = df["TmFGA"] + df["OppFGA"]
    gm_fta = df["TmFTA"] + df["OppFTA"]
    gm_dreb = df["TmDREB"] + df["OppDREB"]
    gm_oreb = df["TmOREB"] + df["OppOREB"]
    gm_ast = df["TmAST"] + df["OppAST"]
    gm_stl = df["TmSTL"] + df["OppSTL"]
    gm_blk = df["TmBLK"] + df["OppBLK"]
    gm_pf = df["TmPF"] + df["OppPF"] 
    gm_tov = df["TmTOV"] + df["OppTOV"]
    
    pie_den = gm_pts + gm_fgm + gm_ftm - gm_fga - gm_fta + gm_dreb + (0.5 * gm_oreb) + \
              gm_ast + gm_stl + (0.5 * gm_blk) - gm_pf - gm_tov
              
    # PIE Denominator protection: Floor at 20.0 to prevent division by near-zero in bad aggregates
    df["PIE"] = (pie_num / pie_den.clip(lower=20.0) * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["PIE"] = df["PIE"].clip(-100, 100.0)
    
    # Game Score (GmScr)
    df["GmScr"] = df["PTS"] + 0.4 * df["FGM"] - 0.7 * df["FGA"] - 0.4 * (df["FTA"] - df["FTM"]) + \
                  0.7 * df["OREB"] + 0.3 * df["DREB"] + df["STL"] + 0.7 * df["AST"] + 0.7 * df["BLK"] - \
                  0.4 * df["PF"] - df["TOV"]
    
    # Rounding
    pct_cols = ["FG%", "2P%", "3P%", "FT%", "eFG%", "TS%", "USG%", "AST%", "OFFRTG", "DEFRTG", "NETRTG", "PIE", "GmScr", "AST/TO"]
    df[pct_cols] = df[pct_cols].round(1)
    
    return df

def calculate_derived_team_stats(df):
    """Vectorized calculation of advanced stats for TEAMS."""
    if df.empty: return df
    
    df = normalize_stats(df)
    
    # --- BASIC RATE STATS ---
    df["FG%"] = (df["FGM"] / df["FGA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["2P%"] = (df["2PM"] / df["2PA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["3P%"] = (df["3PM"] / df["3PA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["FT%"] = (df["FTM"] / df["FTA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    df["eFG%"] = ((df["FGM"] + 0.5 * df["3PM"]) / df["FGA"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    ts_denom = 2 * (df["FGA"] + 0.44 * df["FTA"])
    df["TS%"] = (df["PTS"] / ts_denom * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    # --- POSSESSIONS ---
    # Team Poss = FGA + 0.44*FTA - OREB + TOV
    df["Poss"] = df["FGA"] + 0.44 * df["FTA"] - df["OREB"] + df["TOV"]
    df["OppPoss"] = df["OppFGA"] + 0.44 * df["OppFTA"] - df["OppOREB"] + df["OppTOV"]
    
    # --- ADVANCED RATINGS ---
    # OFFRTG: Points Per 100 Possessions
    df["OFFRTG"] = (df["PTS"] / df["Poss"] * 100).fillna(0.0)
    
    # DEFRTG: Opp Points Per 100 Opp Possessions (Using Opp stats)
    # Note: OppPTS is not explicitly in normalize_stats, usually derived or mapped
    # If OppPTS is missing, use DefPTS logic or infer from Opp stats
    opp_pts = df.get("OppPTS", df["FGM"]*0) # Default to 0 if missing
    if "OppPTS" not in df.columns:
        # Fallback: Calculate OppPTS from components if available
        opp_pts = (df["OppFGM"] - df["Opp3PM"]) * 2 + df["Opp3PM"] * 3 + df["OppFTM"]
        
    df["DEFRTG"] = (opp_pts / df["OppPoss"] * 100).fillna(0.0)
    
    df["NETRTG"] = df["OFFRTG"] - df["DEFRTG"]
    
    # --- FOUR FACTORS & OTHERS ---
    # AST%: For Teams, this is usually % of FGs assisted
    df["AST%"] = (df["AST"] / df["FGM"] * 100).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    # OREB%: OREB / (OREB + OppDREB)
    denom_oreb = df["OREB"] + df["OppDREB"]
    df["OREB%"] = (df["OREB"] / denom_oreb * 100).fillna(0.0)
    
    # DREB%: DREB / (DREB + OppOREB)
    denom_dreb = df["DREB"] + df["OppOREB"]
    df["DREB%"] = (df["DREB"] / denom_dreb * 100).fillna(0.0)
    
    # REB%: Total Rebound Rate
    denom_reb = df["REB"] + df["OppDREB"] + df["OppOREB"]
    df["REB%"] = (df["REB"] / denom_reb * 100).fillna(0.0)
    
    # USG% -> Calculate if Lineup Team Stats are available
    if "TmFGA" in df.columns:
        tm_poss = df["TmFGA"] + 0.44 * df["TmFTA"] + df["TmTOV"] # Simplified
        df["USG%"] = (df["Poss"] / tm_poss.replace(0, 1) * 100).fillna(0.0)
    else:
        # Default to 0 or leave existing? Leave existing if not 100.
        # But for Teams, it might differ. Keeping it safe:
        # If no TmFGA, maybe it IS a team row?
        # But get_daily_stats works on players. 
        # Leaving it generic:
        pass
    
    # AST/TO
    df["AST/TO"] = (df["AST"] / df["TOV"]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    
    # PIE for Teams: (Team Stats) / (Team + Opp Stats)
    # Num
    pie_num = df["PTS"] + df["FGM"] + df["FTM"] - df["FGA"] - df["FTA"] + df["DREB"] + (0.5 * df["OREB"]) + \
              df["AST"] + df["STL"] + (0.5 * df["BLK"]) - df["PF"] - df["TOV"]
    
    # Denom (Game Total) -> Need Opponent counterparts
    opp_pie_sum = opp_pts + df["OppFGM"] + df["OppFTM"] - df["OppFGA"] - df["OppFTA"] + df["OppDREB"] + (0.5 * df["OppOREB"]) + \
                  df["OppAST"] + df["OppSTL"] + (0.5 * df["OppBLK"]) - df["OppPF"] - df["OppTOV"]
                  
    pie_den = pie_num + opp_pie_sum
    df["PIE"] = (pie_num / pie_den * 100).fillna(0.0)
    
    # GmScr doesn't apply to teams usually, but we can compute aggregate
    df["GmScr"] = df["PTS"] + 0.4 * df["FGM"] - 0.7 * df["FGA"] - 0.4 * (df["FTA"] - df["FTM"]) + \
                  0.7 * df["OREB"] + 0.3 * df["DREB"] + df["STL"] + 0.7 * df["AST"] + 0.7 * df["BLK"] - \
                  0.4 * df["PF"] - df["TOV"]

    # Rounding
    pct_cols = ["FG%", "2P%", "3P%", "FT%", "eFG%", "TS%", "USG%", "AST%", "OFFRTG", "DEFRTG", "NETRTG", "PIE", "GmScr", "AST/TO", "OREB%", "DREB%", "REB%"]
    # Filter only existing columns
    final_cols = [c for c in pct_cols if c in df.columns]
    df[final_cols] = df[final_cols].round(1)
    
    return df

def format_mins(val):
    """Format float minutes to MM:SS"""
    try:
        mins = int(val)
        secs = int(round((val - mins) * 60))
        if secs == 60:
            mins += 1
            secs = 0
        return f"{mins:02d}:{secs:02d}"
    except:
        return "00:00"

def apply_standard_stat_formatting(df, per_game=False):
    """
    Apply a consistent rounding and casting policy based on metric type.
    - Counting Stats (PTS, REB, etc.): Integer for totals, 1-decimal for per_game.
    - Rate Stats (%, Efficiency, Ratings): Always 1-decimal.
    """
    if df.empty: return df
    
    # Define categories
    counting_stats = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "2PM", "2PA", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "FD", "Eff", "+/-"]
    rate_stats = ["FG%", "2P%", "3P%", "FT%", "eFG%", "TS%", "USG%", "AST%", "OFFRTG", "DEFRTG", "NETRTG", "PIE", "GmScr", "AST/TO", "FIC"]
    
    for col in df.columns:
        # 1. Match against internal names or display names (totals/per_game maps)
        internal_col = None
        for k, v in TOTALS_MAP.items():
            if col == k or col == v: 
                internal_col = k
                break
        
        if not internal_col:
            for k, v in PER_GAME_MAP.items():
                if col == k or col == v:
                    internal_col = k
                    break
        
        target = internal_col if internal_col else col
        
        # 2. Apply rules
        if target in counting_stats:
            if per_game:
                df[col] = df[col].astype(float).round(1)
            else:
                # Use round(0) then int to avoid display issues with .0
                df[col] = df[col].astype(float).round(0).astype(int)
        elif target in rate_stats:
            df[col] = df[col].astype(float).round(1)
            
    return df

def prepare_display_data(df, mode="Standard", entity_type="Player", per_game=False):
    """
    Select and Rename columns for display.
    mode: 'Standard' or 'Advanced'
    entity_type: 'Player' or 'Team'
    per_game: If True, uses PER_GAME_MAP for renaming, else TOTALS_MAP
    """
    df = df.copy()
    
    # 1. Apply formatting first (internal column names)
    # Use the universal rounding function
    mode_arg = "per_game" if per_game else "totals"
    df = apply_stat_rounding(df, mode=mode_arg)
    
    # 2. Select renaming map
    rename_map = PER_GAME_MAP if per_game else TOTALS_MAP
    
    if mode == "Standard":
        cols = ["GP", "No", "Player", "Team", "MIN_CALC", "PTS", "FGM", "FGA", "FG%", "2PM", "2PA", "2P%", 
                "3PM", "3PA", "3P%", "TSA", "TS%", "FTA", "FTM", "OREB", "DREB", "REB", 
                "AST", "STL", "TOV", "AST/TO", "BLK", "PF", "FD", "Eff"]
        
        if entity_type == "Team":
            cols = [c for c in cols if c not in ["No", "Player"]]
            if "Team" not in cols: cols.insert(0, "Team")

        cols = [c for c in cols if c in df.columns]
        out = df[cols].copy()
        out = out.rename(columns=rename_map)
        return out
        
    elif mode == "Advanced":
        cols = ["Player", "Team", "MIN_CALC", "OFFRTG", "DEFRTG", "NETRTG", "AST%", "USG%", "TS%", "eFG%", "PIE", "GmScr"] 
        
        if entity_type == "Team":
            cols = [c for c in cols if c not in ["Player", "PIE", "GmScr"]]
        
        cols = [c for c in cols if c in df.columns]
        out = df[cols].copy()
        out = out.rename(columns=rename_map)
        return out
        
    return df

def generate_match_narrative(match_data):
    """
    Generate a short natural language summary of the match.
    Ex: "India won by 12 points. Led by Player X (25 pts). Dominated the boards (+15 REB)."
    """
    try:
        t1_name = match_data['Teams']['t1']
        t2_name = match_data['Teams']['t2']
        s1 = match_data['TeamStats']['t1'].get("PTS", 0)
        s2 = match_data['TeamStats']['t2'].get("PTS", 0)
        
        diff = s1 - s2
        if diff == 0:
            return "The match ended in a draw."
        
        winner = t1_name if diff > 0 else t2_name
        margin = abs(diff)
        w_key = 't1' if diff > 0 else 't2'
        l_key = 't2' if diff > 0 else 't1'
        
        # 1. Base Sentence
        narrative = f"{winner} won by {margin} point{'s' if margin != 1 else ''}."
        
        # 2. Key Player (Top Scorer of Winner)
        best_p = None
        max_pts = -1
        for p, s in match_data['PlayerStats'].items():
            if s.get("Team") == winner:
                pts = s.get("PTS", 0)
                if pts > max_pts:
                    max_pts = pts
                    best_p = p
        
        if best_p:
            narrative += f" Led by {best_p} ({max_pts} pts)."
            
        # 3. Key Stat (Shooting, Rebounding, or Defense)
        stats_w = match_data['TeamStats'][w_key]
        stats_l = match_data['TeamStats'][l_key]
        
        # Check domination factors
        rebs_w = stats_w.get("REB", 0)
        rebs_l = stats_l.get("REB", 0)
        reb_diff = rebs_w - rebs_l
        
        ast_w = stats_w.get("AST", 0)
        
        fg_w = stats_w.get("FG%", 0)
        fg_l = stats_l.get("FG%", 0)
        
        # Pick the most impressive one
        context_added = False
        
        if reb_diff > 10:
            narrative += f" {winner} dominated the boards (+{reb_diff} REB)."
            context_added = True
        elif (fg_w - fg_l) > 10:
            narrative += f" Shot efficiently ({fg_w:.1f}% vs {fg_l:.1f}%)."
            context_added = True
        elif ast_w > 20:
             narrative += f" Displayed great ball movement ({ast_w} AST)."
             context_added = True
             
        return narrative
        
    except Exception as e:
        return ""

def get_daily_stats(match_list, period="Full Game"):
    """Flat-map all player performances from a list of matches with date context."""
    if not match_list: return pd.DataFrame()
    
    records = []
    for m in match_list:
        meta = m.get("Metadata", {})
        date = meta.get("MatchDate", "Unknown")
        cat = m.get("Category", "Unknown")
        teams = m.get("Teams", {})
        match_id = m.get("MatchID", "Unknown")
        
        # Determine which stats to use based on period
        if period == "Full Game":
            stats_dict = m.get("PlayerStats", {})
        elif period in ["Q1", "Q2", "Q3", "Q4"]:
            # Get period-specific stats (Q1, Q2, Q3, Q4)
            # PeriodStats structure: { "Q1": { "Player Name": {stats}, ... }, "Q2": {...}, ... }
            period_stats = m.get("PeriodStats", {})
            stats_dict = period_stats.get(period, {})
        elif period == "1st Half":
            # Combine Q1 + Q2
            period_stats = m.get("PeriodStats", {})
            q1_stats = period_stats.get("Q1", {})
            q2_stats = period_stats.get("Q2", {})
            stats_dict = combine_period_stats([q1_stats, q2_stats])
        elif period == "2nd Half":
            # Combine Q3 + Q4
            period_stats = m.get("PeriodStats", {})
            q3_stats = period_stats.get("Q3", {})
            q4_stats = period_stats.get("Q4", {})
            stats_dict = combine_period_stats([q3_stats, q4_stats])
        else:
            stats_dict = {}
        
        for p_name, s in stats_dict.items():
            # Check if player has any recorded stats (PTS, REB, AST, etc.)
            # This ensures we include players who played but have 0 minutes recorded (common in partial data)
            has_stats = False
            check_cols = ["PTS", "REB", "AST", "STL", "BLK", "TOV", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "MIN_DEC", "MIN_CALC", "Mins"]
            
            for k in check_cols:
                val = s.get(k, 0)
                try:
                    # Handle numbers and strings
                    if val and float(val) > 0:
                        has_stats = True
                        break
                except (ValueError, TypeError):
                    continue
            
            # DEBUG: KEEP ALL PLAYERS
            if True:
                row = s.copy()
                row["Date"] = date
                row["Category"] = cat
                row["Match"] = f"{teams.get('t1')} vs {teams.get('t2')}"
                row["Opponent"] = teams.get("t2") if s.get("Team") == teams.get("t1") else teams.get("t1")
                row["MatchID"] = match_id
                records.append(row)
                
    if not records: return pd.DataFrame()
    
    df = pd.DataFrame(records)
    df = normalize_stats(df)
    df = calculate_derived_stats(df)
    return df

def combine_period_stats(period_list):
    """Combine stats from multiple periods (e.g., Q1+Q2 for 1st Half)."""
    combined = {}
    
    for period_stats in period_list:
        for player_name, stats in period_stats.items():
            if player_name not in combined:
                combined[player_name] = stats.copy()
            else:
                # Sum up counting stats
                for key, value in stats.items():
                    if key in ["Team", "No", "Jersey"]:
                        # Keep non-numeric fields from first occurrence
                        continue
                    elif isinstance(value, (int, float)):
                        # Skip Rate Stats / Percentages - they should be recalculated
                        if key.endswith("%") or key in ["OFFRTG", "DEFRTG", "NETRTG", "USG%", "AST%", "OREB%", "DREB%", "REB%", "TS%", "eFG%", "Eff", "GmScr", "PIE", "AST/TO"]:
                            continue
                        combined[player_name][key] = combined[player_name].get(key, 0) + value
    
    return combined
