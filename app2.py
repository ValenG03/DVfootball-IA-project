import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go

st.set_page_config(
    page_title="Football & Domestic Violence – AMBA 2024",
    layout="wide"
)

st.title("⚽ Football & Domestic Violence – AMBA 2024")
st.markdown("""
Very basic demo app that combines:

- **Boca_2024_Whole_Year.csv**
- **River_Plate_2024_Whole_Year.csv**
- **DV-Calls-AMBA.csv** (domestic violence calls, AMBA region)

and matches **daily call counts** with **Boca & River matches**.
""")

# -----------------------------
# 1) FILE PATHS – same folder as this script
# -----------------------------
BASE_DIR = Path(__file__).parent

BOCA_FILE = BASE_DIR / "Boca_2024_Whole_Year.csv"
RIVER_FILE = BASE_DIR / "River_Plate_2024_Whole_Year.csv"
DV_FILE    = BASE_DIR / "DV-Calls-AMBA.csv"


@st.cache_data
def load_raw_data():
    # Read CSVs
    df_boca = pd.read_csv(BOCA_FILE)
    df_river = pd.read_csv(RIVER_FILE)
    df_dv = pd.read_csv(DV_FILE)

    # -------- Boca --------
    df_boca["Date"] = pd.to_datetime(df_boca["Date"])
    df_boca["Team"] = "Boca Juniors"
    df_boca["Opponent"] = df_boca["Rival"]
    df_boca["Goals_For"] = df_boca["Boca_Goals"]
    df_boca["Goals_Against"] = df_boca["Rival_Goals"]
    df_boca["Competition"] = df_boca["Tournament"]

    boca_cols = [
        "Date",
        "Team",
        "Opponent",
        "Goals_For",
        "Goals_Against",
        "Competition",
        "Home_or_Away",
        "Win_Draw_Loss",
        "Stadium",
    ]
    df_boca_clean = df_boca[boca_cols]

    # -------- River --------
    df_river["Date"] = pd.to_datetime(df_river["Date"])

    # Split "Score" like "4-0" → home / away goals
    parts = df_river["Score"].str.split("-", expand=True)
    df_river["Home_Goals"] = pd.to_numeric(parts[0], errors="coerce")
    df_river["Away_Goals"] = pd.to_numeric(parts[1], errors="coerce")

    # River as home
    river_home = df_river[df_river["Home"] == "River Plate"].copy()
    river_home["Team"] = "River Plate"
    river_home["Opponent"] = river_home["Away"]
    river_home["Goals_For"] = river_home["Home_Goals"]
    river_home["Goals_Against"] = river_home["Away_Goals"]
    river_home["Home_or_Away"] = "Home"

    # River as away
    river_away = df_river[df_river["Away"] == "River Plate"].copy()
    river_away["Team"] = "River Plate"
    river_away["Opponent"] = river_away["Home"]
    river_away["Goals_For"] = river_away["Away_Goals"]
    river_away["Goals_Against"] = river_away["Home_Goals"]
    river_away["Home_or_Away"] = "Away"

    df_river_all = pd.concat([river_home, river_away], ignore_index=True)
    df_river_all["Competition"] = df_river_all["Competition"]
    df_river_all["Stadium"] = None  # not provided in River CSV

    river_cols = [
        "Date",
        "Team",
        "Opponent",
        "Goals_For",
        "Goals_Against",
        "Competition",
        "Home_or_Away",
        "Win_Draw_Loss",
        "Stadium",
    ]
    df_river_clean = df_river_all[river_cols]

    # -------- Combine matches --------
    df_matches = pd.concat([df_boca_clean, df_river_clean], ignore_index=True)
    df_matches = df_matches.sort_values("Date")

    # -------- DV per day (AMBA) --------
    df_dv["llamado_fecha"] = pd.to_datetime(df_dv["llamado_fecha"])
    dv_daily = (
        df_dv.groupby("llamado_fecha")
        .size()
        .reset_index(name="dv_calls_AMBA")
    )
    dv_daily = dv_daily.rename(columns={"llamado_fecha": "Date"})
    dv_daily = dv_daily.sort_values("Date")

    # Merge DV with matches on date
    df_matches_dv = pd.merge(
        df_matches,
        dv_daily,
        on="Date",
        how="left",
    )

    return df_matches, dv_daily, df_matches_dv


# Load data once (cached)
df_matches, dv_daily, df_matches_dv = load_raw_data()

# -----------------------------
# 2) SIDEBAR CONTROLS
# -----------------------------
st.sidebar.header("Filters")

team_options = ["All", "Boca Juniors", "River Plate"]
selected_team = st.sidebar.selectbox("Team", team_options)

