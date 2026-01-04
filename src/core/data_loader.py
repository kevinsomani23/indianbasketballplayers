"""Data loading utilities for tournament analytics."""
import streamlit as st
import json
import os

@st.cache_data
def load_data_v8():
    """Load tournament data from data.json with caching."""
    # Go up 3 levels: src/core/data_loader.py -> src/core/ -> src/ -> project_root/
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "data.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)
