import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

st.set_page_config(page_title="Football and Domestic Violence", layout="wide")
st.title("⚽ Football and Domestic Violence in Argentina (2024)")

st.markdown("""
This analysis uses **Boca_2024_Whole_Year.csv** and **llamados-violencia-familiar-202407-Argentina.csv**.
We count the **number of calls per day** (based on `llamado_fecha`) and match them to the game dates.
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

    df_calls = df_calls.rename(columns={'llamado_fecha': 'call_date'})
    
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

fig, ax = plt.subplots(figsize=(6, 3))
ax.bar(calls_by_result[result_col], calls_by_result['call_count'], color="#1f77b4")
ax.set_xlabel("Boca result")
ax.set_ylabel("Average calls per day")
ax.set_title("Average calls by result")
fig.tight_layout()
st.pyplot(fig, use_container_width=True)

# -----------------------------
# 4) CHART: Calls and results combined
# -----------------------------
st.header("📅 Calls on match days (time series)")
merged_sorted = merged.sort_values('Date')

result_colors = {
    'W': '#2ca02c',
    'Win': '#2ca02c',
    'D': '#ff7f0e',
    'Draw': '#ff7f0e',
    'L': '#d62728',
    'Loss': '#d62728'
}
result_labels = {
    'W': 'Win',
    'Win': 'Win',
    'D': 'Draw',
    'Draw': 'Draw',
    'L': 'Loss',
    'Loss': 'Loss'
}

bar_colors = merged_sorted[result_col].map(result_colors).fillna('#1f77b4')

fig_combined, ax_combined = plt.subplots(figsize=(6, 3))
ax_combined.bar(merged_sorted['Date'], merged_sorted['call_count'], color=bar_colors)
ax_combined.set_xlabel("Match date")
ax_combined.set_ylabel("Number of calls")
ax_combined.set_title("Calls on match days by Boca result")
ax_combined.tick_params(axis='x', rotation=45)

legend_handles = []
seen_labels = set()
for result_value, color in result_colors.items():
    mask = merged_sorted[result_col] == result_value
    if mask.any():
        label = result_labels[result_value]
        if label not in seen_labels:
            legend_handles.append(Line2D([0], [0], color=color, lw=6, label=label))
            seen_labels.add(label)

if legend_handles:
    ax_combined.legend(handles=legend_handles, title="Result")

fig_combined.tight_layout()
st.pyplot(fig_combined, use_container_width=True)

# -----------------------------
# 5) CHART: Time trend on match days
# -----------------------------
st.header("📅 Calls on match days (time series)")

fig2, ax2 = plt.subplots(figsize=(6, 3))
ax2.plot(merged_sorted['Date'], merged_sorted['call_count'], marker='o', linestyle='-')
ax2.set_xlabel("Match date")
ax2.set_ylabel("Number of calls")
ax2.set_title("Call trend on match days")
ax2.tick_params(axis='x', rotation=45)
fig2.tight_layout()
st.pyplot(fig2, use_container_width=True)

# -----------------------------
# 6) CHART: Calls vs goal difference by venue
# -----------------------------
st.header("🎯 Calls vs goal difference by venue")

if {'Boca_Goals', 'Rival_Goals'}.issubset(merged.columns):
    goal_diff = merged['Boca_Goals'] - merged['Rival_Goals']
    venue_colors = {'Home': '#1f77b4', 'Away': '#ff7f0e'}
    venues_present = merged['Home_or_Away'].dropna().unique() if 'Home_or_Away' in merged.columns else []

    fig_scatter, ax_scatter = plt.subplots(figsize=(6, 3))

    if 'Home_or_Away' in merged.columns and len(venues_present) > 0:
        for venue in venues_present:
            mask = merged['Home_or_Away'] == venue
            ax_scatter.scatter(
                goal_diff[mask],
                merged.loc[mask, 'call_count'],
                color=venue_colors.get(venue, '#7f7f7f'),
                label=venue
            )
        ax_scatter.legend(title="Venue")
    else:
        ax_scatter.scatter(goal_diff, merged['call_count'], color='#1f77b4')

    ax_scatter.axvline(0, color='gray', linestyle='--', linewidth=1)
    ax_scatter.set_xlabel("Goal difference (Boca - Rival)")
    ax_scatter.set_ylabel("Number of calls")
    ax_scatter.set_title("Call volume vs goal difference")
    fig_scatter.tight_layout()
    st.pyplot(fig_scatter, use_container_width=True)
else:
    st.info("Columns 'Boca_Goals' and 'Rival_Goals' are required for this chart.")

# -----------------------------
# 6) CORRELATION: goals vs calls
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
# 7) DATA PREVIEW
# -----------------------------
st.header("🔍 Preview of combined data")
cols_show = [c for c in ['Date', 'Rival', result_col, 'Boca_Goals', 'Rival_Goals', 'call_count'] if c in merged.columns]
st.dataframe(merged[cols_show].head(20))
