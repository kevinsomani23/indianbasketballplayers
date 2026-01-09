import streamlit as st
import sys
import os
import textwrap

# Fix path for Streamlit Cloud deployment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- PAGE CONFIG ---
# Define logo path relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "web", "assets", "tappa", "logo.svg")

# Verify logo exists, otherwise use None to avoid crash
if not os.path.exists(LOGO_PATH):
    print(f"WARNING: Logo not found at {LOGO_PATH}")
    LOGO_PATH = None

try:
    st.set_page_config(
        page_title="SN25 Stats by tappa.bb",
        page_icon=LOGO_PATH,
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except Exception as e:
    st.error(f"Critical Startup Error: {e}")

# Imports AFTER page config to prevent "set_page_config not first" errors
import pandas as pd
import json
import altair as alt
import plotly.graph_objects as go
import numpy as np
try:
    import re
    import importlib
    import src.analytics as ant
    import src.ui.social_generator as sg
    import src.data_manager as dm
    from src.metrics_engine import MetricsEngine
    import src.ui.enhanced_components as ec
    from datetime import datetime
except ImportError as e:
    st.error(f"Failed to import modules: {e}")
    st.stop()

# --- INJECT ENHANCED CSS ---
if 'ec' in locals():
    ec.inject_custom_css()

# Data Loading functions moved to src.data_manager

def get_match_obj(row, raw_data_list):
    t1_s = str(row['Team A']).strip().upper()
    t2_s = str(row['Team B']).strip().upper()
    cat_s = row['Gender']
    
    for m_data in raw_data_list:
        t1_d = str(m_data['Teams']['t1']).strip().upper()
        t2_d = str(m_data['Teams']['t2']).strip().upper()
        cat_d = m_data.get('Category', '')
        
        if cat_d == cat_s:
            if (t1_s == t1_d and t2_s == t2_d) or (t1_s == t2_d and t2_s == t1_d):
                return m_data
    return None

def calculate_unified_standings(schedule_df, manual_scores, raw_data_list):
    # Initialize Teams
    teams = {} # Key: "TeamName_Gender", Value: {GP, W, L, PF, PA, Gender, Group}
    
    # 1. Initialize from Schedule (to ensure all teams exist)
    for _, row in schedule_df.iterrows():
        if pd.isna(row['Team A']): continue
        t1 = str(row['Team A']).strip().upper()
        t2 = str(row['Team B']).strip().upper()
        gender = str(row['Gender']).strip().title() # Normalize to Title Case (Men/Women)
        grp = row['Group']
        
        for t in [t1, t2]:
            key = f"{t}_{gender}"
            if key not in teams:
                teams[key] = {
                    "Team": t,
                    "Gender": gender,
                    "Group": grp,
                    "GP": 0, "W": 0, "L": 0, 
                    "PF": 0, "PA": 0, "PD": 0, "PTS": 0
                }
    
    # 2. Process Matches
    processed_matches = set()
    
    for idx, row in schedule_df.iterrows():
        if pd.isna(row['Team A']): continue
        
        mid = row['Match ID']
        if mid in processed_matches: continue
        
        t1 = str(row['Team A']).strip().upper()
        t2 = str(row['Team B']).strip().upper()
        gender = str(row['Gender']).strip().title()
        
        # Keys for Stats
        k_t1 = f"{t1}_{gender}"
        k_t2 = f"{t2}_{gender}"

        # Check for Score
        s1, s2 = None, None
        
        # A. Check Detailed Stats
        m_found = get_match_obj(row, raw_data_list)
        if m_found:
            s1 = m_found['TeamStats']['t1']['PTS']
            s2 = m_found['TeamStats']['t2']['PTS']
        else:
            # B. Check Manual Scores
            # Manual Scores keys use UPPER gender
            g_upper = gender.upper()
            
            # Try Forward Key
            k1 = f"{t1}_VS_{t2}_{g_upper}"
            if manual_scores.get(k1):
                s1 = manual_scores[k1]['s1']
                s2 = manual_scores[k1]['s2']
            else:
                # Try Reverse Key
                k2 = f"{t2}_VS_{t1}_{g_upper}"
                if manual_scores.get(k2):
                    s1 = manual_scores[k2]['s2']
                    s2 = manual_scores[k2]['s1']
        
        if s1 is not None and s2 is not None:
            # Update Stats
            processed_matches.add(mid)
            
            # Team 1
            if k_t1 in teams:
                teams[k_t1]['GP'] += 1
                teams[k_t1]['PF'] += s1
                teams[k_t1]['PA'] += s2
                if s1 > s2: 
                    teams[k_t1]['W'] += 1
                    teams[k_t1]['PTS'] += 2
                else: 
                    teams[k_t1]['L'] += 1
                    teams[k_t1]['PTS'] += 1
            
            # Team 2
            if k_t2 in teams:
                teams[k_t2]['GP'] += 1
                teams[k_t2]['PF'] += s2
                teams[k_t2]['PA'] += s1
                if s2 > s1: 
                    teams[k_t2]['W'] += 1
                    teams[k_t2]['PTS'] += 2
                else: 
                    teams[k_t2]['L'] += 1
                    teams[k_t2]['PTS'] += 1
                    
        # Update PD
        for t_key in [k_t1, k_t2]:
             if t_key in teams:
                 teams[t_key]['PD'] = teams[t_key]['PF'] - teams[t_key]['PA']

    return list(teams.values())

def get_mvp_simple(m):
    # Find player with max GmScr
    best_p, max_v = None, -999
    for p, s in m.get('PlayerStats', {}).items():
        v = s.get("GmScr", 0)
        if v > max_v:
            max_v = v
            best_p = p
    return best_p, max_v

def render_match_row(row, m_found, idx, key_prefix="sch"):
    if pd.isna(row['Team A']):
        st.markdown(f"<div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 20px; font-weight: bold; color: var(--tappa-orange); text-transform: uppercase; letter-spacing: 0.2rem; filter: drop-shadow(0 0 5px var(--tappa-orange-glow));'>{row['Court']} - {row['Match ID']}</div>", unsafe_allow_html=True)
        return

    logos = dm.load_logos()
    manual_scores = dm.load_manual_scores()
    match_id = str(m_found['MatchID']) if m_found else None
    
    # Extract Team Details
    t1_name, t2_name = str(row['Team A']).strip(), str(row['Team B']).strip()
    t1_logo = logos.get(t1_name, "")
    t2_logo = logos.get(t2_name, "")
    
    # Check manual scores if not found in scraped data
    m_score = None
    if not m_found:
        m_key = f"{t1_name.upper()}_VS_{t2_name.upper()}_{row['Gender'].upper()}"
        m_score = manual_scores.get(m_key)
        # Try reverse key too
        if not m_score:
            m_key_rev = f"{t2_name.upper()}_VS_{t1_name.upper()}_{row['Gender'].upper()}"
            m_score = manual_scores.get(m_key_rev)
            if m_score:
                # Swap scores if reversed
                m_score = {'s1': m_score['s2'], 's2': m_score['s1'], 'id': m_score['id']}

    # TV Scoreboard Style
    with st.container():
        # Outer Card
        is_indoor = "INDOOR" in str(row['Court']).upper()
        has_score = (m_found is not None) or (m_score is not None)
        
        card_bg = "rgba(255, 255, 255, 0.03)" if not has_score else ("linear-gradient(135deg, rgba(255, 133, 51, 0.1) 0%, rgba(0,0,0,0.4) 100%)" if is_indoor else "linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(0,0,0,0.4) 100%)")
        border_color = "rgba(255, 255, 255, 0.1)" if not has_score else ("#ffc107" if is_indoor else "var(--tappa-orange)")
        border_width = "1px" if not has_score else "2px"
        glow = "box-shadow: 0 0 15px rgba(255, 193, 7, 0.2);" if is_indoor and has_score else ("box-shadow: 0 0 15px rgba(255, 133, 51, 0.2);" if has_score else "")
        
        mvp_section = ""
        if m_found:
            mvp_name, mvp_val = get_mvp_simple(m_found)
            if mvp_name:
                import textwrap
                mvp_section = f"""<div style='margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;'>
<span style='font-size: 0.65rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em;'>Player of the Match</span>
<span style='font-size: 0.8rem; font-weight: 700; color: #fff;'>{mvp_name} <span style='color: var(--tappa-orange); margin-left: 5px;'>{mvp_val:.1f}</span></span>
</div>"""
        elif m_score:
             import textwrap
             mvp_section = f"""<div style='margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); text-align: center;'>
<span style='font-size: 0.65rem; color: #666; text-transform: uppercase; letter-spacing: 0.05em;'>Full Statistics Not Available</span>
</div>"""

        # Score formatting
        if m_found:
            score_html = f"<span style='font-family: \"Outfit\", sans-serif; font-weight: 900; font-size: 2.2rem; color: var(--tappa-orange); letter-spacing: 0.05em;'>{m_found['TeamStats']['t1']['PTS']} - {m_found['TeamStats']['t2']['PTS']}</span>"
        elif m_score:
            score_html = f"<span style='font-family: \"Outfit\", sans-serif; font-weight: 900; font-size: 2.2rem; color: var(--tappa-orange); letter-spacing: 0.05em;'>{m_score['s1']} - {m_score['s2']}</span>"
        else:
            score_html = "<span style='color: #444; font-size: 1.2rem; font-weight: 800; font-family: \"Montserrat\", sans-serif;'>VS</span>"

        import textwrap
        st.markdown(f"""<div style='background: {card_bg}; border: {border_width} solid {border_color}; border-radius: 16px; padding: 20px; margin-bottom: 20px; transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); {glow}'>
<div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;'>
<div style='display: flex; flex-direction: column;'>
<span style='font-size: 0.7rem; color: #aaa; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;'>{row['Time']} • {row['Court']}</span>
<span style='font-size: 0.6rem; color: #666;'>ID: {row['Match ID']} | GROUP {row['Group']}</span>
</div>
<div style='background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: 4px; font-size: 0.65rem; font-weight: 700; color: #aaa; border: 1px solid rgba(255,255,255,0.1);'>
{row['Gender'].upper()}
</div>
</div>
<div style='display: flex; align-items: center; justify-content: center; gap: 30px;'>
<div style='flex: 1; display: flex; flex-direction: column; align-items: center; text-align: center;'>
<img src='{t1_logo}' style='width: 48px; height: 48px; object-fit: contain; margin-bottom: 8px; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));' />
<span style='font-family: "Montserrat", sans-serif; font-weight: 700; font-size: 0.9rem; color: #fff;'>{t1_name}</span>
</div>
<div style='display: flex; flex-direction: column; align-items: center; min-width: 100px;'>
{score_html}
</div>
<div style='flex: 1; display: flex; flex-direction: column; align-items: center; text-align: center;'>
<img src='{t2_logo}' style='width: 48px; height: 48px; object-fit: contain; margin-bottom: 8px; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));' />
<span style='font-family: "Montserrat", sans-serif; font-weight: 700; font-size: 0.9rem; color: #fff;'>{t2_name}</span>
</div>
</div>
{mvp_section}
</div>""", unsafe_allow_html=True)

        if match_id:
            # Use a clever column layout for the button to make it look part of the card
            _, btn_col, _ = st.columns([0.3, 0.4, 0.3])
            with btn_col:
                if st.button("📊 View Full Analytics", key=f"{key_prefix}_{row['Match ID']}_{idx}", use_container_width=True):
                    st.session_state.active_tab = "MATCH DASHBOARD"
                    st.session_state.jump_to_match = match_id
                    st.rerun()

def render_schedule_table(filtered_sch, raw_data_all, key_prefix="sch"):
    if filtered_sch.empty:
        st.info("No matches match the selected filters.")
        return

    import textwrap
    
    # Custom CSS for the grid-based table
    st.markdown("""
    <style>
    .sch-row {
        background: rgba(255,255,255,0.03); 
        border-bottom: 1px solid rgba(255,255,255,0.05);
        padding: 10px 0;
        transition: background 0.2s;
    }
    .sch-row:hover {
        background: rgba(255,255,255,0.06);
    }
    .sch-header {
        background: rgba(255,133,51,0.08);
        border-bottom: 2px solid var(--tappa-orange);
        padding: 10px 0;
        font-weight: bold;
        color: #888;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .sch-cell {
        display: flex;
        align-items: center;
        height: 100%;
        padding-left: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header Row
    c1, c2, c3, c4, c5, c6 = st.columns([0.5, 1.2, 2.5, 0.6, 1.2, 1])
    
    with c1: st.markdown("<div class='sch-header' style='padding-left:10px;'>ID</div>", unsafe_allow_html=True)
    with c2: st.markdown("<div class='sch-header'>Time / Court</div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='sch-header'>Matchup</div>", unsafe_allow_html=True)
    with c4: st.markdown("<div class='sch-header'>Group</div>", unsafe_allow_html=True)
    with c5: st.markdown("<div class='sch-header'>Result</div>", unsafe_allow_html=True)
    with c6: st.markdown("<div class='sch-header'>Action</div>", unsafe_allow_html=True)
    
    manual_scores = dm.load_manual_scores()
    
    # Data Rows
    for idx, row in filtered_sch.iterrows():
        if pd.isna(row['Team A']):
            continue
            
        m_found = get_match_obj(row, raw_data_all)
        t1_name, t2_name = str(row['Team A']).strip(), str(row['Team B']).strip()
        
        # Time Logic
        t_val = row['Time']
        if pd.isna(t_val) or str(t_val).lower() == 'nan' or str(t_val).strip() == '':
            t_val = "TBD"
        
        # Score Logic
        score_text = "VS"
        status_color = "#666"
        status_text = "SCHEDULED"
        
        if m_found:
            score_text = f"{m_found['TeamStats']['t1']['PTS']} - {m_found['TeamStats']['t2']['PTS']}"
            status_text = "FINAL (STATS)"
            status_color = "#4CAF50"
        else:
            m_key = f"{t1_name.upper()}_VS_{t2_name.upper()}_{row['Gender'].upper()}"
            m_score = manual_scores.get(m_key)
            if not m_score:
                m_key_rev = f"{t2_name.upper()}_VS_{t1_name.upper()}_{row['Gender'].upper()}"
                m_score = manual_scores.get(m_key_rev)
                if m_score:
                    score_text = f"{m_score['s2']} - {m_score['s1']}"
                    status_text = "FINAL"
                    status_color = "#FF9800"
            else:
                score_text = f"{m_score['s1']} - {m_score['s2']}"
                status_text = "FINAL"
                status_color = "#FF9800"
        
        # Row Container
        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([0.5, 1.2, 2.5, 0.6, 1.2, 1])
            
            # ID
            with c1: 
                st.markdown(f"<div class='sch-cell' style='font-family:\"Outfit\"; font-weight:700; color:#555;'>{row['Match ID']}</div>", unsafe_allow_html=True)
            
            # Time/Court
            with c2:
                st.markdown(f"""
                <div class='sch-cell' style='display:flex; flex-direction:column; align-items:flex-start; justify-content:center;'>
                    <div style='font-size: 0.85rem; font-weight: 600;'>{t_val}</div>
                    <div style='font-size: 0.65rem; color: #888;'>{row['Court']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Matchup
            with c3:
                st.markdown(f"""
                <div class='sch-cell' style='display:flex; flex-direction:column; align-items:flex-start; justify-content:center;'>
                     <div style='display: flex; align-items: center; gap: 8px;'>
                        <span style='font-weight: 700; font-size: 0.9rem; color: #fff;'>{t1_name}</span>
                        <span style='color: #444; font-size: 0.65rem; font-weight: 900;'>VS</span>
                        <span style='font-weight: 700; font-size: 0.9rem; color: #fff;'>{t2_name}</span>
                    </div>
                    <div style='font-size: 0.65rem; color: #666; text-transform: uppercase;'>{row['Gender']} Division</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Group
            with c4:
                st.markdown(f"<div class='sch-cell' style='color:#aaa; font-size:0.8rem;'>{row['Group']}</div>", unsafe_allow_html=True)
            
            # Result
            with c5:
                st.markdown(f"""
                <div class='sch-cell' style='display:flex; flex-direction:column; align-items:flex-start; justify-content:center;'>
                    <div style='font-family:\"Outfit\"; font-weight:900; color:var(--tappa-orange); font-size:1.1rem;'>{score_text}</div>
                    <div style='font-size:0.6rem; color:{status_color}; font-weight:700;'>{status_text}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Action (Button)
            with c6:
                if m_found:
                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True) # Spacer
                    if st.button("📊 Stats", key=f"{key_prefix}_btn_stats_{row['Match ID']}_{idx}", use_container_width=True):
                        st.session_state.active_tab = "MATCH DASHBOARD"
                        # Assuming m_found has 'MatchId' or similar from raw_data
                        # raw_data matches usually have 'MatchId' at root or similar? 
                        # Actually get_match_obj returns the FULL stats object. 
                        # It should have 'MatchId' or we use the loop key?
                        # Let's assume 'MatchId' exists in the object or use row['Match ID'] mapping if needed.
                        # The existing code used `row['Match ID']` for jump_to_match primarily? 
                        # No, previously it passed `match_id` variable which came from where?
                        # Ah, the previous card implementation used `match_id` variable.
                        # Let's check `get_match_obj` return structure if possible or just try to be safe.
                        # Standard raw data usually has 'MatchId'.
                        # If not, we can try to use the schedule ID but that needs mapping.
                        # But `get_match_obj` returns the FULL stats object. 
                        # To jump to it, we need the ID that the dashboard uses to look it up.
                        # The dashboard uses `st.session_state.jump_to_match`.
                        # Let's assume for now we pass the Schedule ID and the dashboard handles mapping?
                        # Or we pass the ID from `m_found` if available.
                        
                        target_id = m_found.get('MatchId')
                        st.session_state.jump_to_match = str(target_id) if target_id else str(row['Match ID'])
                        st.rerun()
                else:
                    st.markdown("<div class='sch-cell' style='color:#444; font-size:0.7rem;'>-</div>", unsafe_allow_html=True)

        st.markdown("<div style='border-bottom: 1px solid rgba(255,255,255,0.05);'></div>", unsafe_allow_html=True)

def style_rankings(df, title):
    if df.empty: return f"<div style='padding:10px;'>No {title} Data</div>"
    st.markdown(f"<h5 style='color: var(--tappa-orange); font-family: \"Space Grotesk\"; margin-bottom: 10px;'>{title}</h5>", unsafe_allow_html=True)
    # Ensure columns exist
    cols = ['Rank', 'Team', 'W', 'L']
    if 'Diff' in df.columns: cols.append('Diff')
    elif '+/-' in df.columns: cols.append('+/-')
    
    disp = df[cols].copy()
    disp.columns = ['#', 'Team', 'W', 'L', '+/-']
    st.dataframe(disp, hide_index=True, use_container_width=True)




# Aggregation Logic moved to src.metrics_engine.py

def calculate_power_rankings(raw_data_list):
    # 1. Get Unified Standings (Record, PD, etc. for ALL teams)
    # Note: We need schedule_df and manual_scores here.
    # Ideally, we should pass them in, but for backward compatibility, load them here if needed.
    df_sch = dm.load_schedule()
    manual_scores = dm.load_manual_scores()
    unified_standings = calculate_unified_standings(df_sch, manual_scores, raw_data_list)
    df_unified = pd.DataFrame(unified_standings)
    
    if df_unified.empty:
        return pd.DataFrame()

    # 2. Get Advanced Stats for teams that have them
    # We want Team Stats here (NetRtg, etc)
    _, df_adv = MetricsEngine.get_tournament_stats(raw_data_list, "Full Game", entity_type="Teams")
    
    # 3. Merge
    # We want a master list of all teams.
    # df_unified has: Team, Gender, Group, GP, W, L, PF, PA, PD, PTS
    # df_adv has: Team, NetRtg, PIE, TS%, etc.
    
    # Init Rankings List
    rankings = []
    
    for _, row in df_unified.iterrows():
        team = row['Team']
        
        # Base Metric (Win % + PD Factor)
        win_pct = row['W'] / row['GP'] if row['GP'] > 0 else 0
        pd_norm = row['PD'] / row['GP'] if row['GP'] > 0 else 0
        # Normalize PD: assume max PD is ~50.
        pd_score = min(max(pd_norm / 50.0, -1.0), 1.0) * 20 # +/- 20 points impact
        
        base_score = (win_pct * 60) + 20 + pd_score # 0-80 range approx
        
        # Advanced Metric Bonus
        adv_bonus = 0
        has_stats = False
        
        if not df_adv.empty and team in df_adv['Team'].values:
            has_stats = True
            adv_row = df_adv[df_adv['Team'] == team].iloc[0]
            
            # Net Rating (-30 to +30 range approx) -> +/- 10
            net = adv_row.get('NetRtg', 0)
            net_score = min(max(net / 30.0, -1.0), 1.0) * 10
            
            # PIE (0 to 20 range approx, avg 10) -> +/- 5
            # Actually PIE is % (e.g. 50%).
            pie = adv_row.get('PIE', 50)
            pie_score = ((pie - 50) / 20) * 10 # +/- 10
            
            adv_bonus = net_score + pie_score
            
            # Sanity cap
            adv_bonus = min(max(adv_bonus, -15), 15)
        
        final_score = base_score + adv_bonus
        
        rankings.append({
            "Team": team,
            "Category": row['Gender'],
            "Record": f"{row['W']}-{row['L']}",
            "W": row['W'],
            "L": row['L'],
            "Diff": row['PD'],
            "PD": row['PD'],
            "Score": round(final_score, 1),
            "HasStats": has_stats,
            "Trend": 0 # Placeholder
        })
        
    df_rank = pd.DataFrame(rankings)
    if not df_rank.empty:
        # Group sort by Category then Score to get Rank per category
        # But wait, usually we filter by category later.
        # So Rank should ideally be calculated per category?
        # The old function returned a dict by category.
        # Now we return one DF.
        # If we calculate rank globally, it mixes Men and Women.
        # We should calculate Rank per Category.
        
        df_rank = df_rank.sort_values(['Category', 'Score'], ascending=[True, False])
        df_rank['Rank'] = df_rank.groupby('Category').cumcount() + 1
        
    return df_rank


# Load Data
try:
    raw_data_dict, total_games, last_updated = dm.load_data()
    # Check if dict or list
    if isinstance(raw_data_dict, list):
        raw_data = raw_data_dict
    else:
        raw_data = raw_data_dict.get("Matches", [])
except NameError:
    # Fallback if v12 unavailable (should not happen)
    st.error("Data loader v12 not found. Please restart app.")
    raw_data = []

if not raw_data:
    st.error("Data.json not found. Please run tournament_engine.py first.")
    st.stop()


# --- HEADER & CATEGORY FILTERING ---
# Load Maps
cat_map = dm.load_category_map()
logos = dm.load_logos()

# Inject Category into raw_data
if raw_data and cat_map:
    for m in raw_data:
        mid = str(m.get("MatchID"))
        if mid in cat_map:
            m['Category'] = cat_map[mid]

# Store unfiltered data for player profiles (so game log shows all matches)
raw_data_all = raw_data.copy()



# --- HELPER: FORMATTING ---
def format_df(df, precision=0):
    """Format dataframe values based on column types and apply styling"""
    df = df.copy()
    
    # Percentage columns
    pct_cols = [c for c in df.columns if '%' in c or c in ['TS%', 'eFG%', 'FG%', '2P%', '3P%', 'FT%', 'USG%', 'AST%', 'REB%', 'OREB%', 'DREB%', 'PIE']]
    for c in pct_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').round(1)
    
    # Ratio columns
    ratio_cols = [c for c in df.columns if 'Ratio' in c or 'RATIO' in c or c == 'AST/TO']
    for c in ratio_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').round(2)
    
    # Count stats
    count_cols = ['Pts', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'OFF', 'DEF', 'PTS', 'TOV', 'PF', 'FD', '2CP', 'BLKR', '+/-', 'Eff', 'EFF', 'FIC', 'GmScr']
    # Add Opponent cols
    opp_cols = [c for c in df.columns if c.startswith('Opp') or c.startswith('Tm')]
    all_count = count_cols + opp_cols
    
    for c in all_count:
        if c in df.columns:
            if precision == 0:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
            else:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).round(precision)
                
    if 'GP' in df.columns:
        df['GP'] = pd.to_numeric(df['GP'], errors='coerce').fillna(0).astype(int)
            
    # Conditional Formatting Logic
    def highlight_exceptional(s):
        is_high = pd.Series(data=False, index=s.index)
        col = s.name
        
        # Thresholds
        try:
            # Count Stats
            if col in ["Pts", "PTS"]: is_high = s >= 20
            elif col in ["REB", "Reb", "REB%"]: is_high = s >= 10
            elif col in ["AST"]: is_high = s >= 6
            elif col in ["STL"]: is_high = s >= 4
            elif col in ["BLK"]: is_high = s >= 3
            
            # Advanced / Composite
            elif col in ["PIE"]: is_high = s >= 15
            elif col in ["GmScr"]: is_high = s >= 15
            elif col in ["FIC"]: is_high = s >= 15
            elif col in ["Eff", "EFF"]: is_high = s >= 20
            
            # Percentages
            elif col in ["FG%", "2P%"]: is_high = s >= 50.0
            elif col in ["3P%"]: is_high = s >= 40.0
            elif col in ["FT%"]: is_high = s >= 80.0
            # elif col in ["eFG%", "EFG%"]: is_high = s >= 55.0 # Optional
            # elif col in ["TS%"]: is_high = s >= 60.0 # Optional
            
        except:
            pass # Handle comparison errors
        
        return ['background-color: #1a472a; color: white; font-weight: bold' if v else '' for v in is_high]
    
    # Create a format dictionary to avoid .0 on integers
    format_dict = {}
    for col in df.columns:
        if col in pct_cols:
            format_dict[col] = "{:.1f}"
        elif col in ratio_cols:
            format_dict[col] = "{:.2f}"
        elif col in all_count or col == 'GP':
            # Check if the column actually contains floats that should be integers
            # This is important if precision was 0 during initial processing
            if pd.api.types.is_integer_dtype(df[col]):
                format_dict[col] = "{:.0f}"
            else: # If it's float (e.g., precision was not 0), format with the specified precision
                format_dict[col] = f"{{:.{precision}f}}"
        elif pd.api.types.is_numeric_dtype(df[col]):
            # Default for other numeric columns, e.g., MIN_CALC
            format_dict[col] = f"{{:.{precision}f}}"

    # Styler Definition
    styler = df.style.format(format_dict, na_rep="-")\
                     .set_properties(**{'text-align': 'center', 'vertical-align': 'middle'})\
                     .set_table_styles([
                         {'selector': 'th', 'props': [('text-align', 'center'), ('vertical-align', 'middle'), ('font-weight', 'bold')]},
                         {'selector': 'td', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]}
                     ])

    # Apply Highlight
    target_cols = ["Pts", "PTS", "REB", "AST", "STL", "BLK", "PIE", "GmScr", "FIC", "Eff", "FG%", "2P%", "3P%", "FT%"]
    existing_cols = [c for c in target_cols if c in df.columns]
    
    if existing_cols:
        styler.apply(highlight_exceptional, subset=existing_cols)
        
    return styler

# --- MAIN LAYOUT ---
c_title = st.container()
with c_title:
    col_title, col_filter = st.columns([0.7, 0.3])
    
    with col_title:
        # Get logo paths for inline display
        tappa_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "assets", "tappa", "logo.svg")
        kev_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "assets", "tappa", "thekev circ.png")
        
        # Convert logos to base64 for inline display
        import base64
        tappa_b64 = ""
        kev_b64 = ""
        
        if os.path.exists(tappa_logo):
            with open(tappa_logo, "rb") as f:
                tappa_b64 = base64.b64encode(f.read()).decode()
        
        if os.path.exists(kev_logo):
            with open(kev_logo, "rb") as f:
                kev_b64 = base64.b64encode(f.read()).decode()
        
        st.markdown(f"""<div style='text-align: center; margin-top: 0px;'>
<h1 style='margin: 0; font-family: "Space Grotesk", sans-serif; font-weight: 700; font-size: 2.2rem; letter-spacing: -0.04em; color: #ffffff !important;'>
SN25 Stats by <span style='color: var(--tappa-orange);'>tappa.bb</span>
</h1>
<p style='color: var(--text-secondary); font-size: 0.8rem; margin: 4px 0 0 0; font-family: "Space Grotesk", sans-serif; display: flex; align-items: center; justify-content: center; gap: 8px;'>
<span style='display: flex; align-items: center; gap: 4px;'>
Powered by 
<img src="data:image/svg+xml;base64,{tappa_b64}" style="height: 16px; vertical-align: middle;" />
<a href="https://www.instagram.com/tappa.bb/" target="_blank" style='color: var(--tappa-orange); font-weight: 600; text-decoration: none; display: flex; align-items: center; gap: 3px;'>
Tappa
<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
</svg>
</a>
</span>
<span style='color: rgba(255, 255, 255, 0.3);'>|</span>
<span style='display: flex; align-items: center; gap: 4px;'>
Made by 
<img src="data:image/png;base64,{kev_b64}" style="height: 16px; vertical-align: middle; border-radius: 50%;" />
<a href="https://www.instagram.com/thekevmedia/" target="_blank" style='color: #ff3333; font-weight: 600; text-decoration: none; display: flex; align-items: center; gap: 3px;'>
Kev Media
<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
</svg>
</a>
</span>
<span style='color: rgba(255, 255, 255, 0.3);'>|</span>
<span style='display: flex; align-items: center; gap: 4px;'>
Supported by 
<a href="https://www.instagram.com/nolooknationind/" target="_blank" style='color: #87CEEB; font-weight: 600; text-decoration: none; display: flex; align-items: center; gap: 3px;'>
<img src="data:image/svg+xml;base64,{ec.NNI_LOGO_B64}" style="height: 16px; vertical-align: middle;" />
NoLookNation
<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
</svg>
</a>
</span>
</p>
</div>""", unsafe_allow_html=True)
    
    with col_filter:
        st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
        cat_filter = st.radio("Tournament Category", ["All", "Men", "Women"], index=0, horizontal=True, label_visibility="visible")
        st.markdown("</div>", unsafe_allow_html=True)

