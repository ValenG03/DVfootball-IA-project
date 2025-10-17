# Boca Juniors Matches vs Domestic Violence Calls - Streamlit App

This repo contains a Streamlit application that analyzes the relationship between Boca Juniors match weekends and domestic violence call volumes.

Files in the branch:
- app.py - Streamlit application
- requirements.txt - Python dependencies

How to run locally
1. Clone the repository and switch to a working branch:
   - git clone https://github.com/ValenG03/DVfootball-IA-project.git
   - cd DVfootball-IA-project
2. (Optional) Create a virtualenv and activate it:
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows
3. Install dependencies:
   - pip install -r requirements.txt
4. Place the two CSVs in the project root (or upload them via the app UI):
   - llamados-violencia-familiar-202407-Argentina.csv
   - Boca Juniors Results Tournament May-Dic-2024.csv
5. Run the app:
   - streamlit run app.py

Deploy to Streamlit Community Cloud:
1. Commit `app.py` and `requirements.txt` to a GitHub branch (e.g., `streamlit-app`) in this repository.
2. Push the branch to GitHub.
3. Go to https://share.streamlit.io and log in with GitHub.
4. Select this repository and the `streamlit-app` branch and deploy.
5. Make sure your CSVs are included in the repository or modify the app to fetch them from an accessible URL.

Notes:
- The football CSV may come with irregular columns/encodings. The app attempts to parse it robustly and will ask you to select columns if it can't detect them automatically.
- If you want the app to run automatically on Streamlit Cloud, include the CSV files in the repo (be mindful of privacy and size).
