"""Tournament-level data aggregation for players and teams."""
import streamlit as st
import pandas as pd
import numpy as np
from src import analytics as ant


@st.cache_data
def get_tournament_aggregates_v12(match_list):
    """Aggregate stats across all matches for Players and Teams."""
    if not match_list:
        return pd.DataFrame(), pd.DataFrame()
    
    p_recs, t_recs = [], []
    
    for m in match_list:
        mid = m.get("MatchID")
        # Player Stats
        for p, s in m.get('PlayerStats', {}).items():
            r = s.copy()
            r['Player'] = p
            r['MatchID'] = mid
            p_recs.append(r)
            
        # Team Stats (Enriched with Tm/Opp context for Advanced Stats)
        ts = m.get('TeamStats', {})
        tn = m.get('Teams', {})
        if 't1' in ts and 't2' in ts:
            s1 = ts['t1'].copy()
            s2 = ts['t2'].copy()
            
            # Helper to enrich (adds Tm/Opp context while preserving base stats)
            def enrich(base, self_stats, opp_stats):
                # Keep original stats (these are what we aggregate)
                # base already has PTS, FGM, FGA, 3PM, 3PA, etc from the copy
                
                # Add Tm prefix (for downstream calculations if needed)
                for k, v in self_stats.items():
                    if isinstance(v, (int, float)):
                        base[f"Tm{k}"] = v
                        
                # Add Opp prefix  
                for k, v in opp_stats.items():
                    if isinstance(v, (int, float)):
                        base[f"Opp{k}"] = v
                return base

            # T1
            s1 = enrich(s1, ts['t1'], ts['t2'])
            s1['Team'] = tn.get('t1', 'Unknown')
            s1['MatchID'] = mid
            t_recs.append(s1)
            
            # T2
            s2 = enrich(s2, ts['t2'], ts['t1'])
            s2['Team'] = tn.get('t2', 'Unknown')
            s2['MatchID'] = mid
            t_recs.append(s2)
            
    # Process Players
    if p_recs:
        df_p = pd.DataFrame(p_recs)
        
        # Ensure standard columns are numeric BEFORE aggregation
        numeric_targets = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "2PM", "2PA", 
                          "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "FD", 
                          "BLKR", "2CP", "MIN_CALC", "MIN_DEC"]
        for c in numeric_targets:
            if c in df_p.columns:
                df_p[c] = pd.to_numeric(df_p[c], errors='coerce').fillna(0.0)
        
        # Map MIN_DEC to MIN_CALC if exists
        if "MIN_DEC" in df_p.columns:
            df_p["MIN_CALC"] = df_p["MIN_DEC"]
            
        df_p = ant.normalize_stats(df_p)
        
        # Meta: Team, No (Take First)
        meta = df_p.groupby('Player')[['Team', 'No']].first()
        
        # GP (Games Played)
        gp = df_p.groupby('Player')['MatchID'].nunique()
        gp.name = "GP"
        
        # Sum Numerics
        numeric_cols = df_p.select_dtypes(include=np.number).columns
        df_p_agg = df_p.groupby('Player')[numeric_cols].sum()
        
        # Merge
        df_final_p = pd.concat([df_p_agg, meta, gp], axis=1).reset_index()
    else:
        df_final_p = pd.DataFrame()
        
    # Process Teams
    if t_recs:
        df_t = pd.DataFrame(t_recs)
        
        # Ensure numeric
        numeric_targets_t = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "2PM", "2PA", 
                            "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "FD", 
                            "BLKR", "2CP", "MIN_CALC"]
        for c in numeric_targets_t:
            if c in df_t.columns:
                df_t[c] = pd.to_numeric(df_t[c], errors='coerce').fillna(0.0)

        # normalize_stats handles missing cols
        df_t = ant.normalize_stats(df_t)
        
        gp_t = df_t.groupby('Team')['MatchID'].nunique()
        gp_t.name = "GP"
        
        numeric_cols_t = df_t.select_dtypes(include=np.number).columns
        df_t_agg = df_t.groupby('Team')[numeric_cols_t].sum()
        
        df_final_t = pd.concat([df_t_agg, gp_t], axis=1).reset_index()
        # Default Team Minutes to GP * 40 (Standard Game Duration)
        df_final_t["MIN_CALC"] = df_final_t["GP"] * 40.0
    else:
        df_final_t = pd.DataFrame()
        
    return df_final_p, df_final_t
