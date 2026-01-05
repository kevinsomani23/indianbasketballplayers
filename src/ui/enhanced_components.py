"""
Enhanced UI Components for Basketball Analytics Dashboard
Reusable modern components with glassmorphism, animations, and premium design
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json

def inject_custom_css():
    """Inject enhanced CSS with modern design system"""
    # Combine everything into one clean injection to avoid multiple markdown blocks
    # Using a single triple-quoted string that starts immediately to avoid leading \n
    css = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&family=Montserrat:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
    /* GLOBAL RESET & TYPOGRAPHY */
    :root {
        --tappa-orange: #ff8533;
        --tappa-orange-glow: rgba(255, 133, 51, 0.4);
        --bg-glass: rgba(18, 18, 18, 0.85);
        --border-glass: rgba(255, 255, 255, 0.1);
        --text-primary: #ffffff;
        --text-secondary: #a0a0a0;
        --text-muted: #707070;
        --accent-glow: 0 0 20px rgba(255, 133, 51, 0.25);
    }

    .stApp {
        background-color: #000000 !important;
    }

    body, p, span, div {
        font-family: 'Space Grotesk', sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.02em !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }

    .gradient-text {
        background: linear-gradient(135deg, #ffffff 0%, #a0a0a0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
    }

    /* Ensure all generic text is white */
    p, span, div, label {
        color: #ffffff !important;
    }

    /* Target Streamlit Widget Labels Specifically */
    .stWidgetLabel, label[data-testid="stWidgetLabel"], .stRadio label, .stSelectbox label, .stSlider label {
        color: #ffffff !important;
    }
    
    .stWidgetLabel p, label[data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Target Radio button options */
    [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
    }
    
    div[role="radiogroup"] label p {
        color: #ffffff !important;
    }

    /* GLASS CARD SYSTEM */
    .glass-card {
        background: var(--bg-glass);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
    }

    /* BUTTONS */
    .stButton > button {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        border-color: var(--tappa-orange) !important;
        background-color: rgba(255, 133, 51, 0.1) !important;
        box-shadow: var(--accent-glow) !important;
    }

    .stButton > button[kind="primary"] {
        background-color: rgba(255, 133, 51, 0.15) !important;
        border: 1px solid var(--tappa-orange) !important;
        color: white !important;
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 2px solid var(--border-glass);
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--text-secondary);
        font-weight: 700;
        text-transform: uppercase;
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        color: var(--tappa-orange) !important;
        border-bottom: 3px solid var(--tappa-orange) !important;
    }

    /* SUB-NAVIGATION PILLS */
    .sub-nav-pill {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 30px !important;
        padding: 6px 16px !important;
        font-size: 0.8rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase !important;
    }

    .sub-nav-pill-active {
        background: var(--tappa-orange) !important;
        border-color: var(--tappa-orange) !important;
        color: white !important;
        box-shadow: var(--accent-glow) !important;
    }

    /* DATAFRAME & TABLES */
    div[data-testid="stDataFrame"] {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 12px;
        border: 1px solid var(--border-glass);
        overflow: hidden;
    }

    /* SCROLLBAR */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--tappa-orange); }

    /* MOBILE ADJUSTMENTS */
    @media (max-width: 768px) {
        .main .block-container { padding: 1.5rem 1rem !important; }
        h1 { font-size: 1.8rem !important; }
        .stButton > button { font-size: 0.8rem !important; padding: 0.4rem 0.8rem !important; }
    }

    /* HIGHLIGHTS */
    .highlight-max {
        background: rgba(255, 133, 51, 0.45) !important;
        color: white !important;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
        font-weight: 700 !important;
    }

    /* AGGRESSIVE HIDING OF STREAMLIT UI */
    header, [data-testid="stHeader"], .stApp > header {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    
    #MainMenu, footer, [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
    }
</style>"""
    st.markdown(css, unsafe_allow_html=True)


