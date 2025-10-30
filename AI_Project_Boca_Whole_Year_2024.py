import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="DV vs Boca", layout="wide")

@st.cache_data
def load_data(calls_file, matches_file):
    # CSV con posible encoding latino
    df_calls = pd.read_csv(calls_file, encoding="latin1", encoding_errors="ignore")

    # Excel de partidos
    df_matches_xlsx = pd.read_excel(matches_file, header=None, engine="openpyxl")
    # tu formato: primera fila encabezado “raro”, luego 1 columna con texto separado por comas
    df_matches = df_matches_xlsx.iloc[1:].copy()
    df_matches = df_matches[0].astype(str).str.split(",", expand=True)
    df_matches.columns = ['Date','Tournament','Instance','Rival','Boca_Goals',
                          'Rival_Goals','Result','Stadium','Home_or_Away','Win_Draw_Loss']
    return df_calls, df_matches

@st.cache_data
def preprocess_dates(df_calls, df_matches):
    df_calls['llamado_fecha'] = pd.to_datetime(df_calls['llamado_fecha'], errors="coerce").dt.date
    df_matches['Date'] = pd.to_datetime(df_matches['Date'], errors="coerce").dt.date
    df_calls = df_calls.dropna(subset=['llamado_fecha'])
    df_matches = df_matches.dropna(subset=['Date'])
    return df_calls, df_matches

@st.cache_data
def merge_data(df_calls, df_matches):
    return pd.merge(df_calls, df_matches, left_on='llamado_fecha', right_on='Date', how='inner')

@st.cache_data
def analyze_calls(df_calls, df_merged, df_matches):
    s = pd.to_datetime(df_calls['llamado_fecha'])
    df_calls = df_calls.assign(weekday=s.dt.dayofweek)
    df_weekends = df_calls[df_calls['weekday'].isin([5, 6])].copy()

    boca_dates = pd.Series(df_matches['Date'].unique())
    df_weekends_no_boca = df_weekends[~pd.to_datetime(df_weekends['llamado_fecha']).dt.date.isin(boca_dates)].copy()

    num_calls_boca_playing = len(df_merged)
    num_calls_boca_not_playing_weekend = len(df_weekends_no_boca)

    num_boca_playing_weekend_days = df_merged['llamado_fecha'].nunique()
    num_boca_not_playing_weekend_days = df_weekends_no_boca['llamado_fecha'].nunique()

    avg_calls_boca_playing_weekend = (num_calls_boca_playing / num_boca_playing_weekend_days) if num_boca_playing_weekend_days else 0
    avg_calls_boca_not_playing_weekend = (num_calls_boca_not_playing_weekend / num_boca_not_playing_weekend_days) if num_boca_not_playing_weekend_days else 0

    return {
        "num_calls_boca_playing": num_calls_boca_playing,
        "num_boca_playing_weekend_days": num_boca_playing_weekend_days,
        "avg_calls_boca_playing_weekend": avg_calls_boca_playing_weekend,
        "num_calls_boca_not_playing_weekend": num_calls_boca_not_playing_weekend,
        "num_boca_not_playing_weekend_days": num_boca_not_playing_weekend_days,
        "avg_calls_boca_not_playing_weekend": avg_calls_boca_not_playing_weekend
    }

def visualize_data(df_calls, df_matches):
    fig1, ax1 = plt.subplots(figsize=(12, 4))
    calls_per_day = df_calls.groupby('llamado_fecha').size()
    ax1.plot(calls_per_day.index, calls_per_day.values)
    ax1.set_title('Llamados por día')
    ax1.set_xlabel('Fecha'); ax1.set_ylabel('N° llamados'); ax1.grid(True)

    fig2, ax2 = plt.subplots(figsize=(12, 1.8))
    ax2.scatter(df_matches['Date'], [1]*len(df_matches), marker='|', s=120)
    ax2.set_title('Fechas de partidos de Boca')
    ax2.set_xlabel('Fecha'); ax2.set_yticks([]); ax2.grid(True)
    return fig1, fig2

def main():
    st.title("Llamados Línea 137 vs Partidos de Boca — 2024")
    st.write("Subí **ambos** archivos para continuar:")

    calls_file = st.file_uploader("CSV de llamados (Argentina 2024)", type=["csv"])
    matches_file = st.file_uploader("Excel de partidos de Boca (.xlsx)", type=["xlsx"])

    if not calls_file or not matches_file:
        st.info("Esperando ambos archivos…")
        return

    try:
        df_calls, df_matches = load_data(calls_file, matches_file)
        df_calls, df_matches = preprocess_dates(df_calls, df_matches)
        df_merged = merge_data(df_calls, df_matches)
        results = analyze_calls(df_calls, df_merged, df_matches)
        fig1, fig2 = visualize_data(df_calls, df_matches)

        st.subheader("Resultados")
        c1, c2, c3 = st.columns(3)
        c1.metric("Llamados en días con Boca (finde)", results["num_calls_boca_playing"])
        c2.metric("Días con Boca (finde) únicos", results["num_boca_playing_weekend_days"])
        c3.metric("Promedio llamados (con Boca)", f"{results['avg_calls_boca_playing_weekend']:.2f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Llamados en días sin Boca (finde)", results["num_calls_boca_not_playing_weekend"])
        c5.metric("Días sin Boca (finde) únicos", results["num_boca_not_playing_weekend_days"])
        c6.metric("Promedio llamados (sin Boca)", f"{results['avg_calls_boca_not_playing_weekend']:.2f}")

        st.subheader("Vistas rápidas")
        st.pyplot(fig1)
        st.pyplot(fig2)

        st.subheader("Muestras")
        st.write("Llamados")
        st.dataframe(df_calls.head(30), use_container_width=True)
        st.write("Partidos (parseados)")
        st.dataframe(df_matches.head(30), use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar archivos: {e}")

if __name__ == "__main__":
    main()



