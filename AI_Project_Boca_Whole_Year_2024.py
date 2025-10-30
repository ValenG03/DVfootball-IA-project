import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="DV vs Boca", layout="wide")

EXPECTED_MATCH_COLS = ['Date','Tournament','Instance','Rival','Boca_Goals',
                       'Rival_Goals','Result','Stadium','Home_or_Away','Win_Draw_Loss']

@st.cache_data
def demo_data():
    # Fechas mínimas para que se vea algo
    calls = pd.DataFrame({
        "llamado_fecha": pd.to_datetime([
            "2024-03-02","2024-03-02","2024-03-03",
            "2024-03-09","2024-03-10","2024-03-10",
            "2024-03-16"
        ]).date
    })

    matches = pd.DataFrame({
        "Date": pd.to_datetime([
            "2024-03-02","2024-03-10","2024-03-16"
        ]).date,
        "Tournament": ["LPF","LPF","LPF"],
        "Instance": ["Liga","Liga","Liga"],
        "Rival": ["River","Racing","San Lorenzo"],
        "Boca_Goals": [1,2,0],
        "Rival_Goals": [1,0,1],
        "Result": ["D","W","L"],
        "Stadium": ["Monu","Bombonera","SL"],
        "Home_or_Away": ["A","H","A"],
        "Win_Draw_Loss": ["Draw","Win","Loss"]
    })
    return calls, matches

def parse_matches_df(df_xlsx):
    """
    Autodetecta si el Excel viene:
    - ya tabulado (>=10 columnas) -> renombra columnas si cuadran
    - como una sola columna con comas -> hace split
    """
    # Quitar filas completamente vacías
    df_xlsx = df_xlsx.dropna(how="all")
    # Si ya viene con varias columnas y cabeceado reconocible
    if df_xlsx.shape[1] >= 10:
        df = df_xlsx.copy()
        # intenta alinear nombres si no coinciden
        if len(df.columns) >= 10:
            df = df.iloc[0:].copy()
            df = df.iloc[:, :10]
            df.columns = EXPECTED_MATCH_COLS
        else:
            # fallback: fuerza nombres para primeras 10 cols
            cols = df.columns.tolist()[:10]
            df = df[cols]
            df.columns = EXPECTED_MATCH_COLS
        return df

    # Caso “una sola col con comas”
    # si la primera fila es encabezado "raro", salteala y usa desde la segunda
    if df_xlsx.shape[1] == 1:
        # decidir si saltear primera fila: si contiene comas y parece header
        series = df_xlsx.iloc[:,0].astype(str)
        # si la primera fila NO parece datos (pocas comas), la saltamos
        start_idx = 1 if series.iloc[0].count(",") < 3 else 0
        df = df_xlsx.iloc[start_idx:].copy()
        df = df.iloc[:,0].astype(str).str.split(",", expand=True)
        if df.shape[1] < 10:
            # si no hay 10 columnas, no se puede parsear así
            raise ValueError("El Excel de partidos no tiene el formato esperado.")
        df = df.iloc[:, :10]
        df.columns = EXPECTED_MATCH_COLS
        return df

    raise ValueError("Formato de Excel no reconocido. Sube un .xlsx válido.")

@st.cache_data
def load_data(calls_file, matches_file):
    # CSV con posible encoding latino
    df_calls = pd.read_csv(calls_file, encoding="latin1", encoding_errors="ignore")

    # Excel de partidos (forzar openpyxl en muchos entornos)
    df_matches_xlsx = pd.read_excel(matches_file, engine="openpyxl", header=None)
    df_matches = parse_matches_df(df_matches_xlsx)

    return df_calls, df_matches

@st.cache_data
def preprocess_dates(df_calls, df_matches):
    # Normalización y limpieza
    if "llamado_fecha" not in df_calls.columns:
        # intenta inferir si viene como 'fecha' o similar
        for cand in ["fecha", "date", "Fecha", "LLAMADO_FECHA"]:
            if cand in df_calls.columns:
                df_calls = df_calls.rename(columns={cand: "llamado_fecha"})
                break
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
    # calcular weekday correctamente
    s = pd.to_datetime(df_calls['llamado_fecha'])
    df_calls = df_calls.assign(weekday=s.dt.weekday)  # <-- el fix está acá
    df_weekends = df_calls[df_calls['weekday'].isin([5, 6])].copy()

    # normalizo tipos de fecha para el isin
    boca_dates = pd.to_datetime(df_matches['Date']).dt.date.unique()
    calls_dates = pd.to_datetime(df_weekends['llamado_fecha']).dt.date
    df_weekends_no_boca = df_weekends[~calls_dates.isin(boca_dates)].copy()

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

    use_demo = st.toggle("Usar datos de ejemplo (sin subir archivos)", value=True)

    calls_file = None
    matches_file = None
    df_calls = None
    df_matches = None

    if not use_demo:
        st.write("Subí **ambos** archivos para continuar:")
        calls_file = st.file_uploader("CSV de llamados (Argentina 2024)", type=["csv"])
        matches_file = st.file_uploader("Excel de partidos de Boca (.xlsx)", type=["xlsx"])

    try:
        if use_demo:
            df_calls, df_matches = demo_data()
        else:
            if not calls_file or not matches_file:
                st.info("Esperando ambos archivos… o activa 'Usar datos de ejemplo'.")
                return
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
