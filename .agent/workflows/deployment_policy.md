---
description: Strict policy for deployment and git operations
---

# Deployment Safety Protocol

**CRITICAL RULE: DO NOT PUSH CODE WITHOUT EXPLICIT PERMISSION.**

1.  **Verification First**: Always verify changes locally (using scripts or browser tests) and present the results to the user.
2.  **Explicit Approval**: You must ask: "Do I have permission to push this to main?" and wait for a clear "Yes".
3.  **No "Safe-Keeping"**: Never push code just to "save" it. Use local branches or stashes if needed, but never touch the remote `main` branch without approval.
4.  **Revert Immediately**: If a push is made accidentally without approval, revert it immediately and notify the user.

## Staging vs. Production Workflow

- **Staging Repo**: `https://github.com/kevinsomani23/tappastatsapp` (Use `git push staging main`)
- **Production Repo**: `https://github.com/kevinsomani23/indianbasketballplayers` (Use `git push tappa main`)

**Protocol**:

1.  **Local Verification**: Verify changes locally on your machine first.
2.  **Staging Deployment**: Push to **Staging** (`git push staging main`) and ask user to verify on the test app.
3.  **Production Deployment**: Only after explicit user confirmation ("Push to main"), push to **Production** (`git push tappa main`).

## Entry Point Quirk (CRITICAL)

- **Staging**: Runs `streamlit_app.py` (Standard).
- **Production**: Locked to run `src/hub_app.py`.
  - **Consequence**: Code in `streamlit_app.py` (like the Header) is ignored in Production.
  - **Workaround**: You must manually inject header/branding updates directly into `src/hub_app.py` for them to appear on Production.

## Usage-Based Upload Policy (Crucial Data Only)

- **Minimizing Footprint**: Only upload data strictly necessary for the application to function.
- **Whitelisted**: `data/processed/data.json`, `src/*.py`, `.streamlit/config.toml`, `requirements.txt`.
- **Blacklisted**: CSVs (e.g., `matches/*.csv`), Text files (e.g., `data/links/*.txt`, `verification_results.txt`), Scripts (`scripts/*.py`), Debug files.
- **Rule**: Artifacts used for generation/verification but NOT used by `hub_app.py` must stay local (or be gitignored).
