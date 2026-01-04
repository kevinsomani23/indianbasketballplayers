"""Reusable UI components for the dashboard."""
import streamlit as st
from PIL import Image
import os


def render_header():
    """Render the dashboard header with logo and title."""
    c_title = st.container()
    with c_title:
        cl1, cl2 = st.columns([0.1, 0.9])
        with cl1:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.jpg")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                st.image(logo, width=120)
        with cl2:
            st.title("🏀 Tappa Pro Analytics Dashboard")
            st.caption("Advanced Basketball Statistics & Insights")
    st.divider()


def render_footer():
    """Render the dashboard footer."""
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p>Powered by Tappa Pro Analytics | Data Source: Genius Sports</p>
    </div>
    """, unsafe_allow_html=True)
