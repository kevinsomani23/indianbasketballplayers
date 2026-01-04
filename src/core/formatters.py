"""Data formatting and styling utilities for display."""
import pandas as pd


def format_df(df, precision=0):
    """Format dataframe values based on column types and apply styling.
    
    Args:
        df: Pandas DataFrame to format
        precision: Decimal places for count stats (0 for totals, 1 for averages)
    
    Returns:
        Styled DataFrame with conditional formatting
    """
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
            if pd.api.types.is_integer_dtype(df[col]):
                format_dict[col] = "{:.0f}"
            else:
                format_dict[col] = f"{{:.{precision}f}}"
        elif pd.api.types.is_numeric_dtype(df[col]):
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