# Apply category filter
if cat_filter != "All":
    raw_data = [m for m in raw_data if m.get("Category") == cat_filter]
    if not raw_data:
        st.warning(f"No matches found for category: {cat_filter}")

# Add divider below header
st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)






# --- TOP LEVEL NAVIGATION ---
if 'active_main_nav' not in st.session_state:
    st.session_state.active_main_nav = "DASHBOARD"
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "HOME"

NAV_GROUPS = {
    "DASHBOARD": ["HOME"],
    "TOURNAMENT HUB": ["SCHEDULE", "STANDINGS"],
    "GAME CENTRE": ["MATCH DASHBOARD"],
    "LEADERBOARDS": ["TOP PERFORMANCES", "TOURNAMENT STATS"],
    "PLAYER HUB": ["PLAYER PROFILE", "COMPARISON"]
}

# --- VALIDATE STATE ---
# If navigation structure changed, reset state to avoid KeyError
if st.session_state.active_main_nav not in NAV_GROUPS:
    st.session_state.active_main_nav = "DASHBOARD"
    st.session_state.active_tab = "HOME"

# Custom CSS for Navigation
st.markdown("""
    <style>
    .nav-header {
        text-align: center;
        margin-bottom: 15px;
    }
    .main-nav-container {
        display: flex;
        gap: 10px;
        padding: 6px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        backdrop-filter: blur(15px);
        margin-bottom: 8px;
    }
    .sub-nav-container {
        display: flex;
        gap: 8px;
        padding: 4px;
        background: rgba(40, 40, 40, 0.2);
        border-radius: 8px;
        margin-bottom: 20px;
    }
    /* Streamlit button overrides for navigation */
    div.stButton > button {
        border-radius: 8px !important;
        font-family: "Space Grotesk", sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        border-color: var(--tappa-orange) !important;
        color: var(--tappa-orange) !important;
        background: rgba(255, 107, 0, 0.05) !important;
        transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)

# Main Navigation Categories
cols_main = st.columns(len(NAV_GROUPS))
for i, group in enumerate(NAV_GROUPS.keys()):
    is_active = st.session_state.active_main_nav == group
    with cols_main[i]:
        if st.button(group, key=f"main_nav_{group}", use_container_width=True, 
                    type="primary" if is_active else "secondary"):
            st.session_state.active_main_nav = group
            st.session_state.active_tab = NAV_GROUPS[group][0]
            st.rerun()

# Sub-navigation for the active group
active_group_tabs = NAV_GROUPS[st.session_state.active_main_nav]
if len(active_group_tabs) > 1:
    # Small spacer
    st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
    
    # We use a slightly smaller container or fewer columns for sub-nav
    sub_cols = st.columns([1]*len(active_group_tabs) + [target for target in [8 - len(active_group_tabs)] if target > 0])
    for i, tab in enumerate(active_group_tabs):
        is_tab_active = st.session_state.active_tab == tab
        with sub_cols[i]:
            if st.button(tab, key=f"sub_nav_{tab}", use_container_width=True,
                         type="primary" if is_tab_active else "secondary"):
                st.session_state.active_tab = tab
                st.rerun()

st.markdown("<div style='height: 10px; border-bottom: 1px solid rgba(255,255,255,0.03); margin-bottom: 30px;'></div>", unsafe_allow_html=True)

# --- HOME DASHBOARD ---
if st.session_state.active_tab == "HOME":
    # 1. Headline Stats / Leaders
    st.markdown("""<div style='text-align: center; margin-bottom: 30px;'>
<h2 style='font-family: "Montserrat", sans-serif; font-weight: 900; font-size: 1.8rem; text-transform: uppercase; letter-spacing: 0.1em; background: -webkit-linear-gradient(45deg, #FF6B00, #ff9e42); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>
Tournament Overview
</h2>
<div style='height: 4px; width: 60px; background: var(--tappa-orange); margin: 8px auto; border-radius: 2px;'></div>
</div>""", unsafe_allow_html=True)
    
    # Calculate Data

    rankings = calculate_power_rankings(raw_data)
    df_p, _ = MetricsEngine.get_tournament_stats(raw_data, period="Full Game", entity_type="Players")
    
    if not df_p.empty:
        # Separate by Category
        df_men = df_p[df_p['Category'] == 'Men']
        df_women = df_p[df_p['Category'] == 'Women']

        def get_top_stat(df, col):
            return df.sort_values(by=col, ascending=False).head(3)

        # Men's Leaders
        m_pts = get_top_stat(df_men, 'PTS')
        m_reb = get_top_stat(df_men, 'REB')
        
        # Women's Leaders
        w_pts = get_top_stat(df_women, 'PTS')
        w_reb = get_top_stat(df_women, 'REB')
        
        def render_leader_card(title, rows, metric_key):
            # Use separate strings to avoid indentation issues in markdown
            html = f"<div style='background: rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px;'>"
            html += f"<h4 style='font-family: \"Space Grotesk\", sans-serif; font-weight: 700; color: var(--tappa-orange); margin-top: 0; text-transform: uppercase; font-size: 0.9rem;'>{title}</h4>"
            html += f"<div style='display: flex; flex-direction: column; gap: 12px; margin-top: 15px;'>"
            
            for i, r in rows.iterrows():
                val = int(r[metric_key])
                p_full = r['Player']
                if "(" in p_full:
                    p_name = p_full.split("(")[0].strip()
                    p_team = p_full.split("(")[1].replace(")", "").strip()
                else:
                    p_name = p_full
                    p_team = r['Team']

                html += f"<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;'>"
                html += f"<div><div style='font-family: \"Montserrat\", sans-serif; font-weight: 600; font-size: 0.95rem; color: #fff;'>{p_name}</div>"
                html += f"<div style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.75rem; color: #888;'>{p_team}</div></div>"
                html += f"<div style='font-family: \"Outfit\", sans-serif; font-size: 1.25rem; font-weight: 900; color: var(--tappa-orange);'>{val}</div></div>"
            
            html += "</div></div>"
            return html

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(render_leader_card("🔥 Men's Scoring", m_pts, "PTS"), unsafe_allow_html=True)
            st.markdown(render_leader_card("💪 Men's Rebounding", m_reb, "REB"), unsafe_allow_html=True)
        with c2:
            st.markdown(render_leader_card("🔥 Women's Scoring", w_pts, "PTS"), unsafe_allow_html=True)
            st.markdown(render_leader_card("💪 Women's Rebounding", w_reb, "REB"), unsafe_allow_html=True)
        
    
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    
    # --- MERGED HOME SECTION ---
    col_home1, col_home2 = st.columns([0.65, 0.35])
    
    with col_home1:
        st.markdown("<h4 style='font-family: \"Space Grotesk\", sans-serif; color: var(--tappa-orange); text-transform: uppercase;'>Today's Schedule & Results</h4>", unsafe_allow_html=True)
        df_sch = dm.load_schedule()
        if not df_sch.empty:
            # Filter for "Today" based on system date
            try:
                current_date = datetime.now().date()
                # Parse 'Date' column more robustly
                # Attempt explicit format first for DD-Mon-YYYY
                df_sch['Date_Parsed'] = pd.to_datetime(df_sch['Date'].astype(str).str.strip(), format='%d-%b-%Y', errors='coerce').dt.date
                
                # If NaT exists, try fallback
                if df_sch['Date_Parsed'].isna().any():
                    # Fill NaTs with flexible parser
                    mask = df_sch['Date_Parsed'].isna()
                    df_sch.loc[mask, 'Date_Parsed'] = pd.to_datetime(df_sch.loc[mask, 'Date'], errors='coerce').dt.date

                # Check for match
                matches_today = df_sch[df_sch['Date_Parsed'] == current_date]
                if not matches_today.empty:
                    day_today = matches_today.iloc[0]['Day']
                else:
                    day_today = df_sch['Day'].min()
            except Exception as e:
                # Fallback on error
                print(f"Date parsing error: {e}")
                day_today = 1
            
            # day_today = 2 (Removed hardcode) 
            today_matches = df_sch[df_sch['Day'] == day_today]
            if cat_filter != "All":
                today_matches = today_matches[today_matches['Gender'] == cat_filter]
            
            if today_matches.empty:
                st.info("No matches scheduled for today in this category.")
            else:
                # Court Wise Navigation
                courts_available = sorted(today_matches['Court'].unique().tolist())
                nav_tabs = ["ALL COURTS"] + [c.upper() for c in courts_available]
                tabs_ui = st.tabs(nav_tabs)
                
                for idx, tab in enumerate(tabs_ui):
                    with tab:
                        with st.container(height=550, border=False):
                            if idx == 0:
                                subset = today_matches
                            else:
                                target_court = courts_available[idx-1]
                                subset = today_matches[today_matches['Court'] == target_court]
                            
                            if subset.empty:
                                st.info("No matches on this court.")
                            else:
                                render_schedule_table(subset, raw_data_all, key_prefix=f"home_sch_{idx}")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("View Full Schedule", use_container_width=True, key="view_full_sch"):
                st.session_state.active_tab = "SCHEDULE"
                st.rerun()
        else:
            st.info("Schedule not available.")

    with col_home2:
        st.markdown("<h4 style='font-family: \"Space Grotesk\", sans-serif; color: var(--tappa-orange); text-transform: uppercase;'>Power Rankings</h4>", unsafe_allow_html=True)
        # Filter rankings for View
        if rankings.empty:
            r_women = pd.DataFrame()
            r_men = pd.DataFrame()
        else:
            r_women = rankings[rankings['Category'].astype(str).str.contains('Women', case=False, na=False)]
            r_men = rankings[rankings['Category'].astype(str).str.contains('Men', case=False, na=False)]

        if cat_filter == 'Women':
            style_rankings(r_women, "Women's Division")
        elif cat_filter == 'Men':
            style_rankings(r_men, "Men's Division")
        else:
            style_rankings(r_men, "Men")
            style_rankings(r_women, "Women")

    # 3. Recent Matches Ticker
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    st.markdown("""<h3 style='font-family: "Montserrat", sans-serif; font-size: 1.0rem; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px;'>
Recent Results
</h3>""", unsafe_allow_html=True)
    
    # Sort raw_data by MatchID (proxy for time) desc, take last 4
    recents = raw_data[-4:] if len(raw_data) >= 4 else raw_data
    recents = reversed(recents) # Newest first
    
    ticker_cols = st.columns(4)
    for idx, m in enumerate(recents):
        with ticker_cols[idx % 4]:
            t1 = m['Teams']['t1']
            t2 = m['Teams']['t2']
            s1 = m['TeamStats']['t1']['PTS']
            s2 = m['TeamStats']['t2']['PTS']
            date_raw = m.get('Metadata', {}).get('MatchDate', 'Jan 2025')
            # Extract simple date if format permits, else use raw
            date_disp = date_raw.split(' ')[0] if ' ' in date_raw else date_raw
            
            # Formatting
            w_team = t1 if s1 > s2 else t2
            
            # Card Style
            st.markdown(textwrap.dedent(f"""\
            <div style='background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02)); border-radius: 10px; padding: 15px; border: 1px solid rgba(255,255,255,0.08); text-align: center; transition: transform 0.2s;'>
                <div style='font-family: "Space Grotesk", sans-serif; font-size: 0.75rem; color: #aaa; margin-bottom: 8px; text-transform: uppercase;'>{date_disp}</div>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>
                    <span style='font-family: "Montserrat", sans-serif; font-weight: 700; font-size: 0.9rem; color: {"#fff" if s1 > s2 else "#888"};'>{t1}</span>
                    <span style='font-family: "Outfit", sans-serif; font-weight: 900; font-size: 1.2rem; color: {"var(--tappa-orange)" if s1 > s2 else "#fff"};'>{s1}</span>
                </div>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <span style='font-family: "Montserrat", sans-serif; font-weight: 700; font-size: 0.9rem; color: {"#fff" if s2 > s1 else "#888"};'>{t2}</span>
                    <span style='font-family: "Outfit", sans-serif; font-weight: 900; font-size: 1.2rem; color: {"var(--tappa-orange)" if s2 > s1 else "#fff"};'>{s2}</span>
                </div>
            </div>
            """), unsafe_allow_html=True)



# --- STANDINGS DASHBOARD ---
if st.session_state.active_tab == "STANDINGS":
    st.markdown("""<div style='text-align: center; margin-bottom: 30px;'>
    <h2 style='font-family: "Montserrat", sans-serif; font-weight: 900; font-size: 1.8rem; text-transform: uppercase; letter-spacing: 0.1em; background: -webkit-linear-gradient(45deg, #FF6B00, #ff9e42); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>
    Group Standings
    </h2>
    <div style='height: 4px; width: 60px; background: var(--tappa-orange); margin: 8px auto; border-radius: 2px;'></div>
    </div>""", unsafe_allow_html=True)
    
    # Calculate Unified Standings
    df_sch = dm.load_schedule()
    manual_scores_df = dm.load_manual_scores()
    standings_data = calculate_unified_standings(df_sch, manual_scores_df, raw_data_all)
    df_standings = pd.DataFrame(standings_data)
    
    if df_standings.empty:
        st.info("No standings data available.")
    else:
        # Separate by Gender
        tab_men, tab_women = st.tabs(["MEN'S DIVISION", "WOMEN'S DIVISION"])
        
        def render_group_table(df_g, group_name):
            st.markdown(f"<h4 style='color: #888; margin-top: 20px; font-family:\"Space Grotesk\";'>GROUP {group_name}</h4>", unsafe_allow_html=True)
            
            # Sort: Wins DESC, PD DESC, PF DESC
            df_g = df_g.sort_values(by=['W', 'PD', 'PF'], ascending=[False, False, False]).reset_index(drop=True)
            
            # Table Header
            st.markdown("""
            <div style='background: rgba(255,255,255,0.05); border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05);'>
                <div style='display: flex; background: rgba(255,133,51,0.1); padding: 10px; border-bottom: 2px solid var(--tappa-orange);'>
                    <div style='flex: 3; font-weight: bold; font-size: 0.8rem; color: #fff;'>TEAM</div>
                    <div style='flex: 1; text-align: center; font-weight: bold; font-size: 0.8rem; color: #aaa;'>GP</div>
                    <div style='flex: 1; text-align: center; font-weight: bold; font-size: 0.8rem; color: #fff;'>W</div>
                    <div style='flex: 1; text-align: center; font-weight: bold; font-size: 0.8rem; color: #fff;'>L</div>
                    <div style='flex: 1; text-align: center; font-weight: bold; font-size: 0.8rem; color: #aaa;'>PD</div>
                    <div style='flex: 1; text-align: center; font-weight: bold; font-size: 0.8rem; color: var(--tappa-orange);'>PTS</div>
                </div>
            """, unsafe_allow_html=True)
            
            for i, r in df_g.iterrows():
                bg = "rgba(255,255,255,0.02)" if i % 2 == 0 else "transparent"
                st.markdown(f"""
                <div style='display: flex; padding: 10px; background: {bg}; border-bottom: 1px solid rgba(255,255,255,0.03); align-items: center;'>
                    <div style='flex: 3; font-weight: 700; font-family: "Montserrat"; color: #eee;'>{r['Team']}</div>
                    <div style='flex: 1; text-align: center; color: #aaa; font-size: 0.9rem;'>{r['GP']}</div>
                    <div style='flex: 1; text-align: center; color: #4CAF50; font-weight: 700; font-size: 0.9rem;'>{r['W']}</div>
                    <div style='flex: 1; text-align: center; color: #F44336; font-weight: 700; font-size: 0.9rem;'>{r['L']}</div>
                    <div style='flex: 1; text-align: center; color: #aaa; font-size: 0.9rem;'>{r['PD']}</div>
                    <div style='flex: 1; text-align: center; color: var(--tappa-orange); font-weight: 900; font-size: 1.0rem;'>{r['PTS']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_men:
            df_m = df_standings[df_standings['Gender'] == "Men"]
            if df_m.empty:
                st.info("No Men's Data")
            else:
                groups = sorted(df_m['Group'].dropna().unique())
                cols = st.columns(2)
                for idx, g in enumerate(groups):
                    with cols[idx % 2]:
                        render_group_table(df_m[df_m['Group'] == g], g)
        
        with tab_women:
            df_w = df_standings[df_standings['Gender'] == "Women"]
            if df_w.empty:
                st.info("No Women's Data")
            else:
                groups = sorted(df_w['Group'].dropna().unique())
                cols = st.columns(2)
                for idx, g in enumerate(groups):
                    with cols[idx % 2]:
                        render_group_table(df_w[df_w['Group'] == g], g)


# --- SCHEDULE DASHBOARD ---
if st.session_state.active_tab == "SCHEDULE":
    st.markdown("""<div style='text-align: center; margin-bottom: 30px;'>
<h2 style='font-family: "Montserrat", sans-serif; font-weight: 900; font-size: 1.8rem; text-transform: uppercase; letter-spacing: 0.1em; background: -webkit-linear-gradient(45deg, #FF6B00, #ff9e42); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>
Tournament Schedule
</h2>
<div style='height: 4px; width: 60px; background: var(--tappa-orange); margin: 8px auto; border-radius: 2px;'></div>
</div>""", unsafe_allow_html=True)

    df_schedule = dm.load_schedule()
    
    if df_schedule.empty:
        st.warning("Schedule file not found.")
    else:
        # Daytime navigation strip
        st.markdown("<div style='margin-bottom: 20px;'>", unsafe_allow_html=True)
        unique_days = sorted(df_schedule['Day'].unique().tolist())
        day_cols = st.columns(len(unique_days) + 1)
        
        if 'selected_day' not in st.session_state:
            st.session_state.selected_day = "All"

        if day_cols[0].button("ALL", type="primary" if st.session_state.selected_day == "All" else "secondary", use_container_width=True):
            st.session_state.selected_day = "All"
            st.rerun()

        for d_idx, d_val in enumerate(unique_days):
            if day_cols[d_idx+1].button(f"DAY {d_val}", type="primary" if st.session_state.selected_day == d_val else "secondary", use_container_width=True):
                st.session_state.selected_day = d_val
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Small filter for Court
        courts = ["All Courts"] + sorted(df_schedule['Court'].unique().tolist())
        sel_court = st.selectbox("Court Filter", courts, label_visibility="collapsed")

        filtered_sch = df_schedule.copy()
        if st.session_state.selected_day != "All":
            filtered_sch = filtered_sch[filtered_sch['Day'] == st.session_state.selected_day]
        if sel_court != "All Courts":
            filtered_sch = filtered_sch[filtered_sch['Court'] == sel_court]
        
        # Category cross-filter (from main layout)
        if cat_filter != "All":
            filtered_sch = filtered_sch[filtered_sch['Gender'] == cat_filter]

        # Display Schedule in Compact Table View
        render_schedule_table(filtered_sch, raw_data_all)


# --- MATCH DASHBOARD ---
if st.session_state.active_tab == "MATCH DASHBOARD":
    if not isinstance(raw_data, list):
        st.error("Invalid data format. Expected list of matches.")
        st.stop()
        
    def get_quarter_scores(period_stats, t1_name, t2_name):
        """Calculate quarter-wise scores for both teams"""
        q_scores = {}
        for q, p_dict in period_stats.items():
            s1 = sum(s.get('PTS', 0) for p, s in p_dict.items() if s.get('Team') == t1_name)
            s2 = sum(s.get('PTS', 0) for p, s in p_dict.items() if s.get('Team') == t2_name)
            q_scores[q] = (s1, s2)
        return q_scores

    def calculate_four_factors(df_team, df_opp):
        """Calculate 4 Factors: eFG%, TO Ratio, OREB%, FT Rate"""
        if df_team.empty: return {}
        
        # Aggregates
        fgm = df_team['FGM'].sum()
        fga = df_team['FGA'].sum()
        pm3 = df_team['3PM'].sum()
        tov = df_team['TOV'].sum()
        oreb = df_team['OREB'].sum()
        fta = df_team['FTA'].sum()
        ftm = df_team['FTM'].sum()
        
        opp_dreb = df_opp['DREB'].sum() if not df_opp.empty else 0
        
        # 1. eFG%
        efg = ((fgm + 0.5 * pm3) / fga) * 100 if fga > 0 else 0
        
        # 2. TO Ratio (TOV per 100 Poss approx or just TOV/Poss)
        poss = fga + 0.44 * fta + tov - oreb
        to_ratio = (tov / poss * 100) if poss > 0 else 0
        
        # 3. OREB%
        oreb_pct = (oreb / (oreb + opp_dreb) * 100) if (oreb + opp_dreb) > 0 else 0
        
        # 4. FT Rate (FTM / FGA) 
        ft_rate = (ftm / fga * 100) if fga > 0 else 0
        
        return {
            "eFG%": efg,
            "TO Ratio": to_ratio,
            "OREB%": oreb_pct,
            "FT Rate": ft_rate
        }





    # Match Selector
    m_options = {f"{m['Teams']['t1']} vs {m['Teams']['t2']} ({m.get('Category', 'Unknown')})": str(m['MatchID']) for m in raw_data}
    
    if not m_options:
        st.warning("No matches found. Please check data source.")
        st.stop()
        
    # Handle jump from Schedule
    selected_index = 0
    if 'jump_to_match' in st.session_state:
        target_id = st.session_state.jump_to_match
        for idx, (label, mid) in enumerate(m_options.items()):
            if mid == target_id:
                selected_index = idx
                break
    
    sel_label = st.selectbox("Select Match", options=list(m_options.keys()), index=selected_index)
    
    # Clear jump state after selection
    if 'jump_to_match' in st.session_state:
        del st.session_state.jump_to_match

    if sel_label is None:
        st.stop()
        
    selected_id = m_options[sel_label]
    m = next(x for x in raw_data if str(x['MatchID']) == selected_id)
    
    # --- CONTEXT HEADER ---
    t1, t2 = m['Teams']['t1'], m['Teams']['t2']
    cat = m.get('Category', 'Unknown')
    # Try to parse date if available or use generic context
    context_str = f"{cat} • {t1} vs {t2}" 
    
    st.markdown(f"""<div style="margin-top: -12px; margin-bottom: 24px; text-align: left;">
        <span style="font-family: 'Space Grotesk', sans-serif; color: var(--text-secondary); font-size: 0.9rem; letter-spacing: 0.05em; text-transform: uppercase;">
            {context_str}
        </span>
    </div>""", unsafe_allow_html=True)
    
    st.divider()
    
    # --- HEADER ---
    s1, s2 = m['TeamStats']['t1']['PTS'], m['TeamStats']['t2']['PTS']
    
    # Calculate MVP (Best GmScr) - GLOBAL
    def get_mvp(team_name, stats):
        best_p, max_v = None, -999
        for p, s in stats.items():
            if s.get("Team") == team_name:
                v = s.get("GmScr", 0)
                if v > max_v: max_v = v; best_p = p
        return best_p, max_v
    
    mvp1, val1 = get_mvp(t1, m['PlayerStats'])
    mvp2, val2 = get_mvp(t2, m['PlayerStats'])
    
    # ... [SCOREBOARD CODE REMAINS UNCHANGED UP TO NEXT SECTION] ...
    
    # Bold Modern Scoreboard
    import textwrap
    st.markdown("""<div style='text-align: center; margin-bottom: 12px;'>
<h2 style='font-family: "Montserrat", sans-serif; font-weight: 900; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-secondary); margin: 0;'>
Match Scoreboard
</h2>
</div>""", unsafe_allow_html=True)
    
    col_t1, col_vs, col_t2 = st.columns([1, 0.15, 1])
    logo_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "assets", "teams")
    
    import base64

    # --- HELPER: IMAGE ENCODING ---
    def get_image_base64(path):
        """Read image file and render as base64 string"""
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        return ""
    
    with col_t1:
        winner_class = "winner-glow" if s1 > s2 else ""
        border_col = '#d16b07' if s1 > s2 else 'var(--border-glass)'

        st.markdown(textwrap.dedent(f"""\
            <div class="glass-card {winner_class}" style="text-align: center; padding: 12px; border: 2px solid {border_col};">
                <div style="margin: 0;">
                    <h3 style="font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 1rem; color: var(--text-primary); margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.05em;">
                        {t1}
                    </h3>
                    <div class="score-display" style="font-size: 3rem; font-weight: 400; line-height: 1; color: {'#ff8533' if s1 > s2 else 'var(--text-primary)'}; margin: 6px 0;">
                        {s1}
                    </div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-glass);">
                        <div class="stat-label" style="color: var(--text-muted); margin-bottom: 3px; font-size: 0.65rem;">MVP</div>
                        <div style="color: var(--text-primary); font-size: 0.85rem; font-weight: 700; font-family: 'Inter', sans-serif;">{mvp1 if mvp1 else 'N/A'}</div>
                        <div style="color: var(--tappa-orange); font-size: 0.7rem; font-weight: 600; margin-top: 2px;">{val1:.1f}</div>
                    </div>
                </div>
            </div>
        """), unsafe_allow_html=True)

    with col_vs:
        st.markdown(textwrap.dedent("""\
            <div style="display: flex; align-items: center; justify-content: center; height: 100%;">
                <div style="font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 1.5rem; color: var(--text-muted); letter-spacing: 0.05em;">VS</div>
            </div>
        """), unsafe_allow_html=True)

    with col_t2:
        winner_class = "winner-glow" if s2 > s1 else ""
        border_col = '#d16b07' if s2 > s1 else 'var(--border-glass)'
        
        st.markdown(textwrap.dedent(f"""\
            <div class="glass-card {winner_class}" style="text-align: center; padding: 12px; border: 2px solid {border_col};">
                <div style="margin: 0;">
                    <h3 style="font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 1rem; color: var(--text-primary); margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.05em;">
                        {t2}
                    </h3>
                    <div class="score-display" style="font-size: 3rem; font-weight: 400; line-height: 1; color: {'#ff8533' if s2 > s1 else 'var(--text-primary)'}; margin: 6px 0;">
                        {s2}
                    </div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-glass);">
                        <div class="stat-label" style="color: var(--text-muted); margin-bottom: 3px; font-size: 0.65rem;">MVP</div>
                        <div style="color: var(--text-primary); font-size: 0.85rem; font-weight: 700; font-family: 'Inter', sans-serif;">{mvp2 if mvp2 else 'N/A'}</div>
                        <div style="color: var(--tappa-orange); font-size: 0.7rem; font-weight: 600; margin-top: 2px;">{val2:.1f}</div>
                    </div>
                </div>
            </div>
        """), unsafe_allow_html=True)

    # --- MATCH RECAP ---
    narrative_text = ant.generate_match_narrative(m)
    if narrative_text:
        st.markdown(f"""
        <div class="glass-card" style='margin: 20px auto; padding: 16px 20px; max-width: 800px; border-left: 3px solid var(--tappa-orange);'>
            <div style='display: flex; align-items: flex-start; gap: 12px;'>
                <div style='flex-shrink: 0; margin-top: 2px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--tappa-orange)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                </div>
                <div style='flex: 1;'>
                    <div style='font-family: "Space Grotesk", sans-serif; font-size: 0.7rem; font-weight: 600; color: var(--tappa-orange); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;'>
                        Match Recap
                    </div>
                    <p style='font-family: "Space Grotesk", sans-serif; font-size: 0.9rem; color: var(--text-primary); font-weight: 400; line-height: 1.5; margin: 0;'>
                        {narrative_text}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("##### Scoreboard")
    q_scores = get_quarter_scores(m['PeriodStats'], t1, t2)
    q_data = {
        "Team": [t1, t2],
        "Q1": [q_scores.get("Q1", (0,0))[0], q_scores.get("Q1", (0,0))[1]],
        "Q2": [q_scores.get("Q2", (0,0))[0], q_scores.get("Q2", (0,0))[1]],
        "Q3": [q_scores.get("Q3", (0,0))[0], q_scores.get("Q3", (0,0))[1]],
        "Q4": [q_scores.get("Q4", (0,0))[0], q_scores.get("Q4", (0,0))[1]]
    }
    q_data["T"] = [sum(x) for x in zip(q_data["Q1"], q_data["Q2"], q_data["Q3"], q_data["Q4"])]
    q_data["T"] = [sum(x) for x in zip(q_data["Q1"], q_data["Q2"], q_data["Q3"], q_data["Q4"])]
    st.markdown(ec.render_html_scoreboard(q_data, t1, t2), unsafe_allow_html=True)

    st.divider()

    # --- FILTER SECTION ---
    # Moved inside logic below
    
    # --- SECONDARY NAVIGATION (SUB-TABS) ---
    if 'match_sub_tab' not in st.session_state:
        st.session_state.match_sub_tab = "MATCH STATS"
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    sub_tabs = ["MATCH STATS", "BOX SCORES"]
    c_sub_nav = st.container()
    with c_sub_nav:
        # Create a centered layout for the pills
        _, sub_col, _ = st.columns([0.1, 0.8, 0.1])
        with sub_col:
            sub_cols = st.columns(len(sub_tabs))
            for i, tab_name in enumerate(sub_tabs):
                is_active = st.session_state.match_sub_tab == tab_name
                btn_type = "primary" if is_active else "secondary"
                # Use the custom .sub-nav-pill class defined in CSS
                if sub_cols[i].button(tab_name, key=f"sub_nav_{tab_name}", use_container_width=True, type=btn_type, help=f"View {tab_name}"):
                    st.session_state.match_sub_tab = tab_name
                    st.rerun()
                    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # --- DATA PROCESSING ---
    raw_recs = []
    for p, s in m['PlayerStats'].items():
        s_copy = s.copy()
        s_copy['Player'] = p
        raw_recs.append(s_copy)
    # --- SUB-TAB: MATCH STATS ---
    if st.session_state.match_sub_tab == "MATCH STATS":
        st.markdown("<h4 style='font-family: \"Space Grotesk\", sans-serif; font-size: 1.1rem; margin-bottom: 16px;'>Four Factors Breakdown</h4>", unsafe_allow_html=True)
        
        # Calculate full game automatically for 4 Factors
        f_raw_recs = []
        for p, s in m['PlayerStats'].items():
            s_copy = s.copy()
            s_copy['Player'] = p
            f_raw_recs.append(s_copy)
            
        if f_raw_recs:
            df_full = pd.DataFrame(f_raw_recs)
            if "MIN_DEC" in df_full.columns: df_full["MIN_CALC"] = df_full["MIN_DEC"]
            df_full = ant.normalize_stats(df_full)
            df_full = ant.calculate_derived_stats(df_full)
            
            if 'Team' in df_full.columns:
                df_t1 = df_full[df_full['Team'] == t1]
                df_t2 = df_full[df_full['Team'] == t2]
                
                f1 = calculate_four_factors(df_t1, df_t2)
                f2 = calculate_four_factors(df_t2, df_t1)
                
                factors_data = {
                    "eFG%": [f1.get("eFG%"), f2.get("eFG%")],
                    "TO Ratio": [f1.get("TO Ratio"), f2.get("TO Ratio")],
                    "OREB%": [f1.get("OREB%"), f2.get("OREB%")],
                    "FT Rate": [f1.get("FT Rate"), f2.get("FT Rate")]
                }
                f_df = pd.DataFrame(factors_data, index=[t1, t2])
                st.markdown(ec.render_four_factors_table(f_df), unsafe_allow_html=True)
                
                st.markdown("<h4 style='font-family: \"Space Grotesk\", sans-serif; font-size: 1.1rem; margin: 32px 0 16px 0;'>Team Comparison</h4>", unsafe_allow_html=True)
                categories = ['PTS', 'REB', 'AST', 'STL', 'BLK']
                t1_vals = [df_t1[cat].sum() if cat in df_t1.columns else 0 for cat in categories]
                t2_vals = [df_t2[cat].sum() if cat in df_t2.columns else 0 for cat in categories]
                
                comparison_chart = ec.create_comparison_bar_chart(
                    categories=categories,
                    team1_values=t1_vals,
                    team2_values=t2_vals,
                    team1_name=t1,
                    team2_name=t2
                )
                st.plotly_chart(comparison_chart, use_container_width=True)
            else:
                st.warning("Team data missing.")

    # --- SUB-TAB: BOX SCORES ---
    elif st.session_state.match_sub_tab == "BOX SCORES":
        # --- PRESETS CONTROL ---
        cp1, cp2 = st.columns([1, 1.5])
        
        with cp1:
            period_mode = st.radio("Period", ["Full Game", "1st Half", "2nd Half", "Custom"], horizontal=True, key="box_period")
            
        with cp2:
            stats_view = st.radio("Stats View", ["Summary", "Advanced", "Scoring", "USG"], horizontal=True, key="box_view")
            
        # Contextual Filters
        q_curr = []
        if period_mode == "Full Game":
            q_curr = ["Q1", "Q2", "Q3", "Q4"]
        elif period_mode == "1st Half":
            q_curr = ["Q1", "Q2"]
        elif period_mode == "2nd Half":
            q_curr = ["Q3", "Q4"]
        else:
             # Custom
             c1, c2, c3, c4 = st.columns(4)
             with c1: 
                 if st.checkbox("Q1", value=True, key="q1_check"): q_curr.append("Q1")
             with c2:
                 if st.checkbox("Q2", value=True, key="q2_check"): q_curr.append("Q2")
             with c3:
                 if st.checkbox("Q3", value=True, key="q3_check"): q_curr.append("Q3")
             with c4:
                 if st.checkbox("Q4", value=True, key="q4_check"): q_curr.append("Q4")

        # Aggregation Logic
        if not q_curr:
            st.info("Select at least one period to view box scores.")
        else:
            raw_recs = []
            if set(q_curr) == {"Q1", "Q2", "Q3", "Q4"} and period_mode != "Custom":
                for p, s in m['PlayerStats'].items():
                    s_copy = s.copy()
                    s_copy['Player'] = p
                    raw_recs.append(s_copy)
            else:
                for q in q_curr:
                    q_data = m.get('PeriodStats', {}).get(q, {})
                    for p, s in q_data.items():
                        s_copy = s.copy()
                        s_copy['Player'] = p
                        raw_recs.append(s_copy)
            
            df_active = pd.DataFrame(raw_recs)
            if not df_active.empty:
                if "MIN_DEC" in df_active.columns: df_active["MIN_CALC"] = df_active["MIN_DEC"]
                df_active = ant.normalize_stats(df_active)
                
                if len(q_curr) != 4 or period_mode == "Custom":
                    num_cols = df_active.select_dtypes(include=np.number).columns
                    df_agg = df_active.groupby('Player')[num_cols].sum().reset_index()
                    df_meta = df_active.groupby('Player')[["Team", "No"]].first().reset_index()
                    df_active = pd.merge(df_agg, df_meta, on='Player')
                
                df_active = ant.calculate_derived_stats(df_active)

                # --- OUTLIER & STAR PLAYER CALCULATION ---
                # Major stats for outlier detection (including Advanced Metrics)
                major_stats = ["PTS", "REB", "AST", "STL", "BLK", "GmScr", "OFFRTG", "DEFRTG", "TS%", "eFG%", "USG%", "PIE", "FIC"]
                outlier_thresholds = {}
                
                # Calculate thresholds across ALL players in this view
                for stat in major_stats:
                    if stat in df_active.columns:
                        vals = pd.to_numeric(df_active[stat], errors='coerce').dropna()
                        if not vals.empty:
                            # Using Mean + 1.5 * StdDev as "Outlier" threshold
                            outlier_thresholds[stat] = vals.mean() + (1.5 * vals.std())
                            
                # Identify Star Players (Top 2-3 per team based on GmScr)
                star_players = []
                for team_name in [t1, t2]:
                    team_players = df_active[df_active["Team"] == team_name]
                    if not team_players.empty:
                        # Get up to 3 players with GmScr > 10 (arbitrary floor for "stars")
                        top_p = team_players.sort_values("GmScr", ascending=False).head(3)
                        # Ensure we only pick players who actually had a good game
                        top_p = top_p[top_p["GmScr"] > team_players["GmScr"].mean()]
                        star_players.extend(top_p["Player"].tolist())

                # Prepare data based on view type
                mode_arg = "Advanced" if stats_view == "Advanced" else "Standard" 
                df_disp = ant.prepare_display_data(df_active, mode_arg)
                
                # Column selection based on view (Mapping internal keys to display names)
                base_cols = ["No", "Player", "Mins"]
                from src.analytics import TOTALS_MAP
                
                # Map highlight thresholds to display names
                display_outlier_thresholds = {}
                for k, v in outlier_thresholds.items():
                    disp_k = TOTALS_MAP.get(k, k)
                    display_outlier_thresholds[disp_k] = v

                view_map = {
                    # Standard Stats Tab
                    "Summary": ["FGM", "FGA", "FG%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", 
                               "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS", "+/-", "GmScr"],
                    
                    # Advanced Stats Tab
                    "Advanced": ["OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", "AST RATIO", 
                                "OREB%", "DREB%", "REB%", "TO RATIO", "eFG%", "TS%", "USG%", "PACE", "PIE"],
                    
                    # Scoring Breakdown Tab
                    "Scoring": ["%FGA 2PT", "%FGA 3PT", "%PTS 2PT", "%PTS 2PT MR", "%PTS 3PT", 
                               "%PTS FBPS", "%PTS FT", "%PTS OFFTO", "%PTS PITP", 
                               "2FGM %AST", "2FGM %UAST", "3FGM %AST", "3FGM %UAST", 
                               "FGM %AST", "FGM %UAST"],
                    
                    # USG Tab (team-relative percentages)
                    "USG": ["USG%", "%FGM", "%FGA", "%3PM", "%3PA", "%FTM", "%FTA", 
                           "%OREB", "%DREB", "%REB", "%AST", "%TOV", "%STL", "%BLK", "%BLKA", 
                           "%PF", "%PFD", "%PTS"],
                    
                    # Keep Playmaking and Defense for backward compatibility
                    "Playmaking": ["AST", "TOV", "AST/TO", "AST%", "USG%"],
                    "Defense": ["DREB", "STL", "BLK", "PF", "DEFRTG"]
                }
                
                target_internal = view_map.get(stats_view, [])
                display_cols = list(base_cols)
                for t in target_internal:
                    disp_name = TOTALS_MAP.get(t, t)
                    if disp_name in df_disp.columns:
                        display_cols.append(disp_name)
                    elif t in df_disp.columns:
                        display_cols.append(t)
                
                final_cols = [c for c in display_cols if c in df_disp.columns]
                df_disp = df_disp[final_cols]

                # Render tables
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                
                def render_team_box(team_name):
                    players_in_team = df_active[df_active["Team"] == team_name]["Player"].unique()
                    tdf = df_disp[df_disp["Player"].isin(players_in_team)].copy()
                    if not tdf.empty:
                        st.markdown(f"<h5 style='font-family: \"Space Grotesk\", sans-serif; color: var(--tappa-orange); margin-bottom: 12px;'>{team_name}</h5>", unsafe_allow_html=True)
                        st.markdown(ec.render_html_table(
                            tdf, 
                            star_players=star_players, 
                            outlier_thresholds=display_outlier_thresholds
                        ), unsafe_allow_html=True)

                render_team_box(t1)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                render_team_box(t2)


# --- TOP PERFORMANCES ---
elif st.session_state.active_tab == "TOP PERFORMANCES":
    # UI Controls at top
    c_date, c_period = st.columns([1.5, 1.5])
    
    with c_period:
        period_sel = st.radio("Time Segment", ["Full Game", "1st Half", "2nd Half", "Q1", "Q2", "Q3", "Q4"], horizontal=True, index=0)
    
    # Aggregate all daily stats with period filter
    df_all_perfs = ant.get_daily_stats(raw_data, period=period_sel)
    
    if df_all_perfs.empty:
        if period_sel != "Full Game":
            st.info(f"Period-specific stats ({period_sel}) are not available. Please select 'Full Game' or ensure period stats are included in the data.")
        else:
            st.warning("No performance data available yet.")
    else:
        # Date Filter Control
        dates = sorted(df_all_perfs['Date'].unique(), reverse=True)
        with c_date:
            sel_date = st.selectbox("Filter by Date (Optional)", ["Whole Tournament"] + dates)
        
        # Apply date filter and determine if we should show dates in cards
        if sel_date != "Whole Tournament":
            df_view = df_all_perfs[df_all_perfs['Date'] == sel_date].copy()
            view_label = f"Performances on {sel_date}"
            show_date_in_cards = False  # Hide date when specific date is selected
        else:
            df_view = df_all_perfs.copy()
            view_label = "Tournament High"  # Changed from "Tournament Records"
            show_date_in_cards = True  # Show date for whole tournament view
            
        if df_view.empty:
            st.info(f"No match data found for the selection.")
        else:
            st.markdown(f"<h4 style='font-family: \"Space Grotesk\", sans-serif; font-size: 1.1rem; margin-bottom: 20px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em;'>{view_label}</h4>", unsafe_allow_html=True)
            
            # --- TABS FOR DIFFERENT VIEWS ---
            tab_lead, tab_std, tab_adv, tab_usg, tab_scoring = st.tabs(["LEADERBOARDS", "STANDARD STATS", "ADVANCED STATS", "USG", "SCORING"])

            # TAB 1: LEADERBOARDS (Grid)
            with tab_lead:
                # Top Highs Grid (2x3)
                r1_c1, r1_c2, r1_c3 = st.columns(3)
                with r1_c1:
                    ec.create_leader_board(df_view, "PTS", "Single Game Points", top_n=5, show_date=show_date_in_cards)
                with r1_c2:
                    if "REB" in df_view.columns:
                        ec.create_leader_board(df_view, "REB", "Single Game Boards", top_n=5, show_date=show_date_in_cards)
                with r1_c3:
                    if "AST" in df_view.columns:
                        ec.create_leader_board(df_view, "AST", "Single Game Assists", top_n=5, show_date=show_date_in_cards)
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                
                r2_c1, r2_c2, r2_c3 = st.columns(3)
                with r2_c1:
                    if "STL" in df_view.columns:
                        ec.create_leader_board(df_view, "STL", "Single Game Steals", top_n=5, show_date=show_date_in_cards)
                with r2_c2:
                    if "BLK" in df_view.columns:
                        ec.create_leader_board(df_view, "BLK", "Single Game Blocks", top_n=5, show_date=show_date_in_cards)
                with r2_c3:
                    if "GmScr" in df_view.columns:
                        ec.create_leader_board(df_view, "GmScr", "Impact (GmScr)", top_n=5, show_date=show_date_in_cards)

            # TAB 2: STANDARD STATS (Table)
            with tab_std:
                std_cols = ["Player", "Team", "Opponent", "Date", "MIN_CALC", "PTS", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", 
                           "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "DD2", "TD3", "+/-"]
                # Filter to available columns
                available_cols = [c for c in std_cols if c in df_view.columns]
                
                # Sort by PTS by default
                if "PTS" in df_view.columns:
                    df_std = df_view[available_cols].sort_values(by="PTS", ascending=False).head(100).reset_index(drop=True).copy()
                else:
                    df_std = df_view[available_cols].head(100).reset_index(drop=True).copy()
                
                # Rename MIN_CALC to Min for display BEFORE adding Rank
                if "MIN_CALC" in df_std.columns:
                    df_std = df_std.rename(columns={"MIN_CALC": "Min"})
                
                # Add Rank column
                df_std.insert(0, "Rank", range(1, len(df_std) + 1))
                
                # Round percentage columns to 1 decimal place
                pct_cols = ["FG%", "3P%", "FT%"]
                for col in pct_cols:
                    if col in df_std.columns:
                        df_std[col] = df_std[col].round(1)
                
                # Apply styling to highlight max values
                def highlight_max(s):
                    """Highlight the maximum in a Series."""
                    if s.name in ["PTS", "REB", "AST", "STL", "BLK", "FGM", "3PM", "FTM"]:
                        is_max = s == s.max()
                        return ['background-color: rgba(255, 133, 51, 0.3); font-weight: bold' if v else '' for v in is_max]
                    return ['' for _ in s]
                
                # Create format dict for percentage columns
                format_dict = {}
                for col in pct_cols:
                    if col in df_std.columns:
                        format_dict[col] = "{:.1f}"
                
                styled_df = df_std.style.apply(highlight_max).format(format_dict, na_rep="-")
                
                # Display dataframe without selection
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=600
                )

            # TAB 3: ADVANCED STATS (Table)
            with tab_adv:
                adv_cols = ["Player", "Team", "Opponent", "Date", "MIN_CALC", "OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", 
                           "AST RATIO", "OREB%", "DREB%", "REB%", "TO RATIO", "eFG%", "TS%", "USG%", "PIE", "PPoss"]
                # Filter to available columns
                available_cols = [c for c in adv_cols if c in df_view.columns]
                
                # Sort by PIE by default
                if "PIE" in df_view.columns:
                    df_adv = df_view[available_cols].sort_values(by="PIE", ascending=False).head(100).reset_index(drop=True).copy()
                else:
                    df_adv = df_view[available_cols].head(100).reset_index(drop=True).copy()
                
                # Rename MIN_CALC to MIN for display BEFORE adding Rank
                if "MIN_CALC" in df_adv.columns:
                    df_adv = df_adv.rename(columns={"MIN_CALC": "MIN"})
                
                # Add Rank column
                df_adv.insert(0, "Rank", range(1, len(df_adv) + 1))
                
                # Round numeric columns to 1 decimal place
                numeric_cols = ["OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", "AST RATIO", "OREB%", "DREB%", "REB%", 
                               "TO RATIO", "eFG%", "TS%", "USG%", "PIE", "PPoss"]
                for col in numeric_cols:
                    if col in df_adv.columns:
                        df_adv[col] = df_adv[col].round(1)
                
                # Apply styling to highlight max values
                def highlight_max(s):
                    """Highlight the maximum in a Series."""
                    if s.name in ["PIE", "OFFRTG", "NETRTG", "TS%", "eFG%"]:
                        is_max = s == s.max()
                        return ['background-color: rgba(255, 133, 51, 0.3); font-weight: bold' if v else '' for v in is_max]
                    return ['' for _ in s]
                
                # Create format dict for numeric columns
                format_dict = {}
                for col in numeric_cols:
                    if col in df_adv.columns:
                        format_dict[col] = "{:.1f}"
                
                styled_df = df_adv.style.apply(highlight_max).format(format_dict, na_rep="-")
                
                # Display dataframe without selection
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=600
                )

            # TAB 4: USG (Table)
            with tab_usg:
                # Calculate usage percentages
                df_usg = df_view.copy()
                
                # Calculate team-relative percentages
                if "Team" in df_usg.columns and "MatchID" in df_usg.columns and not df_usg.empty:
                    try:
                        # Define columns we want to aggregate - Added MIN_DEC for USG calc
                        agg_cols = ["FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DREB",
                                   "REB", "AST", "TOV", "STL", "BLK", "PF", "FD", "PTS", "MIN_DEC", "Mins"]
                        
                        # Only aggregate columns that actually exist in the full dataset
                        available_agg_cols = {col: "sum" for col in agg_cols if col in df_all_perfs.columns}
                        
                        if not available_agg_cols:
                            st.warning("No stat columns available for usage calculations.")
                        else:
                            # Standardize MatchID and Team to string to ensure correct grouping and merging
                            df_all_perfs["MatchID"] = df_all_perfs["MatchID"].astype(str)
                            df_all_perfs["Team"] = df_all_perfs["Team"].astype(str)
                            df_usg["MatchID"] = df_usg["MatchID"].astype(str)
                            df_usg["Team"] = df_usg["Team"].astype(str)

                            # Calculate team totals per game using MatchID and Team from the FULL DATASET
                            team_game_totals = df_all_perfs.groupby(["MatchID", "Team"]).agg(available_agg_cols).reset_index()
                            
                            # Rename to Tm prefix
                            rename_dict = {col: f"Tm{col}" for col in available_agg_cols.keys()}
                            team_game_totals = team_game_totals.rename(columns=rename_dict)
                            
                            # Drop any existing Tm columns from df_usg to avoid _x/_y suffixes
                            cols_to_drop = [col for col in df_usg.columns if col.startswith('Tm') and col in team_game_totals.columns]
                            if cols_to_drop:
                                df_usg = df_usg.drop(columns=cols_to_drop)
                            
                            # Merge team totals back using MatchID and Team
                            df_usg = df_usg.merge(team_game_totals, on=["MatchID", "Team"], how="left")
                            
                            # --- CALCULATE USG% ---
                            # Formula: 100 * ((FGA + 0.44*FTA + TOV) * (TmMIN / 5)) / (MIN * (TmFGA + 0.44*TmFTA + TmTOV))
                            # Ensure required columns exist
                            req_usg = ["FGA", "FTA", "TOV", "MIN_DEC", "TmFGA", "TmFTA", "TmTOV", "TmMIN_DEC"]
                            if all(c in df_usg.columns for c in req_usg):
                                try:
                                    # Player Possessions (Numerator Part 1)
                                    p_poss = df_usg["FGA"] + 0.44 * df_usg["FTA"] + df_usg["TOV"]
                                    # Team Possessions (Denominator Part 2)
                                    tm_poss = df_usg["TmFGA"] + 0.44 * df_usg["TmFTA"] + df_usg["TmTOV"]
                                    
                                    # Team Minutes (Sum of all players)
                                    tm_min = df_usg["TmMIN_DEC"]
                                    # Player Minutes - Avoid zero division
                                    p_min = df_usg["MIN_DEC"].replace(0, 1) 
                                    
                                    # Usage Rate Formula
                                    numerator = p_poss * (tm_min / 5)
                                    denominator = p_min * tm_poss
                                    
                                    # Handle bad denominators
                                    usg_raw = (numerator / denominator.replace(0, 1) * 100).fillna(0)
                                    
                                    # Filter out garbage time (less than 5 mins played)
                                    df_usg["USG%"] = usg_raw.where(df_usg["MIN_DEC"] >= 5, 0.0).round(1)
                                except Exception as e:
                                    st.warning(f"Could not calc USG%: {e}")
                            
                            # Calculate percentages only for columns that exist
                            if "FGM" in df_usg.columns and "TmFGM" in df_usg.columns:
                                df_usg["%FGM"] = (df_usg["FGM"] / df_usg["TmFGM"].replace(0, 1) * 100).fillna(0).round(1)
                            if "FGA" in df_usg.columns and "TmFGA" in df_usg.columns:
                                df_usg["%FGA"] = (df_usg["FGA"] / df_usg["TmFGA"].replace(0, 1) * 100).fillna(0).round(1)
                            if "3PM" in df_usg.columns and "Tm3PM" in df_usg.columns:
                                df_usg["%3PM"] = (df_usg["3PM"] / df_usg["Tm3PM"].replace(0, 1) * 100).fillna(0).round(1)
                            if "3PA" in df_usg.columns and "Tm3PA" in df_usg.columns:
                                df_usg["%3PA"] = (df_usg["3PA"] / df_usg["Tm3PA"].replace(0, 1) * 100).fillna(0).round(1)
                            if "FTM" in df_usg.columns and "TmFTM" in df_usg.columns:
                                df_usg["%FTM"] = (df_usg["FTM"] / df_usg["TmFTM"].replace(0, 1) * 100).fillna(0).round(1)
                            if "FTA" in df_usg.columns and "TmFTA" in df_usg.columns:
                                df_usg["%FTA"] = (df_usg["FTA"] / df_usg["TmFTA"].replace(0, 1) * 100).fillna(0).round(1)
                            if "OREB" in df_usg.columns and "TmOREB" in df_usg.columns:
                                df_usg["%OREB"] = (df_usg["OREB"] / df_usg["TmOREB"].replace(0, 1) * 100).fillna(0).round(1)
                            if "DREB" in df_usg.columns and "TmDREB" in df_usg.columns:
                                df_usg["%DREB"] = (df_usg["DREB"] / df_usg["TmDREB"].replace(0, 1) * 100).fillna(0).round(1)
                            if "REB" in df_usg.columns and "TmREB" in df_usg.columns:
                                df_usg["%REB"] = (df_usg["REB"] / df_usg["TmREB"].replace(0, 1) * 100).fillna(0).round(1)
                            if "AST" in df_usg.columns and "TmAST" in df_usg.columns:
                                df_usg["%AST"] = (df_usg["AST"] / df_usg["TmAST"].replace(0, 1) * 100).fillna(0).round(1)
                            if "TOV" in df_usg.columns and "TmTOV" in df_usg.columns:
                                df_usg["%TOV"] = (df_usg["TOV"] / df_usg["TmTOV"].replace(0, 1) * 100).fillna(0).round(1)
                            if "STL" in df_usg.columns and "TmSTL" in df_usg.columns:
                                df_usg["%STL"] = (df_usg["STL"] / df_usg["TmSTL"].replace(0, 1) * 100).fillna(0).round(1)
                            if "BLK" in df_usg.columns and "TmBLK" in df_usg.columns:
                                df_usg["%BLK"] = (df_usg["BLK"] / df_usg["TmBLK"].replace(0, 1) * 100).fillna(0).round(1)
                            if "PF" in df_usg.columns and "TmPF" in df_usg.columns:
                                df_usg["%PF"] = (df_usg["PF"] / df_usg["TmPF"].replace(0, 1) * 100).fillna(0).round(1)
                            if "FD" in df_usg.columns and "TmFD" in df_usg.columns:
                                df_usg["%PFD"] = (df_usg["FD"] / df_usg["TmFD"].replace(0, 1) * 100).fillna(0).round(1)
                            if "PTS" in df_usg.columns and "TmPTS" in df_usg.columns:
                                df_usg["%PTS"] = (df_usg["PTS"] / df_usg["TmPTS"].replace(0, 1) * 100).fillna(0).round(1)
                            
                            # Select columns for display
                            usg_cols = ["Player", "Team", "Opponent", "Date", "USG%", "%FGM", "%FGA", "%3PM", "%3PA", 
                                       "%FTM", "%FTA", "%OREB", "%DREB", "%REB", "%AST", "%TOV", "%STL", "%BLK", "%PF", "%PFD", "%PTS"]
                            available_cols = [c for c in usg_cols if c in df_usg.columns]
                            
                            # Sort by USG%
                            if "USG%" in df_usg.columns:
                                df_usg_display = df_usg.sort_values(by="USG%", ascending=False).reset_index(drop=True)
                            else:
                                df_usg_display = df_usg.reset_index(drop=True)
                            
                            # Add Rank
                            df_usg_display.insert(0, "Rank", range(1, len(df_usg_display) + 1))
                            display_cols = ["Rank"] + available_cols
                            
                            st.dataframe(df_usg_display[display_cols], use_container_width=True, hide_index=True, height=600)
                    except Exception as e:
                        st.error(f"Error calculating usage percentages: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                else:
                    missing = []
                    if "Team" not in df_usg.columns:
                        missing.append("Team")
                    if "MatchID" not in df_usg.columns:
                        missing.append("MatchID")
                    st.info(f"Required columns missing: {missing if missing else 'None'}. Available columns: {list(df_usg.columns[:15])}")

            # TAB 5: SCORING (Table)
            with tab_scoring:
                # Calculate scoring distribution
                df_scoring = df_view.copy()
                
                if "PTS" in df_scoring.columns and "FGA" in df_scoring.columns:
                    # Calculate 2PT stats
                    df_scoring["2PM"] = df_scoring.get("2PM", df_scoring["FGM"] - df_scoring["3PM"])
                    df_scoring["2PA"] = df_scoring.get("2PA", df_scoring["FGA"] - df_scoring["3PA"])
                    
                    # Points from each source
                    df_scoring["PTS_2PT"] = df_scoring["2PM"] * 2
                    df_scoring["PTS_3PT"] = df_scoring["3PM"] * 3
                    df_scoring["PTS_FT"] = df_scoring["FTM"]
                    
                    # Percentage of FGA
                    df_scoring["%FGA_2PT"] = (df_scoring["2PA"] / df_scoring["FGA"] * 100).fillna(0).round(1)
                    df_scoring["%FGA_3PT"] = (df_scoring["3PA"] / df_scoring["FGA"] * 100).fillna(0).round(1)
                    
                    # Percentage of PTS
                    df_scoring["%PTS_2PT"] = (df_scoring["PTS_2PT"] / df_scoring["PTS"] * 100).fillna(0).round(1)
                    df_scoring["%PTS_3PT"] = (df_scoring["PTS_3PT"] / df_scoring["PTS"] * 100).fillna(0).round(1)
                    df_scoring["%PTS_FT"] = (df_scoring["PTS_FT"] / df_scoring["PTS"] * 100).fillna(0).round(1)
                    
                    # Assisted vs Unassisted (if available)
                    if "2FGM_AST" in df_scoring.columns:
                        df_scoring["2FGM_%AST"] = (df_scoring["2FGM_AST"] / df_scoring["2PM"] * 100).fillna(0).round(1)
                        df_scoring["2FGM_%UAST"] = (100 - df_scoring["2FGM_%AST"]).round(1)
                    
                    if "3FGM_AST" in df_scoring.columns:
                        df_scoring["3FGM_%AST"] = (df_scoring["3FGM_AST"] / df_scoring["3PM"] * 100).fillna(0).round(1)
                        df_scoring["3FGM_%UAST"] = (100 - df_scoring["3FGM_%AST"]).round(1)
                    
                    # Select columns
                    scoring_cols = ["Player", "Team", "Opponent", "Date", "%FGA_2PT", "%FGA_3PT", 
                                   "%PTS_2PT", "%PTS_3PT", "%PTS_FT", "PTS_2PT", "PTS_3PT", "PTS_FT"]
                    available_cols = [c for c in scoring_cols if c in df_scoring.columns]
                    
                    # Sort by PTS
                    df_scoring_display = df_scoring.sort_values(by="PTS", ascending=False).head(100).reset_index(drop=True)
                    
                    # Add Rank
                    df_scoring_display.insert(0, "Rank", range(1, len(df_scoring_display) + 1))
                    display_cols = ["Rank"] + available_cols
                    
                    st.dataframe(df_scoring_display[display_cols], use_container_width=True, hide_index=True, height=600)
                else:
                    st.info("Scoring data not available.")


# --- TOURNAMENT STATS ---
elif st.session_state.active_tab == "TOURNAMENT STATS":
    # --- UI CONTROLS (Moved up) ---
    c_sel, c_mode = st.columns([1.5, 2])
    
    with c_sel:
        entity_type = st.radio("Entity", ["Players", "Teams"], horizontal=True)
        period_sel = st.radio("Time Segment", ["Full Game", "Q1", "Q2", "Q3", "Q4", "1st Half", "2nd Half"], horizontal=True, index=0)
        
    with c_mode:
        opts = ["Totals", "Per Game"]
        if entity_type == "Players":
            opts.append("Per 36 Min")
        stat_mode = st.radio("Stats Mode", opts, horizontal=True)

    # --- AGGREGATION ---
    # --- AGGREGATION ---
    df_p_all, _ = MetricsEngine.get_tournament_stats(raw_data, period=period_sel, entity_type="Players")
    _, df_t_all = MetricsEngine.get_tournament_stats(raw_data, period=period_sel, entity_type="Teams")
    
    if df_p_all.empty:
        st.warning("No matched processed yet.")
    else:
        # --- MODE LOGIC ---
            
        # --- PREPARATION ---
        if entity_type == "Players":
            df_view = df_p_all.copy()
        else:
            df_view = df_t_all.copy()
            # df_view['Player'] = df_view['Team'] # REMOVED: analytics engine improved
            
        # --- MODE LOGIC ---
        # Identify columns to scale (All numeric except Metadata and RATE STATS)
        exclude_cols = ["No", "GP", "MatchID", "Team"]
        
        # Rate stats that should NOT be divided (they're already rates/percentages)
        rate_stats = ["USG%", "AST%", "FG%", "2P%", "3P%", "FT%", "eFG%", "TS%", 
                     "OFFRTG", "DEFRTG", "NETRTG", "PIE", "OREB%", "DREB%", "REB%",
                     "TO RATIO", "AST RATIO", "AST/TO"]
        
        exclude_cols.extend(rate_stats)
        numeric_cols = [c for c in df_view.select_dtypes(include=np.number).columns if c not in exclude_cols]
        
        df_display = df_view.copy()
        
        if stat_mode == "Per Game":
            for c in numeric_cols:
                # Ensure we don't divide if column missing (select_dtypes handles this but good to specific)
                df_display[c] = (df_display[c] / df_display['GP']).round(1)
                    
        elif stat_mode == "Per 36 Min":
            # Avoiding divide by zero
            valid_mins = df_display['MIN_CALC'] > 0
            df_display = df_display[valid_mins].copy()
            factor = df_display['MIN_CALC'] / 36.0
            
            for c in numeric_cols:
                if c != "MIN_CALC": # Don't divide MIN_CALC yet
                    df_display[c] = (df_display[c] / factor).round(1)
            df_display['MIN_CALC'] = 36.0 # Set explicit
            
        # Preserve USG% from MetricsEngine (it's already correctly calculated)
        # Recalculating after per-game division breaks the formula because _TmMin becomes per-game
        usg_preserved = df_display['USG%'].copy() if 'USG%' in df_display.columns else None
            
        # Recalculate Derived (Correct % and Ratings)
        # Recalculate Derived (Correct % and Ratings)
        if entity_type == "Players":
            df_display = ant.calculate_derived_stats(df_display)
        else:
            df_display = ant.calculate_derived_team_stats(df_display)
        
        # Restore preserved USG% (don't use the recalculated one)
        if usg_preserved is not None:
            df_display['USG%'] = usg_preserved
        
        # Default Sort: Points or PPG
        if not df_display.empty:
            sort_col = "PTS" if "PTS" in df_display.columns else df_display.columns[0]
            df_display = df_display.sort_values(by=sort_col, ascending=False)
        
        # --- DISPLAY ---
        ts_leaders, ts1, ts2, ts_usg, ts_scoring = st.tabs(["Leaders", "Standard Stats", "Advanced Stats", "USG", "SCORING"])
        
        # Prepare display data
        is_pg = (stat_mode in ["Per Game", "Per 36 Min"])
        tab_prec = 1 if is_pg else 0
        
        with ts_leaders:
            if entity_type == "Players" and not df_display.empty:
                st.markdown("<h4 style='font-family: \"Space Grotesk\", sans-serif; font-size: 1.1rem; margin-bottom: 20px; color: var(--text-secondary);'>TOURNAMENT PERFORMANCE LEADERS</h4>", unsafe_allow_html=True)
                
                # Row 1: Primary Stats
                r1_c1, r1_c2, r1_c3 = st.columns(3)
                with r1_c1:
                    ec.create_leader_board(df_display, "PTS", "Scoring Leaders", top_n=5)
                with r1_c2:
                    if "REB" in df_display.columns:
                        ec.create_leader_board(df_display, "REB", "Rebound Leaders", top_n=5)
                with r1_c3:
                    if "AST" in df_display.columns:
                        ec.create_leader_board(df_display, "AST", "Assist Leaders", top_n=5)
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                
                # Row 2: Secondary/Impact Stats
                r2_c1, r2_c2, r2_c3 = st.columns(3)
                with r2_c1:
                    if "STL" in df_display.columns:
                        ec.create_leader_board(df_display, "STL", "Steal Leaders", top_n=5)
                with r2_c2:
                    if "BLK" in df_display.columns:
                        ec.create_leader_board(df_display, "BLK", "Block Leaders", top_n=5)
                with r2_c3:
                    if "GmScr" in df_display.columns:
                        ec.create_leader_board(df_display, "GmScr", "Impact (GmScr)", top_n=5)
            else:
                st.info("Leader boards available for Players view only")
        
        with ts1:
            # Use same detailed columns as Top Performance
            std_cols = ["Player", "Team", "Opponent", "Date", "MIN_CALC", "PTS", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", 
                       "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "DD2", "TD3", "+/-"]
            
            # Filter to available columns
            available_cols = [c for c in std_cols if c in df_display.columns]
            
            # Sort by PTS by default
            if "PTS" in df_display.columns:
                df_std = df_display[available_cols].sort_values(by="PTS", ascending=False).head(100).reset_index(drop=True).copy()
            else:
                df_std = df_display[available_cols].head(100).reset_index(drop=True).copy()
            
            # Rename MIN_CALC to Min for display BEFORE adding Rank
            if "MIN_CALC" in df_std.columns:
                df_std = df_std.rename(columns={"MIN_CALC": "Min"})
            
            # Add Rank column
            df_std.insert(0, "Rank", range(1, len(df_std) + 1))
            
            # Round all numeric columns appropriately
            # Percentages: 1 decimal
            pct_cols = ["FG%", "3P%", "FT%"]
            for col in pct_cols:
                if col in df_std.columns:
                    df_std[col] = df_std[col].round(1)
            
            # Counting stats: integers for totals, 1 decimal for per-game
            if stat_mode in ["Per Game", "Per 36 Min"]:
                count_cols = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "+/-", "Min"]
                for col in count_cols:
                    if col in df_std.columns:
                        df_std[col] = df_std[col].round(1)
            else:
                count_cols = ["PTS", "FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "+/-"]
                for col in count_cols:
                    if col in df_std.columns:
                        df_std[col] = df_std[col].round(0).astype(int)
            
            # Apply styling to highlight max values
            def highlight_max(s):
                """Highlight the maximum in a Series."""
                if s.name in ["PTS", "REB", "AST", "STL", "BLK", "FGM", "3PM", "FTM"]:
                    is_max = s == s.max()
                    return ['background-color: rgba(255, 133, 51, 0.3); font-weight: bold' if v else '' for v in is_max]
                return ['' for _ in s]
            
            # Create format dict for percentage columns
            format_dict = {}
            for col in pct_cols:
                if col in df_std.columns:
                    format_dict[col] = "{:.1f}"
            
            # Add format for counting stats based on mode
            if stat_mode in ["Per Game", "Per 36 Min"]:
                # Per-game: 1 decimal for all counting stats
                for col in count_cols:
                    if col in df_std.columns:
                        format_dict[col] = "{:.1f}"
            else:
                # Totals: integers for counting stats
                for col in count_cols:
                    if col in df_std.columns and col != "+/-":  # +/- can be negative, keep as int
                        format_dict[col] = "{:.0f}"
            
            styled_df = df_std.style.apply(highlight_max).format(format_dict, na_rep="-")
            
            # Display dataframe without selection
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=600
            )
            
        with ts2:
            # Use same detailed columns as Top Performance
            adv_cols = ["Player", "Team", "Opponent", "Date", "MIN_CALC", "OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", 
                       "AST RATIO", "OREB%", "DREB%", "REB%", "TO RATIO", "eFG%", "TS%", "USG%", "PIE", "PPoss"]
            
            # Filter to available columns
            available_cols = [c for c in adv_cols if c in df_display.columns]
            
            # Sort by PIE by default
            if "PIE" in df_display.columns:
                df_adv = df_display[available_cols].sort_values(by="PIE", ascending=False).head(100).reset_index(drop=True).copy()
            else:
                df_adv = df_display[available_cols].head(100).reset_index(drop=True).copy()
            
            # Rename MIN_CALC to MIN for display BEFORE adding Rank
            if "MIN_CALC" in df_adv.columns:
                df_adv = df_adv.rename(columns={"MIN_CALC": "MIN"})
            
            # Add Rank column
            df_adv.insert(0, "Rank", range(1, len(df_adv) + 1))
            
            # Round all advanced stats to 1 decimal place
            numeric_cols = ["OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", "AST RATIO", "OREB%", "DREB%", "REB%", 
                           "TO RATIO", "eFG%", "TS%", "USG%", "PIE", "PPoss", "MIN"]
            for col in numeric_cols:
                if col in df_adv.columns:
                    df_adv[col] = df_adv[col].round(1)
            
            # Apply styling to highlight max values
            def highlight_max(s):
                """Highlight the maximum in a Series."""
                if s.name in ["PIE", "OFFRTG", "NETRTG", "TS%", "eFG%"]:
                    is_max = s == s.max()
                    return ['background-color: rgba(255, 133, 51, 0.3); font-weight: bold' if v else '' for v in is_max]
                return ['' for _ in s]
            
            # Create format dict for numeric columns
            format_dict = {}
            for col in numeric_cols:
                if col in df_adv.columns:
                    format_dict[col] = "{:.1f}"
            
            styled_df = df_adv.style.apply(highlight_max).format(format_dict, na_rep="-")
            
            # Display dataframe without selection
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=600
            )
        
        # TAB 4: USG (Table)
        with ts_usg:
            # USG% should always use totals, not per-game or per-36 stats
            # Use the original aggregated data before scaling
            df_usg_base = df_p_all.copy() if entity_type == "Players" else df_t_all.copy()
            
            # Calculate usage percentages
            df_usg = df_usg_base.copy()
            
            # For tournament stats, we need to aggregate team totals across all games
            if entity_type == "Players" and not df_usg_base.empty:
                try:
                    # Use Centralized Metrics Engine
                    df_usg, _ = MetricsEngine.get_tournament_stats(raw_data, period=period_sel, entity_type="Players")
                    
                    if not df_usg.empty:
                         # Filter to > 0 GP just in case
                         df_usg = df_usg[df_usg["GP"] > 0].copy()
                         
                         # Calculate percentages relative to TEAM TOTALS
                         # We need to make sure we have the team totals column for each player
                         # Fortunately, MetricsEngine.get_tournament_stats returns df with TmFGM, TmFGA, etc. if we ask it to?
                         # Actually, let's check what columns are in df_usg from debug_risha.py
                         # It showed TmFGM, TmFGA, etc. ARE present!
                         
                         # Define percent columns to calculate
                         pct_map = {
                             "FGM": "TmFGM", "FGA": "TmFGA", 
                             "3PM": "Tm3PM", "3PA": "Tm3PA",
                             "FTM": "TmFTM", "FTA": "TmFTA",
                             "OREB": "TmOREB", "DREB": "TmDREB", "REB": "TmREB",
                             "AST": "TmAST", "TOV": "TmTOV", "STL": "TmSTL", 
                             "BLK": "TmBLK", "PF": "TmPF", "FD": "TmFD", "PTS": "TmPTS"
                         }
                         
                         for stat, tm_stat in pct_map.items():
                             if stat in df_usg.columns and tm_stat in df_usg.columns:
                                 pct_col = f"%{stat}" if stat != "FD" else "%PFD"
                                 # Calculate percentage: Player Stat / Team Stat
                                 # Replace 0 denominator with 1 to avoid NaN/Inf
                                 df_usg[pct_col] = (df_usg[stat] / df_usg[tm_stat].replace(0, 1) * 100).fillna(0).round(1)
                                 
                         # Handle BLKA if available
                         if "BLKA" in df_usg.columns and "TmBLKA" in df_usg.columns:
                             df_usg["%BLKA"] = (df_usg["BLKA"] / df_usg["TmBLKA"].replace(0, 1) * 100).fillna(0).round(1)
                         elif "BLKA" in df_usg.columns:
                              # If TmBLKA missing, assume sum of checks
                              pass
                         
                         # Select display columns (including new ones)
                         usg_cols = ["Player", "Team", "GP", "USG%", "%FGM", "%FGA", "%3PM", "%3PA", 
                                    "%FTM", "%FTA", "%OREB", "%DREB", "%REB", "%AST", "%TOV", "%STL", 
                                    "%BLK", "%PF", "%PFD", "%PTS"]
                                    
                         display_cols = [c for c in usg_cols if c in df_usg.columns]
                         
                         # Sort by USG% descending
                         if "USG%" in df_usg.columns:
                             df_usg = df_usg.sort_values("USG%", ascending=False)
                         
                         # Add Rank
                         df_usg.insert(0, "Rank", range(1, len(df_usg) + 1))
                         display_cols_final = ["Rank"] + display_cols
                         
                         st.dataframe(df_usg[display_cols_final], use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Error calculating USG metrics: {e}")
            else:
                st.info("No player data available for USG metrics.")
        
        # TAB 5: SCORING (Table)
        with ts_scoring:
            # Scoring percentages should always use totals, not per-game or per-36 stats
            # Use the original aggregated data before scaling
            df_scoring_base = df_p_all.copy() if entity_type == "Players" else df_t_all.copy()
            
            if entity_type == "Players" and not df_scoring_base.empty:
                # Calculate scoring distribution
                df_scoring = df_scoring_base.copy()
                
                if "PTS" in df_scoring.columns and "FGA" in df_scoring.columns:
                    # Calculate 2PT stats
                    df_scoring["2PM"] = df_scoring.get("2PM", df_scoring["FGM"] - df_scoring["3PM"])
                    df_scoring["2PA"] = df_scoring.get("2PA", df_scoring["FGA"] - df_scoring["3PA"])
                    
                    # Points from each source
                    df_scoring["PTS_2PT"] = df_scoring["2PM"] * 2
                    df_scoring["PTS_3PT"] = df_scoring["3PM"] * 3
                    df_scoring["PTS_FT"] = df_scoring["FTM"]
                    
                    # Percentage of FGA
                    df_scoring["%FGA_2PT"] = (df_scoring["2PA"] / df_scoring["FGA"] * 100).fillna(0).round(1)
                    df_scoring["%FGA_3PT"] = (df_scoring["3PA"] / df_scoring["FGA"] * 100).fillna(0).round(1)
                    
                    # Percentage of PTS
                    df_scoring["%PTS_2PT"] = (df_scoring["PTS_2PT"] / df_scoring["PTS"] * 100).fillna(0).round(1)
                    df_scoring["%PTS_3PT"] = (df_scoring["PTS_3PT"] / df_scoring["PTS"] * 100).fillna(0).round(1)
                    df_scoring["%PTS_FT"] = (df_scoring["PTS_FT"] / df_scoring["PTS"] * 100).fillna(0).round(1)
                    
                    # Select columns
                    scoring_cols = ["Player", "Team", "%FGA_2PT", "%FGA_3PT", 
                                   "%PTS_2PT", "%PTS_3PT", "%PTS_FT", "PTS_2PT", "PTS_3PT", "PTS_FT"]
                    available_cols = [c for c in scoring_cols if c in df_scoring.columns]
                    
                    # Sort by PTS
                    df_scoring_display = df_scoring.sort_values(by="PTS", ascending=False).head(100).reset_index(drop=True)
                    
                    # Round all percentage columns to 1 decimal
                    pct_cols_scoring = [c for c in df_scoring_display.columns if c.startswith('%')]
                    for col in pct_cols_scoring:
                        if col in df_scoring_display.columns:
                            df_scoring_display[col] = df_scoring_display[col].round(1)
                    
                    # Round point totals to integers
                    pts_cols = ["PTS_2PT", "PTS_3PT", "PTS_FT"]
                    for col in pts_cols:
                        if col in df_scoring_display.columns:
                            df_scoring_display[col] = df_scoring_display[col].round(0).astype(int)
                    
                    # Add Rank
                    df_scoring_display.insert(0, "Rank", range(1, len(df_scoring_display) + 1))
                    display_cols = ["Rank"] + available_cols
                    
                    st.dataframe(df_scoring_display[display_cols], use_container_width=True, hide_index=True, height=600)
                else:
                    st.info("Scoring data not available.")
            else:
                st.info("Scoring stats available for Players view only")




# --- PLAYER PROFILE ---
elif st.session_state.active_tab == "PLAYER PROFILE":
    # Get aggregated player data
    df_p_all, _ = MetricsEngine.get_tournament_stats(raw_data, period="Full Game", entity_type="Players")
    
    if df_p_all.empty:
        st.warning("No player data available.")
        st.stop()
        
    # Ensure Advanced Metrics are calculated
    df_p_all = ant.calculate_derived_stats(df_p_all)
    
    # Filter out players with 0 games played
    df_p_all = df_p_all[df_p_all['GP'] > 0].copy()
    
    # Simple selectors - NO GENDER FILTER FOR NOW
    teams_list = sorted(df_p_all['Team'].unique()) if 'Team' in df_p_all.columns else []
    
    c_p1, c_p2 = st.columns([1, 1])
    
    with c_p1:
        sel_team_prof = st.selectbox("Filter by Team", ["All Teams"] + teams_list, key="prof_team")
    
    with c_p2:
        if sel_team_prof != "All Teams":
            p_opts = sorted(df_p_all[df_p_all['Team'] == sel_team_prof]['Player'].unique())
        else:
            p_opts = sorted(df_p_all['Player'].unique())
        
        if not p_opts:
            st.warning("No players available.")
            st.stop()
            
        sel_player_prof = st.selectbox("Select Player", p_opts, key="prof_player")
    
    # Get Player Stats
    p_stats = df_p_all[df_p_all['Player'] == sel_player_prof].iloc[0]
    player_team = p_stats['Team']
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    # 1. CORE HEADER CARD (Name, Team, GP, PPG, RPG, APG, FIC)
    if sel_player_prof:
        # Strip team suffix to get raw player name for data lookup
        player_name_raw = sel_player_prof
        if " (" in player_name_raw:
            player_name_raw = player_name_raw.split(" (")[0]
        
        # Get player data
        row_p = df_p_all[df_p_all['Player'] == sel_player_prof]
        
        if not row_p.empty:
            row_p = row_p.iloc[0]
            gp = row_p.get('GP', 0)
            
            # Player Header Card
            st.markdown(textwrap.dedent(f"""\
            <div class="glass-card" style='padding: 24px; margin-bottom: 24px; border-left: 4px solid var(--tappa-orange);'>
                <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;'>
                    <div style='flex: 1; min-width: 250px;'>
                        <h1 style='font-family: "Space Grotesk", sans-serif; font-weight: 700; font-size: 2.2rem; color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.02em;'>
                            {player_name_raw}
                        </h1>
                        <p style='font-family: "Space Grotesk", sans-serif; font-size: 1rem; color: var(--tappa-orange); margin: 0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>
                            {row_p.get('Team', 'Unknown')} <span style='color: var(--text-muted); margin: 0 8px;'>|</span> {int(round(float(gp)))} Games Played
                        </p>
                    </div>
                    <div style='display: flex; gap: 24px; flex-wrap: wrap;'>
                        <div style='text-align: center; min-width: 70px;'>
                            <div style='font-size: 2rem; font-weight: 800; color: var(--tappa-orange); font-family: "Outfit", sans-serif;'>
                                {row_p.get('PTS', 0) / gp if gp > 0 else 0:.1f}
                            </div>
                            <div style='font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; font-family: "Space Grotesk", sans-serif;'>PPG</div>
                        </div>
                        <div style='text-align: center; min-width: 70px;'>
                            <div style='font-size: 2rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>
                                {row_p.get('REB', 0) / gp if gp > 0 else 0:.1f}
                            </div>
                            <div style='font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; font-family: "Space Grotesk", sans-serif;'>RPG</div>
                        </div>
                        <div style='text-align: center; min-width: 70px;'>
                            <div style='font-size: 2rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>
                                {row_p.get('AST', 0) / gp if gp > 0 else 0:.1f}
                            </div>
                            <div style='font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; font-family: "Space Grotesk", sans-serif;'>APG</div>
                        </div>
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)

            # 2. METRICS GRID
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                # SHOOTING PROFILE CARD
                st.markdown(textwrap.dedent(f"""\
                <div class="glass-card" style='padding: 20px; height: 100%;'>
                    <h3 style='font-family: "Space Grotesk", sans-serif; font-size: 0.9rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;'>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="m12 8 4 4-4 4M8 12h8"></path></svg>
                        Shooting Profile
                    </h3>
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{float(row_p.get('FG%', 0)):.1f}%</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Field Goal %</div>
                            <div style='font-size: 0.65rem; color: var(--text-muted); opacity: 0.7; font-family: "Outfit", sans-serif;'>{int(round(float(row_p.get('FGM', 0))))}/{int(round(float(row_p.get('FGA', 0))))}</div>
                        </div>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{float(row_p.get('3P%', 0)):.1f}%</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>3-Point %</div>
                            <div style='font-size: 0.65rem; color: var(--text-muted); opacity: 0.7; font-family: "Outfit", sans-serif;'>{int(round(float(row_p.get('3PM', 0))))}/{int(round(float(row_p.get('3PA', 0))))}</div>
                        </div>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{float(row_p.get('FT%', 0)):.1f}%</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Free Throw %</div>
                            <div style='font-size: 0.65rem; color: var(--text-muted); opacity: 0.7; font-family: "Outfit", sans-serif;'>{int(round(float(row_p.get('FTM', 0))))}/{int(round(float(row_p.get('FTA', 0))))}</div>
                        </div>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--tappa-orange); font-family: "Outfit", sans-serif;'>{row_p.get('eFG%', 0):.1f}%</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Effective FG%</div>
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
            
            with col_right:
                # ADVANCED METRICS CARD
                st.markdown(textwrap.dedent(f"""\
                <div class="glass-card" style='padding: 20px; height: 100%;'>
                    <h3 style='font-family: "Space Grotesk", sans-serif; font-size: 0.9rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;'>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
                        Advanced Impact
                    </h3>
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{row_p.get('PIE', 0):.1f}</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Impact (PIE)</div>
                        </div>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{row_p.get('USG%', 0):.1f}%</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Usage Rate</div>
                        </div>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{row_p.get('GmScr', 0) / gp if gp > 0 else 0:.1f}</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Game Score/G</div>
                        </div>
                        <div>
                            <div style='font-size: 1.6rem; font-weight: 800; color: var(--text-primary); font-family: "Outfit", sans-serif;'>{row_p.get('FIC', 0) / gp if gp > 0 else 0:.1f}</div>
                            <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>Impact (FIC/G)</div>
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)

            # 3. SECONDARY STATS ROW (Counting/Context)
            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            
            with c1:
                st.markdown(textwrap.dedent(f"""\
                    <div class='glass-card' style='padding: 12px; text-align: center;'>
                        <div style='font-size: 1.1rem; font-weight: 700; font-family: "Outfit", sans-serif;'>{row_p.get('STL', 0) / gp if gp > 0 else 0:.1f}</div>
                        <div style='font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>STL/G</div>
                    </div>
                """), unsafe_allow_html=True)
            with c2:
                st.markdown(textwrap.dedent(f"""\
                    <div class='glass-card' style='padding: 12px; text-align: center;'>
                        <div style='font-size: 1.1rem; font-weight: 700; font-family: "Outfit", sans-serif;'>{row_p.get('BLK', 0) / gp if gp > 0 else 0:.1f}</div>
                        <div style='font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>BLK/G</div>
                    </div>
                """), unsafe_allow_html=True)
            with c3:
                st.markdown(textwrap.dedent(f"""\
                    <div class='glass-card' style='padding: 12px; text-align: center;'>
                        <div style='font-size: 1.1rem; font-weight: 700; font-family: "Outfit", sans-serif;'>{row_p.get('TOV', 0) / gp if gp > 0 else 0:.1f}</div>
                        <div style='font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>TOV/G</div>
                    </div>
                """), unsafe_allow_html=True)
            with c4:
                ast_to = (row_p.get('AST', 0) / row_p.get('TOV', 1)) if row_p.get('TOV', 0) > 0 else row_p.get('AST', 0)
                st.markdown(textwrap.dedent(f"""\
                    <div class='glass-card' style='padding: 12px; text-align: center;'>
                        <div style='font-size: 1.1rem; font-weight: 700; font-family: "Outfit", sans-serif;'>{ast_to:.1f}</div>
                        <div style='font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>AST/TO</div>
                    </div>
                """), unsafe_allow_html=True)
            with c5:
                st.markdown(textwrap.dedent(f"""\
                    <div class='glass-card' style='padding: 12px; text-align: center;'>
                        <div style='font-size: 1.1rem; font-weight: 700; font-family: "Outfit", sans-serif;'>{row_p.get('PF', 0) / gp if gp > 0 else 0:.1f}</div>
                        <div style='font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; font-family: "Space Grotesk", sans-serif;'>PF/G</div>
                    </div>
                """), unsafe_allow_html=True)

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
    
    game_log = []
    
    # Use raw_data_all to show all games regardless of category filter
    for match in raw_data_all:
        # Check PeriodStats for player participation (more reliable)
        player_found = False
        player_match_stats = None
        
        # First try PlayerStats (aggregated match-level) - use raw name
        if 'PlayerStats' in match and player_name_raw in match['PlayerStats']:
            player_match_stats = match['PlayerStats'][player_name_raw]
            player_found = True
        else:
            # Try to find in PeriodStats (quarter-by-quarter)
            period_stats = match.get('PeriodStats', {})
            combined_stats = {}
            
            for quarter, players in period_stats.items():
                if player_name_raw in players:
                    player_found = True
                    # Aggregate stats across quarters
                    for stat_key, stat_val in players[player_name_raw].items():
                        if stat_key in ['Team', 'No', 'Player']:
                            combined_stats[stat_key] = stat_val
                        else:
                            combined_stats[stat_key] = combined_stats.get(stat_key, 0) + stat_val
            
            if player_found:
                # Calculate derived stats for this game
                player_match_stats = combined_stats
                # Quick FIC and GmScr calculation
                player_match_stats['FIC'] = (
                    player_match_stats.get('PTS', 0) + 
                    player_match_stats.get('OREB', 0) + 
                    0.75 * player_match_stats.get('DREB', 0) + 
                    player_match_stats.get('AST', 0) + 
                    player_match_stats.get('STL', 0) + 
                    player_match_stats.get('BLK', 0) - 
                    0.75 * player_match_stats.get('FGA', 0) - 
                    0.375 * player_match_stats.get('FTA', 0) - 
                    player_match_stats.get('TOV', 0) - 
                    0.5 * player_match_stats.get('PF', 0)
                )
                player_match_stats['GmScr'] = (
                    player_match_stats.get('PTS', 0) + 
                    0.4 * player_match_stats.get('FGM', 0) - 
                    0.7 * player_match_stats.get('FGA', 0) - 
                    0.4 * (player_match_stats.get('FTA', 0) - player_match_stats.get('FTM', 0)) + 
                    0.7 * player_match_stats.get('OREB', 0) + 
                    0.3 * player_match_stats.get('DREB', 0) + 
                    player_match_stats.get('STL', 0) + 
                    0.7 * player_match_stats.get('AST', 0) + 
                    0.7 * player_match_stats.get('BLK', 0) - 
                    0.4 * player_match_stats.get('PF', 0) - 
                    player_match_stats.get('TOV', 0)
                )
        
        if player_found and player_match_stats:
            # Determine opponent
            t1, t2 = match['Teams']['t1'], match['Teams']['t2']
            opponent = t2 if t1 == player_team else t1
            
            # Determine result (W/L)
            team_stats = match.get('TeamStats', {})
            if 't1' in team_stats and 't2' in team_stats:
                s1 = team_stats['t1'].get('PTS', 0)
                s2 = team_stats['t2'].get('PTS', 0)
                
                if t1 == player_team:
                    result = "W" if s1 > s2 else "L"
                    score = f"{s1}-{s2}"
                else:
                    result = "W" if s2 > s1 else "L"
                    score = f"{s2}-{s1}"
            else:
                result = "-"
                score = "-"
            
            # Get date
            date = match.get('Metadata', {}).get('MatchDate', 'Unknown')
            
            # Extract key stats
            game_log.append({
                'Date': date,
                'Opponent': opponent,
                'Result': result,
                'MIN': player_match_stats.get('MIN_DEC', 0),
                'Score': score,
                'PTS': player_match_stats.get('PTS', 0),
                'REB': player_match_stats.get('REB', 0),
                'AST': player_match_stats.get('AST', 0),
                'FG': f"{int(player_match_stats.get('FGM', 0))}/{int(player_match_stats.get('FGA', 0))}",
                '3P': f"{int(player_match_stats.get('3PM', 0))}/{int(player_match_stats.get('3PA', 0))}",
                'FT': f"{int(player_match_stats.get('FTM', 0))}/{int(player_match_stats.get('FTA', 0))}",
                'FIC': round(player_match_stats.get('FIC', 0), 1),
                'GmScr': round(player_match_stats.get('GmScr', 0), 1)
            })
    
    # 4. GAME LOG
    st.markdown("""
    <h3 style='font-family: "Montserrat", sans-serif; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 16px 0; border-bottom: 2px solid var(--tappa-orange); width: fit-content; padding-bottom: 4px;'>
        Game-by-Game Log
    </h3>
    """, unsafe_allow_html=True)
    
    if game_log:
        game_log_df = pd.DataFrame(game_log)
        # Apply specialized formatting for game log (per_game=False for integers)
        game_log_df = ant.apply_standard_stat_formatting(game_log_df, per_game=False)
        # Style the dataframe for better readability
        st.markdown(ec.render_html_table(game_log_df), unsafe_allow_html=True)
    else:
        st.info("No game log available for this player.")



# --- PLAYER COMPARISON ---
elif st.session_state.active_tab == "COMPARISON":
    st.header("Player Comparison")
    
    # Get aggregated player data
    df_p_all_comp, _ = MetricsEngine.get_tournament_stats(raw_data, period="Full Game", entity_type="Players")
    
    if df_p_all_comp.empty:
        st.warning("No player data available.")
        st.stop()
        
    # Ensure Advanced Metrics
    df_p_all_comp = ant.calculate_derived_stats(df_p_all_comp)
    
    # Filter out players with 0 games played
    df_p_all_comp = df_p_all_comp[df_p_all_comp['GP'] > 0].copy()
    
    # --- STAT CATEGORY SELECTOR ---
    st.markdown("### Select Stats to Compare")
    
    # Define categorized stat groups
    stat_categories = {
        "Scoring": ["PTS", "FGM", "FGA", "FG%", "2PM", "2PA", "2P%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", "eFG%", "TS%"],
        "Rebounding": ["REB", "OREB", "DREB"],
        "Playmaking": ["AST", "AST%", "AST/TO", "TOV"],
        "Defense": ["STL", "BLK", "PF", "DEFRTG"],
        "Advanced": ["FIC", "GmScr", "PIE", "USG%", "Eff", "OFFRTG", "NETRTG", "+/-"]
    }
    
    # Flatten all available stats
    all_available_stats = []
    for category_stats in stat_categories.values():
        all_available_stats.extend(category_stats)
    
    # Filter to only stats that exist in the dataframe
    available_stats = [stat for stat in all_available_stats if stat in df_p_all_comp.columns]
    
    # --- PRESET DEFINITIONS ---
    presets = {
        "Balanced (Default)": ["GmScr", "FIC", "PIE", "eFG%", "TS%", "USG%"],
        "Scoring": ["PTS", "FG%", "3P%", "eFG%", "TS%", "USG%"],
        "Playmaking": ["AST", "AST%", "AST/TO", "TOV", "USG%"],
        "Defense": ["STL", "BLK", "DREB", "DEFRTG", "PF"],
        "Shooting": ["FG%", "3P%", "FT%", "eFG%", "TS%", "2P%"],
        "Advanced": ["FIC", "GmScr", "PIE", "USG%", "Eff", "NETRTG", "+/-"]
    }
    
    # helper to filter presets to available stats
    for k in presets:
        presets[k] = [s for s in presets[k] if s in available_stats]
        
    # --- SESSION STATE MANAGEMENT ---
    # Initialize keys if not present
    if "comp_stat_preset" not in st.session_state:
        st.session_state.comp_stat_preset = "Balanced (Default)"
    if "comp_selected_stats" not in st.session_state:
        st.session_state.comp_selected_stats = presets["Balanced (Default)"]
        
    # Callback for Preset Change
    def on_preset_change():
        sel = st.session_state.comp_stat_preset
        if sel != "Custom":
            st.session_state.comp_selected_stats = presets[sel]
            
    # Callback for Multiselect Change
    def on_stats_change():
        # Check if current selection matches any preset
        current = set(st.session_state.comp_selected_stats)
        found = False
        for name, stats in presets.items():
            if set(stats) == current:
                st.session_state.comp_stat_preset = name
                found = True
                break
        if not found:
            st.session_state.comp_stat_preset = "Custom"

    # Layout: 2 Columns (Preset | Stats)
    c_preset, c_stats = st.columns([1, 2])
    
    with c_preset:
        st.selectbox(
            "Stat Preset",
            ["Custom"] + list(presets.keys()),
            key="comp_stat_preset",
            on_change=on_preset_change
        )
        
    with c_stats:
        selected_stats = st.multiselect(
            "Customize Stats",
            available_stats,
            key="comp_selected_stats",
            on_change=on_stats_change,
            help="Select specific metrics to compare"
        )
    
    # Validation (Fallbacks)
    if not selected_stats:
        selected_stats = presets["Balanced (Default)"]
        st.session_state.comp_selected_stats = selected_stats
    
    if len(selected_stats) < 3:
        st.warning("⚠️ Please select at least 3 stats for meaningful comparison.")
    elif len(selected_stats) > 8:
        st.warning("⚠️ Maximum 8 stats allowed for optimal visualization.")
        selected_stats = selected_stats[:8]
    
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    # Multi-Select Players
    all_p_names = sorted(df_p_all_comp['Player'].unique())
    comp_players = st.multiselect("Select Players to Compare (Max 4)", all_p_names, max_selections=4)
    
    if comp_players:
        comp_df = df_p_all_comp[df_p_all_comp['Player'].isin(comp_players)].copy()
        
        # Radar Chart
        import plotly.graph_objects as go
        
        # --- DYNAMIC METRIC CONFIGURATION ---
        # Determine appropriate max values for selected stats
        metric_configs = {}
        
        # Stats that are percentages (max = 100)
        percentage_stats = ["FG%", "2P%", "3P%", "FT%", "eFG%", "TS%", "AST%", "USG%"]
        
        # Stats that should use per-game values
        per_game_stats = ["PTS", "REB", "OREB", "DREB", "AST", "STL", "BLK", "TOV", "PF", 
                         "FGM", "FGA", "2PM", "2PA", "3PM", "3PA", "FTM", "FTA",
                         "FIC", "GmScr", "+/-"]
        
        for stat in selected_stats:
            if stat in percentage_stats:
                # Percentages: max = 100
                metric_configs[stat] = {"max": 100, "label": stat}
            elif stat in ["OFFRTG", "DEFRTG", "NETRTG"]:
                # Ratings: use dynamic max (1.5x highest value)
                max_val = 0
                for _, row in comp_df.iterrows():
                    val = row.get(stat, 0)
                    max_val = max(max_val, abs(val))
                metric_configs[stat] = {"max": max(max_val * 1.5, 10), "label": stat}
            elif stat in per_game_stats:
                # Per-game stats: calculate from totals, use dynamic max
                max_val = 0
                for _, row in comp_df.iterrows():
                    gp = row.get('GP', 1)
                    val = row.get(stat, 0) / gp if gp > 0 else 0
                    max_val = max(max_val, val)
                metric_configs[stat] = {"max": max(max_val * 1.5, 1), "label": stat}
            else:
                # Other advanced stats: use dynamic max
                max_val = 0
                for _, row in comp_df.iterrows():
                    val = row.get(stat, 0)
                    max_val = max(max_val, abs(val))
                metric_configs[stat] = {"max": max(max_val * 1.5, 10), "label": stat}
        
        fig = go.Figure()
        
        # Diverse color palette - distinct colors for each player while maintaining professional look
        colors = [
            '#d16b07',  # Tappa Orange (Player 1)
            '#3b82f6',  # Blue (Player 2)
            '#10b981',  # Green (Player 3)
            '#8b5cf6'   # Purple (Player 4)
        ]
        
        # Collect all values to find actual max for dynamic scaling
        all_normalized_values = []
        
        for idx, (i, row) in enumerate(comp_df.iterrows()):
            gp = row['GP']
            if gp == 0:
                continue
            
            # Calculate raw values dynamically based on selected stats
            raw_values = {}
            for stat in selected_stats:
                if stat in per_game_stats:
                    # Convert totals to per-game
                    raw_values[stat] = row.get(stat, 0) / gp if gp > 0 else 0
                else:
                    # Use raw value (percentages, ratings, etc.)
                    raw_values[stat] = row.get(stat, 0)
            
            # Normalize to 0-100 scale based on expected max
            normalized_vals = []
            for metric, config in metric_configs.items():
                normalized = (raw_values[metric] / config["max"]) * 100
                normalized_vals.append(normalized)
            
            all_normalized_values.extend(normalized_vals)
            
            # Close the polygon by repeating first value
            closed_vals = normalized_vals + [normalized_vals[0]]
            closed_theta = [config["label"] for config in metric_configs.values()] + [list(metric_configs.values())[0]["label"]]
            
            # Get color for this player
            color = colors[idx % len(colors)]
            
            fig.add_trace(go.Scatterpolar(
                r=closed_vals,
                theta=closed_theta,
                fill='toself',
                name=row['Player'],
                line=dict(color=color, width=2),
                fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.25)',
                hovertemplate='<b>%{theta}</b><br>%{r:.1f}<extra></extra>'
            ))
        
        # Calculate dynamic max with padding (so it doesn't fill to 100%)
        if all_normalized_values:
            data_max = max(all_normalized_values)
            chart_max = data_max * 1.25  # Add 25% padding
        else:
            chart_max = 100
        
        # Update layout with Tappa styling
        fig.update_layout(
            polar=dict(
                bgcolor='rgba(255, 255, 255, 0.03)',
                radialaxis=dict(
                    visible=True,
                    showticklabels=True,
                    tickfont=dict(size=10, color='rgba(255, 255, 255, 0.6)', family='Outfit, sans-serif'),
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    range=[0, chart_max],
                ),
                angularaxis=dict(
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    linecolor='rgba(255, 133, 51, 0.3)',
                    tickfont=dict(size=11, color='#ffffff', family='Space Grotesk, sans-serif', weight=600)
                )
            ),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.15,
                xanchor='center',
                x=0.5,
                font=dict(color='#ffffff', size=11, family='Space Grotesk, sans-serif'),
                bgcolor='rgba(0, 0, 0, 0.3)',
                bordercolor='rgba(255, 133, 51, 0.3)',
                borderwidth=1
            ),
            height=550,
            margin=dict(t=40, b=100, l=80, r=80),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', size=12, family='Space Grotesk, sans-serif')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Comparison Table - Custom Format
        st.markdown("### Head-to-Head Stats")
        
        # Build stat definitions dynamically from selected stats
        # Always include GP as first column
        stat_definitions = [("GP", "GP")]
        
        # Add selected stats with appropriate labels
        for stat in selected_stats:
            if stat in per_game_stats and stat not in ["FIC", "GmScr", "+/-"]:
                # Counting stats shown as per-game (except FIC, GmScr which are already labeled)
                if stat in ["PTS", "REB", "AST", "STL", "BLK", "TOV", "PF"]:
                    label = f"{stat[0]}PG" if len(stat) == 3 else f"{stat}/G"
                else:
                    label = f"{stat}/G"
            elif stat in ["FIC", "GmScr"]:
                # These are shown as per-game with /G suffix
                label = f"{stat}/G"
            else:
                # Percentages, ratings, and other advanced stats use their name as-is
                label = stat
            
            stat_definitions.append((stat, label))
        
        # Custom CSS for the Head-to-Head Table (Localized but using globals)
        st.markdown(f"""
            <style>
                .comparison-container {{
                    background: var(--bg-glass);
                    backdrop-filter: blur(12px);
                    border: 1px solid var(--border-glass);
                    border-radius: 12px;
                    overflow-x: auto;
                    margin-top: 24px;
                }}
                .h2h-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-family: 'Space Grotesk', sans-serif;
                    min-width: 500px;
                }}
                .h2h-table th, .h2h-table td {{
                    padding: 14px 20px;
                    text-align: center;
                    border-bottom: 1px solid var(--border-glass);
                }}
                .h2h-table .stat-label {{
                    text-align: left;
                    font-weight: 700;
                    color: var(--text-secondary);
                    background: rgba(0,0,0,0.2);
                    width: 180px;
                    font-size: 0.9rem;
                    text-transform: uppercase;
                }}
                .h2h-table .player-header {{
                    font-size: 1.1rem;
                    font-weight: 800;
                    color: white;
                    letter-spacing: -0.01em;
                }}
                @media (max-width: 768px) {{
                    .h2h-table th, .h2h-table td {{ padding: 10px 12px; font-size: 0.85rem; }}
                    .h2h-table .player-header {{ font-size: 0.95rem; }}
                    .h2h-table .stat-label {{ width: 140px; font-size: 0.75rem; }}
                }}
            </style>
        """, unsafe_allow_html=True)
        
        # Build custom HTML table
        table_html = """
        <div class="comparison-container">
        <table class="h2h-table">
            <thead>
                <tr>
                    <th class="stat-label">Stat</th>
        """
        
        # Add player headers with their assigned colors
        for idx, (i, row) in enumerate(comp_df.iterrows()):
            color = colors[idx % len(colors)]
            p_name = str(row["Player"])
            if " (" in p_name:
                p_name = p_name.split(" (")[0]
            table_html += f'<th class="player-header" style="background: {color}; font-family: \'Space Grotesk\', sans-serif;">{p_name}</th>'
        
        table_html += """
                </tr>
            </thead>
            <tbody>
        """
        
        # Add rows for each stat
        for stat_key, stat_label in stat_definitions:
            if stat_key not in comp_df.columns:
                continue
                
            table_html += f'<tr><td class="stat-label">{stat_label}</td>'
            
            # Get values for all players
            values = []
            for idx, (i, row) in enumerate(comp_df.iterrows()):
                if stat_key == "GP":
                    val = int(row.get(stat_key, 0))
                    values.append((val, False))
                elif stat_key in per_game_stats:
                    # Per-game stats (convert totals)
                    val = row.get(stat_key, 0) / row.get('GP', 1)
                    values.append((val, True))
                else:
                    # Percentage stats and other advanced metrics
                    val = row.get(stat_key, 0)
                    values.append((val, True))
            
            # Find min/max for color coding (only for numeric values)
            numeric_values = [v[0] for v in values if v[1] and isinstance(v[0], (int, float))]
            if numeric_values:
                min_val = min(numeric_values)
                max_val = max(numeric_values)
                val_range = max_val - min_val if max_val != min_val else 1
            else:
                min_val = max_val = val_range = 0
            
            # Add cells for each player
            for idx, (val, is_numeric) in enumerate(values):
                color = colors[idx % len(colors)]
                
                if isinstance(val, str):
                    # Team name - no color coding
                    table_html += f'<td>{val}</td>'
                elif not is_numeric:
                    # GP - no color coding
                    table_html += f'<td>{val}</td>'
                else:
                    # Only highlight the best performer
                    is_best = (val == max_val) if numeric_values else False
                    
                    if is_best and val_range > 0:
                        # Extract RGB from hex for best performer
                        r = int(color[1:3], 16)
                        g = int(color[3:5], 16)
                        b = int(color[5:7], 16)
                        
                        # Formatting based on stat type
                        if stat_key == "GP":
                            display_val = f"{int(val)}"
                        else:
                            display_val = f"{float(val):.1f}"
                            
                        # Highlight best performer with their color
                        table_html += f'<td style="background: rgba({r}, {g}, {b}, 0.7); font-weight: 700; border: 2px solid {color}; font-family: \'Outfit\', sans-serif;">{display_val}</td>'
                    else:
                        # Normal background for others
                        if stat_key == "GP":
                            display_val = f"{int(val)}"
                        else:
                            display_val = f"{float(val):.1f}"
                        table_html += f'<td style="font-weight: 500; font-family: \'Outfit\', sans-serif;">{display_val}</td>'
            
            table_html += '</tr>'
        
        table_html += '</tbody></table></div>'
        
        st.markdown(table_html, unsafe_allow_html=True)
        
    else:
        st.info("Select players to compare using the dropdown above.")


# --- FOOTER ---
st.divider()
st.markdown("""<div style='text-align: center; margin-top: 32px; padding: 24px;'>
<div style='color: var(--text-secondary); font-size: 0.875rem; font-family: "Space Grotesk", sans-serif;'>
Powered by <span style='color: var(--tappa-orange); font-weight: 600;'>Tappa Pro Analytics</span>
</div>
<div style='color: var(--text-secondary); font-size: 0.75rem; margin-top: 8px; font-family: "Space Grotesk", sans-serif;'>
Made by <span style='color: var(--tappa-orange); font-weight: 600;'>Kev Media</span> | Data from Basketball India
</div>
</div>""", unsafe_allow_html=True)