def create_stat_card(label, value, subtitle=None, trend=None, color="primary"):
    """Create a modern stat card with glassmorphism"""
    
    color_map = {
        "primary": "var(--tappa-orange)",
        "success": "var(--success)",
        "warning": "var(--warning)",
        "teal": "#888888"
    }
    
    card_color = color_map.get(color, color_map["primary"])
    
    trend_html = ""
    if trend:
        trend_symbol = "▲" if trend > 0 else "▼" if trend < 0 else "—"
        trend_color = "var(--success)" if trend > 0 else "var(--warning)" if trend < 0 else "var(--text-secondary)"
        trend_html = f"""
        <div style="margin-top: 8px; font-size: 0.875rem; color: {trend_color}; font-family: 'Space Grotesk', sans-serif;">
            {trend_symbol} {abs(trend):.1f}%
        </div>
        """
    
    subtitle_html = f"<div style='color: var(--text-secondary); font-size: 0.875rem; margin-top: 4px; font-family: \"Space Grotesk\", sans-serif;'>{subtitle}</div>" if subtitle else ""
    
    html = f"""<div class="glass-card animate-fade-in" style="text-align: center; min-height: 140px;">
<div class="stat-label" style="color: var(--text-secondary); font-size: 0.7rem; margin-bottom: 12px;">
{label}
</div>
<div class="score-display" style="font-size: 2.5rem; font-weight: 700; color: {card_color}; line-height: 1;">
{value}
</div>
{subtitle_html}
{trend_html}
</div>"""
    
    st.markdown(html, unsafe_allow_html=True)


def create_team_score_card(team_name, score, logo_path=None, mvp_name=None, mvp_score=None, is_winner=False):
    """Create animated team score card"""
    
    winner_glow = "box-shadow: 0 0 30px rgba(209, 107, 7, 0.6);" if is_winner else ""
    animation = "animation: pulse 2s infinite;" if is_winner else ""
    
    logo_html = f'<img src="{logo_path}" style="width: 80px; height: 80px; object-fit: contain; margin-bottom: 16px;" />' if logo_path else ""
    
    mvp_html = ""
    if mvp_name and mvp_score:
        mvp_html = f"""<div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-glass);">
<div class="stat-label" style="color: var(--text-secondary); font-size: 0.7rem; margin-bottom: 4px;">MVP</div>
<div style="color: var(--text-primary); font-size: 1rem; font-weight: 600; font-family: 'Space Grotesk', sans-serif;">{mvp_name}</div>
<div style="color: var(--tappa-orange); font-size: 0.875rem; font-family: 'Space Grotesk', sans-serif;">{mvp_score} GmScr</div>
</div>"""
    
    html = f"""<div class="glass-card animate-slide-in" style="text-align: center; {winner_glow} {animation}">
{logo_html}
<div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; font-family: 'General Sans', sans-serif;">
{team_name}
</div>
<div class="score-display" style="font-size: 4rem; font-weight: 800; background: linear-gradient(135deg, var(--tappa-orange), var(--accent-highlight)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1;">
{score}
</div>
{mvp_html}
</div>"""
    
    st.markdown(html, unsafe_allow_html=True)


