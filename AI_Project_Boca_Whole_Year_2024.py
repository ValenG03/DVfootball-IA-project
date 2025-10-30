import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import date

# =============================
# Configuración
# =============================
st.set_page_config(page_title="DV vs Boca — 2024", layout="wide")

EXPECTED_MATCH_COLS = [
    "Date","Tournament","Instance","Rival","Boca_Goals",
    "Rival_Goals","Result","Stadium","Home_or_Away","Win_Draw_Loss"
]

LOCAL_CALLS_PATH = "/mnt/data/llamados-violencia-familiar-202407-Argentina.csv"
LOCAL_MATCHES_PATH = "/mnt/data/Boca_2024_Whole_Year.csv.xlsx"

# =============================
# Utilitarios
# =============================
def _to_date(series):
    return pd.to_datetime(series, errors="coerce").dt.date

def _num(x):
    return pd.to_numeric(x, errors="coerce")

def _title(s):
    return s.strip().title() if isinstance(s, str) else s

def _upper(s):
    return s.strip().upper() if isinstance(s, str) else s

def _exists_local_files():
    try:
        with open(LOCAL_CALLS_PATH, "rb"): ...
        with open(LOCAL_MATCHES_PATH, "rb"): ...
        return True
    except Exception:
        return False

# =============================
# Datos de ejemplo para vista previa rápida
# =============================
@st.cache_data
def demo_data():
    calls = pd.DataFrame({
        "llamado_fecha": _to_date([
            "2024-03-02","2024-03-02","2024-03-03",
            "2024-03-09","2024-03-10","2024-03-10","2024-03-16"
        ])
    })
    matches = pd.DataFrame({
        "Date": _to_date(["2024-03-02","2024-03-10","2024-03-16"]),
        "Tournament": ["LPF","LPF","LPF"],
        "Instance": ["Liga","Liga","Liga"],
        "Rival": ["River","Racing","San Lorenzo"],
        "Boca_Goals": [1,2,0],
        "Rival_Goals": [1,0,1],
        "Result": ["D","W","L"],
        "Stadium": ["Monumental","Bombonera","Pedro Bidegain"],
        "Home_or_Away": ["A","H","A"],
        "Win_Draw_Loss": ["Draw","Win","Loss"],
    })
    return calls, matches

# =============================
# Parsing flexible de Excel de Partidos
# =============================
@st.cache_data
def parse_matches_df(df_xlsx: pd.DataFrame) -> pd.DataFrame:
    """Acepta planilla tabulada (>=10 cols) o 1 sola col separada por coma."""
    df_xlsx = df_xlsx.dropna(how="all")

    # Caso planilla con múltiples columnas
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
            raise ValueError("El Excel de partidos no tiene el formato esperado (menos de 10 campos).")
        df = df.iloc[:, :10]
        df.columns = EXPECTED_MATCH_COLS
        return df

    raise ValueError("Formato de Excel no reconocido. Sube un .xlsx válido.")

# =============================
# Carga de archivos
# =============================
@st.cache_data
def load_uploaded(calls_file, matches_file):
    df_calls = pd.read_csv(calls_file, encoding="latin1", encoding_errors="ignore")
    try:
        raw = pd.read_excel(matches_file, engine="openpyxl")
    except Exception:
        raw = pd.read_excel(matches_file, engine="openpyxl", header=None)

    if raw.shape[1] >= 10 and any(col in set(raw.columns.astype(str)) for col in ["Date","Rival","Boca_Goals"]):
        raw = raw.iloc[:, :10].copy()
        raw.columns = EXPECTED_MATCH_COLS
        df_matches = raw
    else:
        df_matches = parse_matches_df(raw)

    return df_calls, df_matches

@st.cache_data
def load_local_defaults():
    df_calls = pd.read_csv(LOCAL_CALLS_PATH, encoding="latin1", encoding_errors="ignore")
    try:
        raw = pd.read_excel(LOCAL_MATCHES_PATH, engine="openpyxl")
    except Exception:
        raw = pd.read_excel(LOCAL_MATCHES_PATH, engine="openpyxl", header=None)

    if raw.shape[1] >= 10 and any(col in set(raw.columns.astype(str)) for col in ["Date","Rival","Boca_Goals"]):
        raw = raw.iloc[:, :10].copy()
        raw.columns = EXPECTED_MATCH_COLS
        df_matches = raw
    else:
        df_matches = parse_matches_df(raw)

    return df_calls, df_matches

