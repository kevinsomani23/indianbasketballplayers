# 🚀 VIBE / Tappa Stats - Workflow & Deployment Protocol

## 1. 🏗️ The 3-Tier Environment Structure

We strictly follow a linear promotion pipeline. Code and data flow from left to right.

| Tier           | Folder Path                                | Purpose                                                                                                                                                                                                        |
| :------------- | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. DEV**     | `h:\VIBE CODE\ind basketball\new features` | **Sandbox.** <br> - Develop new features here.<br> - Messy code / breaking changes allowed.<br> - _No user approval needed to edit._                                                                           |
| **2. STAGING** | `h:\VIBE CODE\ind basketball\staging`      | **Integration & Data Testing.** <br> - Merge `new features` + new `data` (scraped matches) here.<br> - Validate that new code works with real data.<br> - **USER APPROVAL REQUIRED** before promoting to Prod. |
| **3. PROD**    | `h:\VIBE CODE\ind basketball\prod`         | **Live Production.** <br> - The "Golden Copy".<br> - Connected to the live Streamlit app.<br> - _Only_ receives content copied from Staging _after_ full approval.                                             |

---

## 2. 🔄 Promotion Workflow

### **Step 1: Develop (in `new features`)**

- Write code, edit `src/hub_app.py`, change CSS, etc.
- Test locally: `streamlit run src/hub_app.py`.

### **Step 2: Stage (in `staging`)**

- **Copy Code**: Copy updated logic from `new features`.
- **Update Data**: Run scraping scripts (`scripts/scrape_75th_all.py`) here to populate `data/`.
- **Verify**: Check `compiled_schedule.csv`, Standings, and Stats accuracy.
- **Request Approval**: Ask user to review Staging.

### **Step 3: Deploy (to `prod`)**

- **Trigger**: ONLY after User says "Approved".
- **Action**: Copy the _entire_ contents (Code + Data) from `staging` → `prod`.
- **Push**: Git push from `prod` to the `production` remote (`indianbasketballplayers`).

---

## 3. 🛡️ .gitignore Policy

- **Synchronization**: Any change to `.gitignore` (e.g., ignoring a new temp file) must be manually synchronized across all three folders.
- **Approval**: Like code, `.gitignore` changes should be verified in `new features` first, then propagated to `staging` and `prod` with user consent.

## 4. 📂 Directory Role Recap

- **`src/`**: Logic (Analytics, UI, App).
- **`scripts/`**: Tools (Scrapers, Verifiers).
- **`data/`**: The Lifeblood (JSONs, Links). **Crucial**: Data integrity must be verified in Staging before touching Prod.
