import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# -----------------------------
# Configuración básica
# -----------------------------
st.set_page_config(page_title="DV vs Boca", layout="wide")

EXPECTED_MATCH_COLS = [
    'Date','Tournament','Instance','Rival','Boca_Goals',
    'Rival_Goals','Result','Stadium','Home_or_Away','Win_Draw_Loss'
]

# -----------------------------
# Datos de demo (rápido para previsualizar)
# -----------------------------
@st.cache_data
def demo_data():
    calls = pd.DataFrame({
        "llamado_fecha": pd.to_datetime([
            "2024-03-02","2024-03-02","2024-03-03",
            "2024-03-09","2024-03-10","2024-03-10",
            "2024-03-16"
        ], errors="coerce").dt.date
    })

    matches = pd.DataFrame({
        "Date": pd.to_datetime([
            "2024-03-02","2024-03-10","2024-03-16"
        ], errors="coerce").dt.date,
        "Tournament": ["LPF","LPF","LPF"],
        "Instance": ["Liga","Liga","Liga"],
        "Rival": ["River","Racing","San Lorenzo"],
        "Boca_Goals": [1,2,0],
        "Rival_Goals": [1,0,1],
        "Result": ["D","W","L"],
        "Stadium": ["Monumental","Bombonera","Pedro Bidegain"],
        "Home_or_Away": ["A","H","A"],
        "Win_Draw_Loss": ["Draw","Win","Loss"]
    })
    return calls, matches

# -----------------------------
# Parsing flexible del Excel de Partidos
# -----------------------------
@st.cache_data
def parse_matches_df(df_xlsx: pd.DataFrame) -> pd.DataFrame:
    """
    Autodetecta si el Excel viene:
    - ya tabulado (>=10 columnas) -> renombra columnas
    - como una sola columna con comas -> hace split
    """
    df_xlsx = df_xlsx.dropna(how="all")

    # Caso con múltiples columnas: usamos las primeras 10 y renombramos
    if df_xlsx.shape[1] >= 10:
        df = df_xlsx.iloc[:, :10].copy()
        df.columns = EXPECTED_MATCH_COLS
        return df

    # Caso 1 columna: separar por coma
    if df_xlsx.shape[1] == 1:
        series = df_xlsx.iloc[:, 0].astype(str)
        start_idx = 1 if series.iloc[0].count(",") < 3 else 0
        df = df_xlsx.iloc[start_idx:, 0].astype(str).str.split(",", expand=True)
        if df.shape[1] < 10:
            raise ValueError("El Excel de partidos no tiene el formato esperado.")
        df = df.iloc[:, :10]
        df.columns = EXPECTED_MATCH_COLS
        return df

    raise ValueError("Formato de Excel no reconocido. Sube un .xlsx válido.")

# -----------------------------
# Carga de archivos
# -----------------------------
@st.cache_data
def load_data(calls_file, matches_file):
    # CSV de llamados con tolerancia de encoding
    df_calls = pd.read_csv(calls_file, encoding="latin1", encoding_errors="ignore")

    # Intento 1: Excel con encabezado normal
    try:
        raw = pd.read_excel(matches_file, engine="openpyxl")
    except Exception:
        raw = pd.read_excel(matches_file, engine="openpyxl", header=None)

    # Si parece tener encabezado correcto y >=10 columnas, normalizamos nombres
    if raw.shape[1] >= 10 and any(col in set(raw.columns.astype(str)) for col in ["Date","Rival","Boca_Goals"]):
        raw = raw.iloc[:, :10].copy()
        raw.columns = EXPECTED_MATCH_COLS
        df_matches = raw
    else:
        # Usamos parser robusto (también cubre header=None)
        df_matches = parse_matches_df(raw)

    return df_calls, df_matches

# -----------------------------
# Preprocesamiento de fechas
# -----------------------------
@st.cache_data
def preprocess_dates(df_calls: pd.DataFrame, df_matches: pd.DataFrame):
    # Detectar columna de fecha en llamados
    if "llamado_fecha" not in df_calls.columns:
        for cand in ["fecha", "date", "Fecha", "LLAMADO_FECHA"]:
            if cand in df_calls.columns:
                df_calls = df_calls.rename(columns={cand: "llamado_fecha"})
                break
    df_calls["llamado_fecha"] = pd.to_datetime(df_calls["llamado_fecha"], errors="coerce").dt.date

    # Fechas en partidos
    df_matches["Date"] = pd.to_datetime(df_matches["Date"], errors="coerce").dt.date

    # Limpieza de nulos
    df_calls = df_calls.dropna(subset=["llamado_fecha"]).copy()
    df_matches = df_matches.dropna(subset=["Date"]).copy()

    # Tipos numéricos básicos
    for c in ["Boca_Goals", "Rival_Goals"]:
        if c in df_matches.columns:
            df_matches[c] = pd.to_numeric(df_matches[c], errors="coerce")

    return df_calls, df_matches

# -----------------------------
# Merge + métricas
# -----------------------------
@st.cache_data
def merge_data(df_calls: pd.DataFrame, df_matches: pd.DataFrame) -> pd.DataFrame:
    return pd.merge(df_calls, df_matches, left_on='llamado_fecha', right_on='Date', how='inner')