# =============================
# Limpieza y normalización
# =============================
@st.cache_data
def preprocess(df_calls: pd.DataFrame, df_matches: pd.DataFrame):
    # --- llamados ---
    if "llamado_fecha" not in df_calls.columns:
        for cand in ["fecha","date","Fecha","LLAMADO_FECHA"]:
            if cand in df_calls.columns:
                df_calls = df_calls.rename(columns={cand: "llamado_fecha"})
                break
    if "llamado_fecha" not in df_calls.columns:
        raise ValueError("No se encontró la columna de fecha en el CSV de llamados (p. ej. 'llamado_fecha').")

    df_calls["llamado_fecha"] = _to_date(df_calls["llamado_fecha"])
    df_calls = df_calls.dropna(subset=["llamado_fecha"]).copy()

    # --- partidos ---
    # Asegurar columnas mínimas
    missing = [c for c in EXPECTED_MATCH_COLS if c not in df_matches.columns]
    if missing:
        raise ValueError(f"Al Excel de partidos le faltan columnas: {missing}")

    df_matches = df_matches.copy()
    df_matches["Date"] = _to_date(df_matches["Date"])
    df_matches = df_matches.dropna(subset=["Date"])

    # Tipos y normalización
    for c in ["Boca_Goals","Rival_Goals"]:
        df_matches[c] = _num(df_matches[c])

    # Normalizar textos clave
    if "Win_Draw_Loss" in df_matches.columns:
        df_matches["Win_Draw_Loss"] = df_matches["Win_Draw_Loss"].map(lambda s: s.strip().title() if isinstance(s, str) else s)

    if "Result" in df_matches.columns:
        # Asegurar en {W,D,L} si viene mezclado
        mapping = {
            "WIN":"W","W":"W","GANÓ":"W","GANO":"W","GANA":"W",
            "DRAW":"D","D":"D","EMPATE":"D",
            "LOSS":"L","L":"L","PERDIÓ":"L","PERDIO":"L","PIERDE":"L"
        }
        df_matches["Result"] = df_matches["Result"].map(lambda s: mapping.get(_upper(s), s) if isinstance(s, str) else s)

    # Orden sugerido (opcional)
    df_matches = df_matches.sort_values("Date").reset_index(drop=True)

    return df_calls, df_matches

# =============================
# Métricas y análisis
# =============================
@st.cache_data
def merge_same_day(df_calls, df_matches):
    return pd.merge(df_calls, df_matches, left_on="llamado_fecha", right_on="Date", how="inner")

@st.cache_data
def weekend_mask(dates):
    # Sábado(5) o Domingo(6)
    w = pd.to_datetime(dates, errors="coerce").dt.weekday
    return w.isin([5, 6])

@st.cache_data
def analyze_basics(df_calls, df_matches):
    # Serie de llamados por día (conteo de filas)
    calls_per_day = df_calls.groupby("llamado_fecha").size().rename("calls")
    calls_per_day = calls_per_day.sort_index()

    # Partidos por día
    matches_by_day = df_matches.groupby("Date").size().rename("matches")

    # Alinear índices por unión (todos los días con llamados)
    full_idx = calls_per_day.index
    plays_mask = pd.Series(False, index=full_idx)
    plays_mask.loc[full_idx.intersection(matches_by_day.index)] = True

    # Fines de semana
    wknd_mask = weekend_mask(full_idx)

    # Promedios (finde) con y sin Boca
    calls_on_wknd = calls_per_day[wknd_mask]
    plays_on_wknd = plays_mask[wknd_mask]
    avg_calls_boca = calls_on_wknd[plays_on_wknd].mean() if (plays_on_wknd.sum() > 0) else np.nan
    avg_calls_no_boca = calls_on_wknd[~plays_on_wknd].mean() if ((~plays_on_wknd).sum() > 0) else np.nan

    # Conteos
    num_calls_boca_playing = int(calls_on_wknd[plays_on_wknd].sum()) if plays_on_wknd.any() else 0
    num_calls_no_boca = int(calls_on_wknd[~plays_on_wknd].sum()) if (~plays_on_wknd).any() else 0
    days_boca = int(plays_on_wknd.sum())
    days_no_boca = int((~plays_on_wknd).sum())

    # Desglose por resultado (solo en días de partido)
    merged = merge_same_day(df_calls, df_matches)
    by_result = merged.groupby("Result").size().to_dict()
    by_result = {k: int(v) for k, v in by_result.items()}

    return {
        "calls_per_day": calls_per_day,
        "plays_mask": plays_mask,
        "wknd_mask": wknd_mask,
        "avg_calls_boca_wknd": float(avg_calls_boca) if pd.notna(avg_calls_boca) else 0.0,
        "avg_calls_no_boca_wknd": float(avg_calls_no_boca) if pd.notna(avg_calls_no_boca) else 0.0,
        "num_calls_boca_playing_wknd": num_calls_boca_playing,
        "num_calls_no_boca_wknd": num_calls_no_boca,
        "days_boca_wknd": days_boca,
        "days_no_boca_wknd": days_no_boca,
        "by_result_calls": by_result,
        "merged_same_day": merged
    }