def create_comparison_bar_chart(categories, team1_values, team2_values, team1_name, team2_name):
    """Create horizontal bar chart for team comparison"""
    
    fig = go.Figure()
    
    # Team 1 bars (left side, negative values for left alignment)
    fig.add_trace(go.Bar(
        y=categories,
        x=[-v for v in team1_values],
        name=team1_name,
        orientation='h',
        marker=dict(
            color='#d16b07',  # Tappa orange
            line=dict(color='#d16b07', width=2)
        ),
        text=team1_values,
        textposition='auto',
        hovertemplate=f'{team1_name}: %{{text}}<extra></extra>'
    ))
    
    # Team 2 bars (right side)
    fig.add_trace(go.Bar(
        y=categories,
        x=team2_values,
        name=team2_name,
        orientation='h',
        marker=dict(
            color='#888888',  # Gray for contrast
            line=dict(color='#888888', width=2)
        ),
        text=team2_values,
        textposition='auto',
        hovertemplate=f'{team2_name}: %{{text}}<extra></extra>'
    ))
    
    # Layout
    max_val = max(max(team1_values), max(team2_values))
    fig.update_layout(
        barmode='overlay',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a0aec0', size=12),
        xaxis=dict(
            range=[-max_val*1.2, max_val*1.2],
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=True,
            zerolinecolor='rgba(255,255,255,0.3)',
            zerolinewidth=2
        ),
        yaxis=dict(
            showgrid=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


def create_leader_board(df, stat_col, title, top_n=10, show_team=True):
    """Create visual leader board with ultra-compact professional design"""
    
    if df.empty or stat_col not in df.columns:
        st.info(f"No data available for {title}")
        return
    
    # Sort and get top N
    df_sorted = df.nlargest(top_n, stat_col).reset_index(drop=True)
    
    st.markdown(f"""<div style="margin-bottom: 12px;">
<h4 style="font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-primary); margin: 0 0 12px 0; border-left: 3px solid var(--tappa-orange); padding-left: 10px;">
{title}
</h4>
</div>""", unsafe_allow_html=True)
    
    for idx, row in df_sorted.iterrows():
        rank = idx + 1
        player = str(row.get('Player', row.get('Player_Name', 'Unknown')))
        stat_value = float(row[stat_col])
        team = str(row.get('Team', ''))
        
        # Clean player name redundancy
        display_name = player
        if " (" in display_name:
            display_name = display_name.split(" (")[0]
            
        # Revert to decimal form for precision
        display_stat = f"{stat_value:.1f}"
            
        # Styling for top 3
        if rank == 1:
            rank_bg = "background: linear-gradient(135deg, #ff8533, #d16b07);"
            rank_color = "#000000"
            border_color = "#d16b07"
        elif rank <= 3:
            rank_bg = "background: rgba(209, 107, 7, 0.1);"
            rank_color = "#ff8533"
            border_color = "rgba(209, 107, 7, 0.2)"
        else:
            rank_bg = "background: rgba(255,255,255,0.03);"
            rank_color = "#999"
            border_color = "rgba(255,255,255,0.05)"
        
        # Progress bar width
        max_val = df_sorted[stat_col].max()
        progress_pct = (stat_value / max_val * 100) if max_val > 0 else 0
        
        html = f"""<div style="background: rgba(255,255,255,0.02); border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; border: 1px solid {border_color}; transition: all 0.2s ease;">
<div style="display: flex; justify-content: space-between; align-items: center;">
<div style="display: flex; align-items: center; gap: 10px; flex: 1;">
<div style="{rank_bg} font-family: 'Space Grotesk', sans-serif; font-size: 0.8rem; font-weight: 800; color: {rank_color}; min-width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; border-radius: 4px;">
{rank}
</div>
<div style="flex: 1;">
<div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary); margin-bottom: 0px; font-family: 'Space Grotesk', sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px;">
{display_name}
</div>
<div style="font-size: 0.65rem; color: var(--text-muted); font-weight: 500; font-family: 'Space Grotesk', sans-serif; opacity: 0.7; text-transform: uppercase;">
{team if show_team else ""}
</div>
</div>
</div>
<div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 45px;">
<div style="font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 800; color: var(--tappa-orange); line-height: 1;">
{display_stat}
</div>
<div style="background: rgba(255,255,255,0.05); height: 3px; border-radius: 1.5px; overflow: hidden; width: 30px; margin-top: 4px;">
<div style="background: var(--tappa-orange); height: 100%; width: {progress_pct}%; border-radius: 1.5px;"></div>
</div>
</div>
</div>
</div>"""
        
        st.markdown(html, unsafe_allow_html=True)

def create_four_factors_chart(team1_name, stats1, team2_name, stats2):
    """
    Create a specialized chart for Four Factors comparison.
    stats1/stats2: dicts with keys 'eFG%', 'TO Ratio', 'OREB%', 'FT Rate' and numeric values.
    """
    factors = ['eFG%', 'TO Ratio', 'OREB%', 'FT Rate']
    
    # Extract values ensuring order
    v1 = [stats1.get(f, 0) for f in factors]
    v2 = [stats2.get(f, 0) for f in factors]
    
    fig = go.Figure()
    
    # Team 1 (Left side)
    fig.add_trace(go.Bar(
        y=factors,
        x=[-v for v in v1], # Negative for left alignment
        name=team1_name,
        orientation='h',
        marker=dict(color='#d16b07'),
        text=[f"{v:.1f}%" if 'Ratio' not in f else f"{v:.1f}" for f, v in zip(factors, v1)],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{team1_name} {f}: {v:.1f}" for f, v in zip(factors, v1)]
    ))
    
    # Team 2 (Right side)
    fig.add_trace(go.Bar(
        y=factors,
        x=v2,
        name=team2_name,
        orientation='h',
        marker=dict(color='#888888'),
        text=[f"{v:.1f}%" if 'Ratio' not in f else f"{v:.1f}" for f, v in zip(factors, v2)],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{team2_name} {f}: {v:.1f}" for f, v in zip(factors, v2)]
    ))
    
    # Dynamic Range
    max_val = max(max(v1) if v1 else 0, max(v2) if v2 else 0)
    limit = max_val * 1.25 if max_val > 0 else 100
    
    fig.update_layout(
        barmode='overlay',
        height=250, # Compact
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(
            range=[-limit, limit],
            showticklabels=False,
            visible=False
        ),
        yaxis=dict(
            color='#b0b0b0',
            tickfont=dict(size=12, family="Inter")
        )
    )
    
    return fig

def render_html_scoreboard(q_data, t1, t2):
    """Render a custom HTML scoreboard table to match the glassmorphic theme"""
    
    # Extract data
    q1_row = [q_data["Q1"][0], q_data["Q2"][0], q_data["Q3"][0], q_data["Q4"][0], q_data["T"][0]]
    q2_row = [q_data["Q1"][1], q_data["Q2"][1], q_data["Q3"][1], q_data["Q4"][1], q_data["T"][1]]
    
    html = f"""
    <div class="glass-card" style="padding: 16px; margin-bottom: 24px; overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Space Grotesk', sans-serif;">
            <thead>
                <tr style="border-bottom: 1px solid var(--border-glass);">
                    <th style="text-align: left; padding: 12px; color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase;">Team</th>
                    <th style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 0.8rem;">Q1</th>
                    <th style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 0.8rem;">Q2</th>
                    <th style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 0.8rem;">Q3</th>
                    <th style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 0.8rem;">Q4</th>
                    <th style="text-align: center; padding: 12px; color: var(--text-primary); font-size: 0.8rem; font-weight: 800;">TOTAL</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid var(--border-glass);">
                    <td style="padding: 12px; font-weight: 800; color: var(--text-primary); font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; font-size: 1rem;">{t1}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q1_row[0]}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q1_row[1]}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q1_row[2]}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q1_row[3]}</td>
                    <td style="text-align: center; padding: 12px; font-weight: 900; color: var(--tappa-orange); font-size: 1.4rem; font-family: 'Outfit', sans-serif;">{q1_row[4]}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: 800; color: var(--text-primary); font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; font-size: 1rem;">{t2}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q2_row[0]}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q2_row[1]}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q2_row[2]}</td>
                    <td style="text-align: center; padding: 12px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 1.1rem;">{q2_row[3]}</td>
                    <td style="text-align: center; padding: 12px; font-weight: 900; color: var(--tappa-orange); font-size: 1.4rem; font-family: 'Outfit', sans-serif;">{q2_row[4]}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    return html

def apply_dataframe_style(df):
    """Apply dark theme to pandas staging"""
    # If it's already a Styler (from format_df), use it directly. 
    # Otherwise, access .style
    styler = df if hasattr(df, "set_properties") else df.style
    
    # Hide index to remove the white column on the left
    styler.hide(axis="index")
    
    # Apply comprehensive dark styles
    return styler.set_properties(**{
        'background-color': '#1a1a1a',
        'color': '#ffffff',
        'border-color': '#333333'
    }).set_table_styles([
        {
            'selector': 'th', 
            'props': [
                ('background-color', '#0f0f0f'), 
                ('color', '#b0b0b0'), 
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('vertical-align', 'middle'),
                ('border-bottom', '1px solid #333')
            ]
        },
        {'selector': 'th.col_heading', 'props': [('background-color', '#0f0f0f'), ('color', '#b0b0b0')]},
        {'selector': 'th.index_name', 'props': [('background-color', '#0f0f0f'), ('color', '#b0b0b0')]},
        {'selector': 'tr:hover', 'props': [('background-color', '#252525')]}
    ])

def render_html_table(df, highlight_cols=None, star_players=None, outlier_thresholds=None):
    """
    Render a styled HTML table with advanced conditional formatting.
    - star_players: List of player names whose rows should be highlighted.
    - outlier_thresholds: Dict of col -> threshold. Cells exceeding this get an outlier glow.
    """
    if df.empty: return ""
    
    if highlight_cols is None:
        highlight_cols = [
            "PTS", "REB", "AST", "STL", "BLK", "Eff", "GmScr", 
            "FIC", "PIE", "TS%", "eFG%", "USG%", "OFFRTG", "DEFRTG", "NETRTG", "FG%", "3P%", "FT%", "AST/TO"
        ]

    if star_players is None: star_players = []
    if outlier_thresholds is None: outlier_thresholds = {}

    # Calculate local max values just in case outlier_thresholds aren't provided
    max_values = {}
    if not outlier_thresholds:
        for col in df.columns:
            if col in highlight_cols:
                try:
                    numeric_vals = pd.to_numeric(df[col], errors='coerce')
                    if not numeric_vals.dropna().empty:
                        max_values[col] = numeric_vals.max()
                except:
                    pass

    # Generate Table Headers
    headers = "".join([f'<th style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 0.8rem; background: rgba(0,0,0,0.3); border-bottom: 2px solid var(--border-glass); font-family: \'Space Grotesk\', sans-serif;">{col}</th>' for col in df.columns])
    
    # Generate Rows
    rows_html = ""
    for _, row in df.iterrows():
        p_name = str(row.get('Player', row.get('PLAYER', '')))
        is_star = any(star in p_name for star in star_players) if p_name else False
        
        row_style = "transition: background 0.2s;"
        if is_star:
            row_style += "background: rgba(255, 133, 51, 0.08);"

        cells = ""
        for col in df.columns:
            val = row[col]
            display_val = val
            
            # Formatting
            if isinstance(val, (int, float, np.integer, np.floating)):
                if val % 1 == 0:
                    display_val = f"{int(val)}"
                else:
                    display_val = f"{float(val):.1f}"
            
            # Base style
            style = f'text-align: center; padding: 10px; color: white; border-bottom: 1px solid var(--border-glass); transition: all 0.2s ease;'
            
            # 1. Outlier/Leader Highlight (Cell level)
            is_highlighted = False
            try:
                numeric_val = float(val)
                if col in outlier_thresholds:
                    if numeric_val >= outlier_thresholds[col] and numeric_val > 0:
                        is_highlighted = True
                elif col in max_values:
                    if numeric_val == max_values[col] and numeric_val > 0:
                        is_highlighted = True
                
                if is_highlighted:
                    style += 'background: rgba(255, 133, 51, 0.45); border-bottom: 2px solid var(--tappa-orange); font-weight: 800; text-shadow: 0 0 10px rgba(255,133,51,0.5);'
                else:
                    # Subtle background to maintain uniformity
                    style += 'background: rgba(255, 255, 255, 0.02);'
            except:
                style += 'background: rgba(255, 255, 255, 0.02);'
            
            # 2. Player names - Left align + Clean Redundancy
            if col in ["Player", "PLAYER"]:
                # Strip (Team) if present in name to avoid redundancy with the Team column
                if isinstance(display_val, str) and " (" in display_val:
                    display_val = display_val.split(" (")[0]
                    
                style = style.replace("text-align: center", "text-align: left; padding-left: 15px")
                style += "font-family: 'Space Grotesk', sans-serif; font-weight: 700;"
                if is_star:
                    style += "color: var(--tappa-orange);"
            else:
                style += "font-family: 'Outfit', sans-serif;"

            cells += f'<td style="{style}">{display_val}</td>'
        
        rows_html += f'<tr style="{row_style}">{cells}</tr>'

    html = f"""
    <div style="
        background: var(--bg-glass);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        overflow-x: auto;
        margin-bottom: 24px;
        position: relative;
    ">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Space Grotesk', sans-serif; font-size: 0.85rem; min-width: 600px;">
            <thead style="position: sticky; top: 0; z-index: 10;">
                <tr>{headers}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    return html

def render_four_factors_table(df):
    """Render the Four Factors comparison as a premium HTML table"""
    # Standardize column names and values
    metrics = df.columns.tolist()
    teams = df.index.tolist()
    
    # Header cells
    headers = "".join([f'<th style="text-align: center; padding: 16px; color: var(--text-muted); font-size: 0.8rem; background: rgba(0,0,0,0.3); border-bottom: 2px solid var(--border-glass); font-family: \'Space Grotesk\', sans-serif;">{col}</th>' for col in ["TEAM"] + metrics])
    
    # Body rows
    rows_html = ""
    for team in teams:
        team_cell = f'<td style="text-align: left; padding: 16px 24px; color: var(--text-primary); background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--border-glass); font-weight: 800; font-family: \'Space Grotesk\', sans-serif; text-transform: uppercase;">{team}</td>'
        
        stat_cells = ""
        for metric in metrics:
            val = df.loc[team, metric]
            display_val = f"{val:.1f}" if isinstance(val, (int, float)) else val
            
            stat_cells += f'<td style="text-align: center; padding: 16px; color: white; background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--border-glass); font-family: \'Outfit\', sans-serif; font-size: 1.2rem; font-weight: 800;">{display_val}</td>'
        
        rows_html += f'<tr>{team_cell}{stat_cells}</tr>'

    html = f"""
    <div class="glass-card" style="overflow-x: auto; margin-bottom: 24px;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr>{headers}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    return html

    return html