@st.cache_data
def analyze_calls(df_calls: pd.DataFrame, df_merged: pd.DataFrame, df_matches: pd.DataFrame):
    # Convertir fechas y calcular día de la semana
    df_calls['weekday'] = pd.to_datetime(df_calls['llamado_fecha'], errors='coerce').dt.weekday
    df_weekends = df_calls[df_calls['weekday'].isin([5, 6])].copy()

    boca_dates = pd.to_datetime(df_matches['Date'], errors="coerce").dt.date.unique()
    calls_dates = pd.to_datetime(df_weekends['llamado_fecha'], errors="coerce").dt.date
    df_weekends_no_boca = df_weekends[~calls_dates.isin(boca_dates)].copy()

    num_calls_boca_playing = len(df_merged)
    num_calls_boca_not_playing_weekend = len(df_weekends_no_boca)

    num_boca_playing_weekend_days = df_merged['llamado_fecha'].nunique()
    num_boca_not_playing_weekend_days = df_weekends_no_boca['llamado_fecha'].nunique()

    avg_calls_boca_playing_weekend = (num_calls_boca_playing / num_boca_playing_weekend_days) if num_boca_playing_weekend_days else 0
    avg_calls_boca_not_playing_weekend = (num_calls_boca_not_playing_weekend / num_boca_not_playing_weekend_days) if num_boca_not_playing_weekend_days else 0

    return {
        "num_calls_boca_playing": int(num_calls_boca_playing),
        "num_boca_playing_weekend_days": int(num_boca_playing_weekend_days),
        "avg_calls_boca_playing_weekend": float(avg_calls_boca_playing_weekend),
        "num_calls_boca_not_playing_weekend": int(num_calls_boca_not_playing_weekend),
        "num_boca_not_playing_weekend_days": int(num_boca_not_playing_weekend_days),
        "avg_calls_boca_not_playing_weekend": float(avg_calls_boca_not_playing_weekend)
    }


# -----------------------------
# Visualizaciones
# -----------------------------
@st.cache_data
def build_figures(df_calls: pd.DataFrame, df_matches: pd.DataFrame):
    fig1, ax1 = plt.subplots(figsize=(12, 4))
    calls_per_day = df_calls.groupby('llamado_fecha').size()
    ax1.plot(calls_per_day.index, calls_per_day.values)
    ax1.set_title('Llamados por día')
    ax1.set_xlabel('Fecha'); ax1.set_ylabel('N° llamados'); ax1.grid(True)

    fig2, ax2 = plt.subplots(figsize=(12, 1.8))
    ax2.scatter(df_matches['Date'], [1]*len(df_matches), marker='|', s=140)
    ax2.set_title('Fechas de partidos de Boca')
    ax2.set_xlabel('Fecha'); ax2.set_yticks([]); ax2.grid(True)

    return fig1, fig2

# -----------------------------
# Export utilitario
# -----------------------------
@st.cache_data
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')

# -----------------------------
# App principal
# -----------------------------
def main():
    st.title("Llamados Línea 137 vs Partidos de Boca — 2024")

    with st.sidebar:
        st.header("Datos")
        use_demo = st.toggle("Usar datos de ejemplo", value=True)
        st.markdown("Subí **ambos** archivos cuando desactives el modo demo.")
        calls_file = st.file_uploader("CSV de llamados (Argentina 2024)", type=["csv"], disabled=use_demo)
        matches_file = st.file_uploader("Excel de partidos (.xlsx)", type=["xlsx"], disabled=use_demo)

    try:
        if use_demo:
            df_calls, df_matches = demo_data()
        else:
            if not calls_file or not matches_file:
                st.info("Esperando ambos archivos… o activa 'Usar datos de ejemplo'.")
                st.stop()
            df_calls, df_matches = load_data(calls_file, matches_file)

        df_calls, df_matches = preprocess_dates(df_calls, df_matches)
        df_merged = merge_data(df_calls, df_matches)
        results = analyze_calls(df_calls, df_merged, df_matches)
        fig1, fig2 = build_figures(df_calls, df_matches)

        # Métricas
        st.subheader("Resultados")
        c1, c2, c3 = st.columns(3)
        c1.metric("Llamados en días con Boca (finde)", results["num_calls_boca_playing"]) 
        c2.metric("Días con Boca (finde) únicos", results["num_boca_playing_weekend_days"]) 
        c3.metric("Promedio llamados (con Boca)", f"{results['avg_calls_boca_playing_weekend']:.2f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Llamados en días sin Boca (finde)", results["num_calls_boca_not_playing_weekend"]) 
        c5.metric("Días sin Boca (finde) únicos", results["num_boca_not_playing_weekend_days"]) 
        c6.metric("Promedio llamados (sin Boca)", f"{results['avg_calls_boca_not_playing_weekend']:.2f}")

        # Gráficos
        st.subheader("Vistas rápidas")
        st.pyplot(fig1)
        st.pyplot(fig2)

        # Tablas
        st.subheader("Muestras")
        st.write("**Llamados**")
        st.dataframe(df_calls.head(30), use_container_width=True)
        st.write("**Partidos (parseados)**")
        st.dataframe(df_matches.head(30), use_container_width=True)

        # Descarga de merge
        if not df_merged.empty:
            st.subheader("Descargar cruce de datos")
            st.download_button(
                label="Descargar CSV de llamados en días con partido",
                data=to_csv_bytes(df_merged),
                file_name="llamados_boca_merge.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Error al procesar archivos: {e}")


if __name__ == "__main__":
    main()

