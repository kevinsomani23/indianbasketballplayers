import streamlit as st
import os
import sys
import runpy

# Streamlit Cloud Entry Point Redirection
# This file exists to redirect the default 'streamlit_app.py' execution 
# to our actual main application file: src/hub_app.py

if __name__ == "__main__":
    # Define the path to the real main app
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, "src", "hub_app.py")
    
    if os.path.exists(app_path):
        # Run the application
        sys.argv = ["streamlit", "run", app_path]
        runpy.run_path(app_path, run_name="__main__")
    else:
        st.error(f"Could not find application at {app_path}")
