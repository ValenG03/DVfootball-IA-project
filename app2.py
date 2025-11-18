import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Football and DV – AMBA 2024",
    layout="wide"
)

col1, col2, col3 = st.columns([1,3,1])

with col1:
    st.image("Boca_escudo.png", width=120)

with col2:
    st.markdown(
        """
        <div style="display:flex; justify-content:center; align-items:center; width:100%;">
            <h1 style="font-size:42px; text-align:center; margin:0; padding:0;">
                ⚽ Football & Domestic Violence in Argentina ⚽
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown("<div style='width:120px; height:1px;'></div>", unsafe_allow_html=True)  # invisible spacer
    st.image("River_logo.png", width=90)


# -----------------------------
# RESEARCH QUESTION + TEAM
# (Centered + flags will render)
# -----------------------------
st.markdown(
    """
    <h3 style='text-align:center;'>
    📌 <b>Research Question:</b><br>
    Does football performance influence domestic violence rates in AMBA?<br><br>

    👥 <b>MAB Team</b><br>
    Mexico,
    Argentina,
    Belgium<br><br>
    <b>Members</b><br>
    Larissa Bolaños, 
    Valentin Gerold,
    Rik Commermann
    </h3>
    """,
    unsafe_allow_html=True
)

st.markdown("""
Web page that combines:

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
    
    # Creamos una versión genérica con columna "Calls"
    df_calls_daily = dv_daily.rename(columns={"dv_calls_AMBA": "Calls"}).copy()


    # Merge DV with matches on date
    df_matches_dv = pd.merge(
        df_matches,
        dv_daily,
        on="Date",
        how="left",
    )
    
    return df_matches, dv_daily, df_matches_dv, df_calls_daily


# Load data once (cached)
df_matches, dv_daily, df_matches_dv, df_calls_daily = load_raw_data()

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
    st.subheader("Matches with DV calls (AMBA) on the same date")

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

# -----------------------------
# DV CALLS graph
# -----------------------------
st.markdown("### Graph 3 – Daily DV Calls (AMBA)")

chart_dv = (
    alt.Chart(dv_daily)
    .mark_bar()
    .encode(
        x="Date:T",
        y="dv_calls_AMBA:Q",
        tooltip=["Date", "dv_calls_AMBA"]
    )
    .properties(height=300)
)

st.altair_chart(chart_dv, use_container_width=True)


# 🔹 COMBINED – DV calls + Boca/River match days (Altair)

st.markdown("### Graph 4 – Combined DV Calls + Boca & River Matches")

# Primero, matcheamos los días de partido con las llamadas de DV
boca_match_days = df_boca_matches.merge(dv_daily, on="Date", how="left")
river_match_days = df_river_matches.merge(dv_daily, on="Date", how="left")

# Barras de llamadas DV (AMBA)
dv_chart = (
    alt.Chart(dv_daily)
    .mark_bar()
    .encode(
        x="Date:T",
        y="dv_calls_AMBA:Q",
        tooltip=["Date:T", "dv_calls_AMBA:Q"]
    )
)

# Puntos para días de partido de Boca
boca_points = (
    alt.Chart(boca_match_days)
    .mark_point(size=80, filled=True)
    .encode(
        x="Date:T",
        y="dv_calls_AMBA:Q",
        color=alt.value("blue"),
        tooltip=["Date:T", "Opponent:N", "Win_Draw_Loss:N", "dv_calls_AMBA:Q"]
    )
)

# Puntos para días de partido de River
river_points = (
    alt.Chart(river_match_days)
    .mark_point(size=80, filled=True)
    .encode(
        x="Date:T",
        y="dv_calls_AMBA:Q",
        color=alt.value("red"),
        tooltip=["Date:T", "Opponent:N", "Win_Draw_Loss:N", "dv_calls_AMBA:Q"]
    )
)

combined_chart = (dv_chart + boca_points + river_points).properties(height=350)

st.altair_chart(combined_chart, use_container_width=True)



# ------------------------------------------------------
# 5) GRAPH – Do DV Calls Rise or Fall When Boca/River Win?
# ------------------------------------------------------

st.markdown("## Violence Calls vs Match Results")

# 1) Mapear resultados a -1 / 0 / 1 (incluyendo W/D/L)
result_num_map = {
    "Win": 1, "W": 1,
    "Draw": 0, "D": 0,
    "Loss": -1, "L": -1
}

# Normalizar la columna de resultados a string limpio
df_matches["Win_Draw_Loss"] = df_matches["Win_Draw_Loss"].astype(str).str.strip()
df_matches["ResultNum"] = df_matches["Win_Draw_Loss"].map(result_num_map)

# 2) Merge: llamadas por día + info de partidos (Boca y River)
df_merged = df_calls_daily.merge(
    df_matches[["Date", "Team", "ResultNum"]],
    on="Date",
    how="left"
)

# 3) Promedio móvil para suavizar ruido
df_merged["Rolling_Calls"] = (
    df_merged["Calls"]
    .rolling(window=3, center=True)
    .mean()
)

# ------------------------------------------------------
# LINE GRAPH (Altair)
# ------------------------------------------------------

# Línea de llamadas diarias
line_calls = alt.Chart(df_merged).mark_line().encode(
    x="Date:T",
    y="Calls:Q",
    tooltip=["Date:T", "Calls:Q"]
)

# Línea de promedio móvil (discontinua)
line_smooth = alt.Chart(df_merged).mark_line(strokeDash=[5, 5]).encode(
    x="Date:T",
    y="Rolling_Calls:Q",
    tooltip=["Date:T", "Rolling_Calls:Q"]
)

# Puntos en los días con partido (colores según resultado)
points_matches = (
    alt.Chart(df_merged[df_merged["ResultNum"].notna()])
    .mark_point(size=120)
    .encode(
        x="Date:T",
        y="Calls:Q",
        color=alt.Color(
            "ResultNum:N",
            scale=alt.Scale(
                domain=[1, 0, -1],
                range=["green", "gray", "red"]
            ),
            legend=alt.Legend(
                title="Match Result",
                labelExpr=(
                    "datum.value == 1 ? 'Win' : "
                    "datum.value == 0 ? 'Draw' : 'Loss'"
                )
            )
        ),
        shape="Team:N",
        tooltip=["Date:T", "Team:N", "ResultNum:Q", "Calls:Q"]
    )
)

graph = (line_calls + line_smooth + points_matches).properties(
    width=900,
    height=400,
    title="Do Violence Calls Increase or Decrease When Boca/River Win or Lose?"
)

st.altair_chart(graph, use_container_width=True)


# ------------------------------------------------------
# 6) CONCLUSIONS – Statistical Analysis (Significance)
# ------------------------------------------------------

st.markdown("---")

st.markdown("### Conclusions")
st.markdown("# Significance Level")

st.markdown("""
- **p-value = α = 0.05**  
- **Boca losses vs. non-match days**: p ≈ 0.037 **< 0.05** → losing days show **fewer calls** than non-match days.  
- **River wins vs. non-match days**: p ≈ 0.105 **> 0.05** → slight trend to fewer calls, but **not statistically significant**.  
- Overall, there is **no robust evidence** that Boca or River results systematically increase or reduce daily DV calls in AMBA.
""")


# ------------------------------------------------------
# 7) Advantages and Disadvantages of our Investigation
# ------------------------------------------------------

st.markdown("---")
st.markdown("### Discussion")

st.markdown("## Advantages and Unique Aspects")

st.markdown("""
- Controlled data selection ensures **clean and reliable inputs**.  
- Use of **OVD**, the official source for domestic-violence statistics.  
- Inclusion of **qualitative context** alongside statistical tests.  
- Clear **interpretations and visualizations** to support findings.  
- **Original study**: no prior research links Boca/River results with DV in AMBA.  
- Potential **usefulness for future prediction models** and prevention strategies.  
""")

st.markdown("## Drawbacks")

st.markdown("""
- **No official DV numbers for the neighborhood of La Boca**.  
- Geographic area for analysis is **broad and imprecise**.  
- DV calls may be reported **days after the event**, especially after weekends.  
- Assumes **40% of AMBA population are Boca fans**, which may not be exact.  
- DV calls do **not necessarily imply a direct causal link** with football results.  
""")



st.markdown("## Closing Image")

st.markdown(
    "<div style='text-align: center;'>",
    unsafe_allow_html=True
)

st.image(
    "Gemini_Generated_Image_gtp4x6gtp4x6gtp4.png",
    caption="One of the main objectives of this project",
    width=400
)

st.markdown(
    "</div>",
    unsafe_allow_html=True
)
