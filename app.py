import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Football and Domestic Violence", layout="wide")
st.title("⚽ Football and Domestic Violence in Argentina (2024)")

st.markdown("""
This analysis uses **Boca_2024_Whole_Year.csv** and **llamados-violencia-familiar-202407-Argentina.csv**.
We count the **number of calls per day** (based on `call_date`, originally `llamado_fecha`) and match them to the game dates.
""")

# -----------------------------
# 1) FILE LOADING (matching your actual columns)
# -----------------------------
MATCHES_FILE = "Boca_2024_Whole_Year.csv"
CALLS_FILE = "llamados-violencia-familiar-202407-Argentina.csv"

@st.cache_data
def load_data(matches_path, calls_path):
    df_matches = pd.read_csv(matches_path)
    df_calls = pd.read_csv(calls_path)
    
    # Normalize relevant columns
    # Matches: includes 'Date', 'Boca_Goals', 'Rival_Goals', 'Result', 'Win_Draw_Loss'
    df_matches['Date'] = pd.to_datetime(df_matches['Date'], errors='coerce').dt.date

    # Calls: includes 'call_date' (call date, converted from 'llamado_fecha')
    df_calls['call_date'] = pd.to_datetime(df_calls['call_date'], errors='coerce').dt.date

    # Add the number of calls per day
    calls_daily = (
        df_calls
        .groupby('call_date', as_index=False)
        .size()
        .rename(columns={'call_date': 'Date', 'size': 'call_count'})
    )

    return df_matches, calls_daily

try:
    df_matches, calls_daily = load_data(MATCHES_FILE, CALLS_FILE)
except Exception as e:
    st.error(f"Error loading files: {e}")
    st.stop()
    
st.success("Files loaded successfully ✅")

# -----------------------------
# 2) MERGE BY DATE
# -----------------------------
merged = pd.merge(df_matches, calls_daily, on='Date', how='inner')

# If the result column is missing, build it from goals (your data already has it)
if 'Win_Draw_Loss' in merged.columns:
    result_col = 'Win_Draw_Loss'
elif 'Result' in merged.columns:
    result_col = 'Result'
else:
    result_col = 'Result'
    merged[result_col] = merged.apply(
        lambda r: 'Win' if r['Boca_Goals'] > r['Rival_Goals']
        else ('Draw' if r['Boca_Goals'] == r['Rival_Goals'] else 'Loss'),
        axis=1
    )

# -----------------------------
# 3) CHART: Average calls by result
# -----------------------------
st.header("📊 Average calls by match result")

calls_by_result = merged.groupby(result_col)['call_count'].mean().reset_index()

fig, ax = plt.subplots()
ax.bar(calls_by_result[result_col], calls_by_result['call_count'])
ax.set_xlabel("Boca result")
ax.set_ylabel("Average calls per day")
ax.set_title("Average calls by result")
st.pyplot(fig)

# -----------------------------
# 4) CHART: Time trend on match days
# -----------------------------
st.header("📅 Calls on match days (time series)")
merged_sorted = merged.sort_values('Date')

fig2, ax2 = plt.subplots()
ax2.plot(merged_sorted['Date'], merged_sorted['call_count'], marker='o', linestyle='-')
ax2.set_xlabel("Match date")
ax2.set_ylabel("Number of calls")
ax2.set_title("Call trend on match days")
plt.xticks(rotation=45)
st.pyplot(fig2)

# -----------------------------
# 5) CORRELATION: goals vs calls
# -----------------------------
st.header("📈 Correlation (Boca goals vs calls)")

if 'Boca_Goals' in merged.columns:
    corr = merged['Boca_Goals'].corr(merged['call_count'])
    st.metric("Correlation coefficient", f"{corr:.3f}")
else:
    st.info("Column 'Boca_Goals' not found in the matches CSV.")

st.markdown("""
- **Negative value** → more goals, **fewer** calls.  
- **Positive value** → more goals, **more** calls.
""")

# -----------------------------
# 6) DATA PREVIEW
# -----------------------------
st.header("🔍 Preview of combined data")
cols_show = [c for c in ['Date', 'Rival', result_col, 'Boca_Goals', 'Rival_Goals', 'call_count'] if c in merged.columns]
st.dataframe(merged[cols_show].head(20))
