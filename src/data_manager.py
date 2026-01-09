
import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os

@st.cache_data(show_spinner=False)
def load_data(json_path=None):
    """Load the main JSON data. Trust data.json as source of truth."""
    try:
        # Use relative path for cloud deployment, fallback to absolute for local
        if json_path:
            actual_path = json_path
        else:
            # Try relative path first (for Streamlit Cloud)
            relative_path = "data/processed/data.json"
            # Fallback to staging absolute path for local development
            staging_path = r"h:\VIBE CODE\ind basketball\2staging\data\processed\data.json"
            
            if os.path.exists(relative_path):
                actual_path = relative_path
            elif os.path.exists(staging_path):
                actual_path = staging_path
            else:
                raise FileNotFoundError(f"data.json not found at {relative_path} or {staging_path}")

        with open(actual_path, "r", encoding='utf-8-sig') as f:
            data = json.load(f)
            
        # Placeholder for total_games and last_updated
        if isinstance(data, dict):
            # Check for wrapped structure first
            if "Matches" in data:
                total_games = len(data["Matches"])
            elif "matches" in data:
                total_games = len(data["matches"])
            else:
                # Assume dict keys are match IDs (production structure)
                total_games = len(data)
        else:
            # Plain list structure
            total_games = len(data)
            
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return data, total_games, last_updated
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return [], 0, "N/A"

@st.cache_data  
def load_category_map():
    """Load category map"""
    try:
        # Try both relative and absolute paths if needed, but relative usually works from root
        path = "data/raw/match_category_map.json"
        if not os.path.exists(path):
             path = r"h:\VIBE CODE\ind basketball\data\raw\match_category_map.json"
             
        with open(path, "r", encoding='utf-8-sig') as f:
            return json.load(f)
    except:
        return {}

@st.cache_data
def load_logos():
    try:
        path = "data/logos.json"
        if not os.path.exists(path):
             # Try prod path
             path = r"h:\VIBE CODE\ind basketball\2staging\data\logos.json" # Staging location
             if not os.path.exists(path):
                 path = r"h:\VIBE CODE\ind basketball\data\logos.json"

        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def load_manual_scores():
    try:
        path = "data/processed/manual_scores.json"
        if not os.path.exists(path):
            path = r"h:\VIBE CODE\ind basketball\2staging\data\processed\manual_scores.json"
            
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def load_schedule():
    """Load the compiled schedule CSV"""
    try:
        # Try relative path first (for Streamlit Cloud)
        relative_path = "compiled_schedule.csv"
        # Fallback to staging absolute path for local development
        staging_path = r"h:\VIBE CODE\ind basketball\2staging\compiled_schedule.csv"
        
        if os.path.exists(relative_path):
            df = pd.read_csv(relative_path)
        elif os.path.exists(staging_path):
            df = pd.read_csv(staging_path)
        else:
            return pd.DataFrame()
        return df
    except:
        return pd.DataFrame()