@st.cache_data
def welch_t_test(sample_a: pd.Series, sample_b: pd.Series):
    """t-test (Welch) simple sin SciPy; devuelve t y gl aproximados."""
    a = pd.to_numeric(sample_a, errors="coerce").dropna().astype(float)
    b = pd.to_numeric(sample_b, errors="coerce").dropna().astype(float)
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    na, nb = len(a), len(b)
    t = (ma - mb) / np.sqrt(va/na + vb/nb)
    # gl de Welch–Satterthwaite
    df = (va/na + vb/nb)**2 / ((va**2)/((na**2)*(na-1)) + (vb**2)/((nb**2)*(nb-1)))
    return float(t), float(df)

# =============================
# Figuras
# =============================
def fig_calls_timeseries(calls_per_day, matches_dates):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(calls_per_day.index, calls_per_day.values)
    ax.set_title("Llamados por día")
    ax.set_xlabel("Fecha"); ax.set_ylabel("N° de llamados")
    ax.grid(True, alpha=0.3)

    # marcar días con partido
    y_min, y_max = ax.get_ylim()
    for d in matches_dates:
        ax.vlines(d, y_min, y_max, linestyles="dashed", alpha=0.25)
    ax.set_ylim(y_min, y_max)
    return fig

def fig_matches_stem(df_matches):
    fig, ax = plt.subplots(figsize=(12, 1.8))
    ax.scatter(df_matches["Date"], [1]*len(df_matches), marker="|", s=140)
    ax.set_title("Fechas de partidos de Boca")
    ax.set_xlabel("Fecha"); ax.set_yticks([]); ax.grid(True, axis="x", alpha=0.3)
    return fig

def fig_bars_avgs(avg_a, avg_b, label_a, label_b):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar([label_a, label_b], [avg_a, avg_b])
    ax.set_ylabel("Promedio de llamados")
    ax.set_title("Comparación de promedios (fines de semana)")
    for i, v in enumerate([avg_a, avg_b]):
        ax.text(i, v, f"{v:.2f}", ha="center", va="bottom")
    ax.grid(True, axis="y", alpha=0.3)
    return fig

# =============================
# Export
# =============================
@st.cache_data
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