view_options = ["Matches + DV calls", "DV daily time series", "Raw data"]
selected_view = st.sidebar.radio("View", view_options)

# Filter by team if needed
if selected_team == "All":
    df_matches_filtered = df_matches_dv.copy()
else:
    df_matches_filtered = df_matches_dv[df_matches_dv["Team"] == selected_team]

# -----------------------------
# 3) MAIN VIEWS
# -----------------------------
if selected_view == "Matches + DV calls":
    st.subheader("Matches with domestic violence calls (AMBA) on the same date")

    st.markdown("""
    Each row is a match (Boca or River) with the **number of DV calls in AMBA**
    on that date.
    """)

    st.dataframe(df_matches_filtered)

    st.markdown("#### Basic summary")
    st.write("Total matches in selection:", len(df_matches_filtered))

    total_calls_on_match_days = df_matches_filtered["dv_calls_AMBA"].sum()
    st.write(
        "Sum of DV calls on those match days (AMBA):",
        int(total_calls_on_match_days)
    )

elif selected_view == "DV daily time series":
    st.subheader("Daily DV calls (AMBA) – Full period")

    st.markdown("""
    This is the aggregated number of domestic violence calls per day
    in the **Metropolitana / AMBA** region (from `DV-Calls-AMBA.csv`).
    """)

    st.line_chart(
        dv_daily.set_index("Date")["dv_calls_AMBA"],
        height=400,
    )

    st.markdown("Preview of daily data:")
    st.dataframe(dv_daily)

else:  # "Raw data"
    tab1, tab2, tab3 = st.tabs(
        ["Matches (Boca + River)", "DV calls (daily)", "Matches + DV merged"]
    )

    with tab1:
        st.subheader("Raw matches data (Boca + River)")
        st.dataframe(df_matches)

    with tab2:
        st.subheader("DV daily counts – AMBA")
        st.dataframe(dv_daily)

    with tab3:
        st.subheader("Matches + DV calls merged on Date")
        st.dataframe(df_matches_dv)

st.markdown("---")
st.caption(
    "Very simple prototype. For deeper analysis you may need more detailed modelling "
    "(e.g. hour of match vs. hour of calls, lagged effects, controls, etc.)."
)


# -----------------------------
# 4) QUICK OVERVIEW GRAPHS
# -----------------------------
st.subheader("Overview – Matches & DV Calls")

# 1) Boca Juniors results (points over time)
df_boca_matches = df_matches[df_matches["Team"] == "Boca Juniors"].copy()
result_map = {"Win": 3, "Draw": 1, "Loss": 0}
df_boca_matches["Points"] = df_boca_matches["Win_Draw_Loss"].map(result_map)
df_boca_matches = df_boca_matches.sort_values("Date")
df_boca_matches["CumPoints"] = df_boca_matches["Points"].cumsum()

st.markdown("**Graph 1 – Boca Juniors results (cumulative points, 2024)**")
st.line_chart(df_boca_matches.set_index("Date")["CumPoints"])

# 2) River Plate results (points over time)
df_river_matches = df_matches[df_matches["Team"] == "River Plate"].copy()
df_river_matches["Points"] = df_river_matches["Win_Draw_Loss"].map(result_map)
df_river_matches = df_river_matches.sort_values("Date")
df_river_matches["CumPoints"] = df_river_matches["Points"].cumsum()

st.markdown("**Graph 2 – River Plate results (cumulative points, 2024)**")
st.line_chart(df_river_matches.set_index("Date")["CumPoints"])

# 3) DV calls in 2024 (AMBA)
st.markdown("**Graph 3 – Daily domestic violence calls (AMBA, 2024)**")
st.line_chart(dv_daily.set_index("Date")["dv_calls_AMBA"])

# 4) Combined view – DV calls + match days (interactive)
st.markdown("**Graph 4 – DV calls with Boca & River match days (interactive)**")

boca_match_days = df_boca_matches.merge(dv_daily, on="Date", how="left")
river_match_days = df_river_matches.merge(dv_daily, on="Date", how="left")

fig = go.Figure()

# DV calls as bars
fig.add_trace(go.Bar(
    x=dv_daily["Date"],
    y=dv_daily["dv_calls_AMBA"],
    name="DV calls (AMBA)"
))

# Boca match markers
fig.add_trace(go.Scatter(
    x=boca_match_days["Date"],
    y=boca_match_days["dv_calls_AMBA"],
    mode="markers",
    name="Boca match days",
))

# River match markers
fig.add_trace(go.Scatter(
    x=river_match_days["Date"],
    y=river_match_days["dv_calls_AMBA"],
    mode="markers",
    name="River match days",
))

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Number of DV calls (AMBA)",
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True)

