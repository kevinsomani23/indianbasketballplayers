
import pandas as pd
import numpy as np
import streamlit as st
import src.analytics as ant

class MetricsEngine:
    """
    Centralized engine for calculating player and team statistics.
    Focuses on robust aggregation and advanced metric formulas (USG%, PIE, FIC).
    """

    @staticmethod
    @st.cache_data(show_spinner=False)
    def get_tournament_stats(raw_data, period="Full Game", entity_type="Players"):
        """
        Main entry point to get aggregated tournament stats.
        Handles the complex logic of "Active Game Totals" for USG%.
        """
        # 1. Get Daily Stats (Player-Game Level)
        df_daily = ant.get_daily_stats(raw_data, period=period)
        
        if df_daily.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 2. Standardize Columns
        # Ensure we have numeric columns for aggregation
        agg_cols = ["FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DREB",
                   "REB", "AST", "TOV", "STL", "BLK", "PF", "FD", "PTS", "MIN_DEC", "Mins",
                   "OffPTS", "DefPTS", "TmPoss", "OppPoss"]
        
        for col in agg_cols:
            if col in df_daily.columns:
                df_daily[col] = pd.to_numeric(df_daily[col], errors='coerce').fillna(0)

        # Standardize ID Types to ensure Merge Works
        if "MatchID" in df_daily.columns:
            df_daily["MatchID"] = df_daily["MatchID"].astype(str)
        if "Team" in df_daily.columns:
            df_daily["Team"] = df_daily["Team"].astype(str)

        # 3. Calculate Team Totals PER GAME (Active Game Context)
        # Group by MatchID + Team
        team_game_totals = df_daily.groupby(["MatchID", "Team"])[agg_cols].sum().reset_index()
        
        # Rename to TmPrefix
        rename_dict = {col: f"Tm{col}" for col in agg_cols}
        team_game_totals_renamed = team_game_totals.rename(columns=rename_dict)
        
        # --- PLAYER AGGREGATION ---
        if entity_type == "Players":
            # DNP Filter: Remove rows where Minutes=0 and Stats=0
            # Ensure we only count actual appearances for per-game stats
            
            # Key Columns to check for activity (if they had any stat, they played)
            activity_cols = ["PTS", "REB", "AST", "STL", "BLK", "TOV", "FGA", "FTA", "PF"]
            check_cols = [c for c in activity_cols if c in df_daily.columns]
            
            if "MIN_DEC" in df_daily.columns and check_cols:
                # Calculate activity sum (absolute values just in case)
                activity_sum = df_daily[check_cols].abs().sum(axis=1)
                
                # Keep row if (Minutes > 0) OR (Activity > 0)
                # Some box scores might have 0 min but recorded a foul/stat -> Keep.
                # Some might have 1 min but 00:00 recorded -> Keep if MIN_DEC > 0.
                mask = (df_daily["MIN_DEC"] > 0) | (activity_sum > 0)
                df_daily = df_daily[mask]

            # PRE-MERGE CLEANUP: Drop conflicting Tm columns from player perfs
            cols_to_drop = [c for c in rename_dict.values() if c in df_daily.columns]
            if cols_to_drop:
                 df_daily = df_daily.drop(columns=cols_to_drop)

            # Merge Team Totals back to Player Daily Stats
            df_merged = df_daily.merge(team_game_totals_renamed, on=["MatchID", "Team"], how="left")
            
            # Calculate Daily USG% (Robust Formula)
            if "FGA" in df_merged.columns and "TmFGA" in df_merged.columns:
                t_poss = df_merged["TmFGA"] + 0.44 * df_merged["TmFTA"] + df_merged["TmTOV"]
                p_poss_raw = df_merged["FGA"] + 0.44 * df_merged["FTA"] + df_merged["TOV"]
                
                p_min = df_merged["MIN_DEC"].replace(0, 0.1)
                tm_min = df_merged["TmMIN_DEC"]
                
                usage_term = (p_poss_raw * (tm_min / 5))
                poss_term = (p_min * t_poss)
                
                df_merged["USG%_Daily"] = np.where(poss_term > 0, 100 * usage_term / poss_term, 0.0)
                df_merged["USG%_Daily"] = df_merged["USG%_Daily"].clip(0, 100.0)

            # Identity Key (Player + Team only, jersey number can vary across games)
            if "P_KEY" not in df_merged.columns:
                 df_merged["P_KEY"] = df_merged["Player"].astype(str) + "_" + df_merged["Team"].astype(str)

            # Aggregation Dictionary
            final_agg_dict = {col: "sum" for col in agg_cols if col in df_daily.columns}
            
            # Add Tm-prefixed columns
            for t_col in rename_dict.values():
                if t_col in df_merged.columns:
                    final_agg_dict[t_col] = "sum"
            
            # Add Opp-prefixed columns (for DEFRTG calculation)
            opp_cols = ["OppFGA", "OppFTA", "OppTOV", "OppOREB", "OppDREB", "OppFGM", 
                       "OppFTM", "OppAST", "OppSTL", "OppBLK", "OppPF", "OppPTS", "Opp3PM"]
            for opp_col in opp_cols:
                if opp_col in df_merged.columns:
                    final_agg_dict[opp_col] = "sum"

            df_agg = df_merged.groupby("P_KEY").agg(final_agg_dict).reset_index()
            
            # GP
            gp_series = df_merged.groupby("P_KEY")["MatchID"].nunique()
            gp_series.name = "GP"
            df_agg = df_agg.merge(gp_series, on="P_KEY", how="left")
            
            # Metadata
            meta_df = df_merged.groupby("P_KEY")[['Player', 'Team', 'No', 'Category']].first().reset_index()
            df_agg = meta_df.merge(df_agg, on="P_KEY", how="left")
            
            # Create MIN column from MIN_DEC or Mins
            if "MIN_DEC" in df_agg.columns:
                df_agg["MIN"] = df_agg["MIN_DEC"]
            elif "Mins" in df_agg.columns:
                df_agg["MIN"] = df_agg["Mins"]
            else:
                df_agg["MIN"] = 0.0
            
            # Create MIN_CALC for analytics
            df_agg["MIN_CALC"] = df_agg["MIN"]
            
            # Weighted Average USG%
            if "USG%_Daily" in df_merged.columns:
                def weighted_usg(x):
                    m = x["MIN_DEC"]
                    u = x.get("USG%_Daily", 0)
                    if m.sum() > 0:
                        return np.average(u, weights=m)
                    else:
                        return 0.0
                        
                weighted_usg_series = df_merged.groupby("P_KEY").apply(weighted_usg)
                weighted_usg_series.name = "USG_Robust"
                df_agg = df_agg.merge(weighted_usg_series, on="P_KEY", how="left")
            
            # Derived Stats
            df_agg = ant.calculate_derived_stats(df_agg)
            
            # Restore Robust USG - DISABLED
            # The calculated USG% now uses the correct formula (TmFGA/TmFTA/TmTOV instead of TmPoss)
            # if "USG_Robust" in df_agg.columns:
            #     df_agg["USG%"] = df_agg["USG_Robust"]
            #     df_agg = df_agg.drop(columns=["USG_Robust"])
            
            return df_agg, pd.DataFrame()

        # --- TEAM AGGREGATION ---
        elif entity_type == "Teams":
            # 1. Get Opponent Stats by Self-Joining team_game_totals
            # We need to know who played whom. df_daily has this info implicitly if we look at matches.
            # A better way is to iterate matches in raw_data, but here we only have df_daily.
            # In df_daily, for a MatchID, there are usually 2 Teams.
            
            # Get list of teams per match
            match_teams = team_game_totals[["MatchID", "Team"]].drop_duplicates()
            
            # Self merge on MatchID
            merged_matches = match_teams.merge(match_teams, on="MatchID", suffixes=("", "_Opp"))
            # Filter out self (Team == Team_Opp)
            merged_matches = merged_matches[merged_matches["Team"] != merged_matches["Team_Opp"]]
            
            # Now we have Map: MatchID, Team -> Team_Opp
            # Join stats
            df_team_ctx = team_game_totals.merge(merged_matches, on=["MatchID", "Team"], how="left")
            
            # Now join again to get Opponent Stats
            # We want to join df_team_ctx (MatchID, Team, Team_Opp) with team_game_totals (MatchID, Team aka Opp)
            df_full_t = df_team_ctx.merge(
                team_game_totals, 
                left_on=["MatchID", "Team_Opp"], 
                right_on=["MatchID", "Team"], 
                suffixes=("", "_Opp"),
                how="left"
            )
            
            # Rename Team_Opp back correctly or just use the _Opp columns
            # df_full_t has Columns: [Stats], Team_Opp, [Stats_Opp]
            
            # Aggregate by Team
            # T_KEY usually just Team Name + Category
            if "Category" in df_daily.columns:
                # recover category from daily
                cat_map = df_daily[["MatchID", "Category"]].drop_duplicates()
                df_full_t = df_full_t.merge(cat_map, on="MatchID", how="left")
                df_full_t["T_KEY"] = df_full_t["Category"].astype(str) + "_" + df_full_t["Team"].astype(str)
            else:
                 df_full_t["T_KEY"] = df_full_t["Team"].astype(str)

            # Define Aggregation
            # Own Stats
            t_agg_dict = {col: "sum" for col in agg_cols if col in df_full_t.columns}
            
            # Opp Stats
            opp_cols = [f"{col}_Opp" for col in agg_cols]
            for c in opp_cols:
                if c in df_full_t.columns:
                    t_agg_dict[c] = "sum"
            
            df_t_agg = df_full_t.groupby("T_KEY").agg(t_agg_dict).reset_index()
            
            # Rename Opp columns
            # Current: FGM_Opp. Desired: OppFGM
            rename_opp = {c: f"Opp{c.replace('_Opp','')}" for c in opp_cols}
            df_t_agg = df_t_agg.rename(columns=rename_opp)
            
            # Also rename Team_x back to Team?
            # We need metadata
            meta_t = df_full_t.groupby("T_KEY")[['Team', 'Category']].first().reset_index()
            # meta_t = meta_t.rename(columns={'Team_x': 'Team'}) # Already Team
            
            # GP
            gp_t = df_full_t.groupby("T_KEY")["MatchID"].nunique()
            gp_t.name = "GP"
            
            df_final_t = meta_t.merge(df_t_agg, on="T_KEY").merge(gp_t, on="T_KEY")
            
            # Prefix Own Stats with Tm? analytics.py expects straight names usually, 
            # but prepare_display_data handles renaming.
            # Actually, standard analytics expects FGM, FGA etc. for own stats.
            
            # Calculate Derived
            # For Teams, we usually set MIN_CALC manually based on period
            if period == "Full Game":
                df_final_t["MIN_CALC"] = df_final_t["GP"] * 40.0
            elif "Half" in period:
                df_final_t["MIN_CALC"] = df_final_t["GP"] * 20.0
            else:
                df_final_t["MIN_CALC"] = df_final_t["GP"] * 10.0
                
            df_final_t = ant.calculate_derived_team_stats(df_final_t)
            
            return pd.DataFrame(), df_final_t

        return pd.DataFrame(), pd.DataFrame()