# =============================
# App
# =============================
def main():
    st.title("Llamados Línea 137 vs Partidos de Boca — 2024")
    st.caption("Comparación simple y clara entre llamados diarios y días de partido. Los cálculos usan coincidencia de **fecha exacta**.")

    with st.sidebar:
        st.header("Fuentes de datos")
        mode = st.radio(
            "Elegí el modo",
            ["Demo (rápido)","Archivos subidos","Archivos locales (/mnt/data)"],
            index=0
        )

        calls_file = None
        matches_file = None

        if mode == "Archivos subidos":
            st.markdown("Subí **ambos** archivos.")
            calls_file = st.file_uploader("CSV de llamados (Argentina 2024)", type=["csv"])
            matches_file = st.file_uploader("Excel de partidos (.xlsx)", type=["xlsx"])
        elif mode == "Archivos locales (/mnt/data)":
            if not _exists_local_files():
                st.warning("No encontré los archivos locales esperados. Cambiá a *Demo* o *Archivos subidos*.")
            st.write("Usando rutas locales predefinidas.")

        st.divider()
        do_ttest = st.toggle("Calcular t-test (Welch) para promedios de findes", value=False)
        st.caption("Compara promedios de llamados en fines de semana **con** vs **sin** partido (exploratorio).")

    # Carga
    try:
        if mode == "Demo (rápido)":
            df_calls, df_matches = demo_data()
        elif mode == "Archivos subidos":
            if not calls_file or not matches_file:
                st.info("Subí ambos archivos para continuar o cambiá a *Demo*.")
                st.stop()
            df_calls, df_matches = load_uploaded(calls_file, matches_file)
        else:
            df_calls, df_matches = load_local_defaults()

        # Limpieza / normalización
        df_calls, df_matches = preprocess(df_calls, df_matches)

        # Análisis básico
        basic = analyze_basics(df_calls, df_matches)

        # ====== Métricas principales ======
        st.subheader("Resultados (fines de semana)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Llamados en días con Boca", basic["num_calls_boca_playing_wknd"])
        c2.metric("Días con Boca (únicos)", basic["days_boca_wknd"])
        c3.metric("Promedio con Boca", f"{basic['avg_calls_boca_wknd']:.2f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Llamados en días sin Boca", basic["num_calls_no_boca_wknd"])
        c5.metric("Días sin Boca (únicos)", basic["days_no_boca_wknd"])
        c6.metric("Promedio sin Boca", f"{basic['avg_calls_no_boca_wknd']:.2f}")

        # Comparación visual de promedios
        st.pyplot(fig_bars_avgs(
            basic["avg_calls_boca_wknd"],
            basic["avg_calls_no_boca_wknd"],
            "Con partido",
            "Sin partido"
        ))

        # t-test (opcional, exploratorio)
        if do_ttest:
            # construir muestras diarias (finde)
            calls = basic["calls_per_day"]
            wknd_mask = basic["wknd_mask"]
            plays = basic["plays_mask"]

            sample_with = calls[wknd_mask & plays]
            sample_without = calls[wknd_mask & (~plays)]

            t, df_approx = welch_t_test(sample_with, sample_without)
            st.info(
                "t-test de Welch (exploratorio): "
                f"t ≈ {t:.3f} | gl ≈ {df_approx:.1f}  \n"
                "Nota: sin p-valor (no usamos librerías externas). Interpretar con cautela."
            )

        # ====== Gráficos de contexto ======
        st.subheader("Evolución y calendario")
        st.pyplot(fig_calls_timeseries(basic["calls_per_day"], df_matches["Date"]))
        st.pyplot(fig_matches_stem(df_matches))

        # ====== Desglose adicional ======
        st.subheader("Cruces y ejemplos")
        colA, colB = st.columns(2)
        with colA:
            st.write("**Llamados (primeras 30 filas)**")
            st.dataframe(df_calls.head(30), use_container_width=True)
        with colB:
            st.write("**Partidos parseados (primeras 30 filas)**")
            st.dataframe(df_matches.head(30), use_container_width=True)

        merged = basic["merged_same_day"]
        st.write("**Cruce: llamados en días con partido (todas las filas que coinciden en fecha)**")
        if merged.empty:
            st.warning("No hay coincidencias exactas de fecha entre llamados y partidos.")
        else:
            st.dataframe(merged, use_container_width=True, height=300)
            st.download_button(
                "Descargar CSV del cruce",
                data=to_csv_bytes(merged),
                file_name="llamados_boca_merge.csv",
                mime="text/csv"
            )

        # Resumen por resultado
        if basic["by_result_calls"]:
            st.write("**Llamados en días con partido, agrupados por resultado (W/D/L):**")
            res_tbl = pd.DataFrame(
                [{"Resultado": k, "Llamados (filas)": v} for k, v in sorted(basic["by_result_calls"].items())]
            )
            st.dataframe(res_tbl, use_container_width=True)

        # Nota metodológica
        with st.expander("Notas metodológicas"):
            st.markdown(
                """
- El cruce se hace por **fecha exacta** (formato fecha, sin hora).  
- Los **promedios** se calculan solo con **sábados y domingos**.  
- Si un día tiene múltiples filas de llamados, cada fila cuenta como 1 llamado (conteo de registros).  
- Normalizamos *Result* a {W, D, L} y *Win_Draw_Loss* a {Win, Draw, Loss} si vienen en otros idiomas/formatos.
- Los resultados son **descriptivos**; cualquier causalidad requiere controles adicionales y más variables.
                """
            )

    except Exception as e:
        st.error(f"Error al procesar archivos: {e}")

if __name__ == "__main__":
    main()

