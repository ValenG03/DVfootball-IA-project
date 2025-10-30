import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Fútbol y Violencia Doméstica", layout="wide")
st.title("⚽ Fútbol y Violencia Doméstica en Argentina (2024)")

st.markdown("""
Este análisis usa **Boca_2024_Whole_Year.csv** y **llamados-violencia-familiar-202407-Argentina.csv**.
Se cuenta la **cantidad de llamados por día** (a partir de `llamado_fecha`) y se lo cruza con las fechas de partidos.
""")

# -----------------------------
# 1) CARGA DE ARCHIVOS (según tus columnas reales)
# -----------------------------
MATCHES_FILE = "Boca_2024_Whole_Year.csv"
CALLS_FILE = "llamados-violencia-familiar-202407-Argentina.csv"

@st.cache_data
def load_data(matches_path, calls_path):
    df_matches = pd.read_csv(matches_path)
    df_calls = pd.read_csv(calls_path)

    # Normalizo columnas relevantes
    # Partidos: tiene 'Date', 'Boca_Goals', 'Rival_Goals', 'Result', 'Win_Draw_Loss'
    df_matches['Date'] = pd.to_datetime(df_matches['Date'], errors='coerce').dt.date

    # Llamados: tiene 'llamado_fecha' (fecha del llamado)
    df_calls['llamado_fecha'] = pd.to_datetime(df_calls['llamado_fecha'], errors='coerce').dt.date

    # Agrego cantidad de llamados por día
    calls_daily = (
        df_calls
        .groupby('llamado_fecha', as_index=False)
        .size()
        .rename(columns={'llamado_fecha': 'Date', 'size': 'cantidad_llamados'})
    )

    return df_matches, calls_daily

try:
    df_matches, calls_daily = load_data(MATCHES_FILE, CALLS_FILE)
except Exception as e:
    st.error(f"Error cargando archivos: {e}")
    st.stop()

st.success("Archivos cargados correctamente ✅")

# -----------------------------
# 2) MERGE POR FECHA
# -----------------------------
merged = pd.merge(df_matches, calls_daily, on='Date', how='inner')

# Si no viene el resultado, lo genero con goles (pero en tus datos sí están)
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
# 3) GRÁFICO: Promedio de llamados por resultado
# -----------------------------
st.header("📊 Promedio de llamados por resultado del partido")

calls_by_result = merged.groupby(result_col)['cantidad_llamados'].mean().reset_index()

fig, ax = plt.subplots()
ax.bar(calls_by_result[result_col], calls_by_result['cantidad_llamados'])
ax.set_xlabel("Resultado de Boca")
ax.set_ylabel("Promedio de llamados por día")
ax.set_title("Promedio de llamados según resultado")
st.pyplot(fig)

# -----------------------------
# 4) GRÁFICO: Tendencia temporal en días de partido
# -----------------------------
st.header("📅 Llamados en días de partido (serie temporal)")
merged_sorted = merged.sort_values('Date')

fig2, ax2 = plt.subplots()
ax2.plot(merged_sorted['Date'], merged_sorted['cantidad_llamados'], marker='o', linestyle='-')
ax2.set_xlabel("Fecha del partido")
ax2.set_ylabel("Cantidad de llamados")
ax2.set_title("Tendencia de llamados en días de partidos")
plt.xticks(rotation=45)
st.pyplot(fig2)

# -----------------------------
# 5) CORRELACIÓN: goles vs llamados
# -----------------------------
st.header("📈 Correlación (Goles de Boca vs Llamados)")

if 'Boca_Goals' in merged.columns:
    corr = merged['Boca_Goals'].corr(merged['cantidad_llamados'])
    st.metric("Coeficiente de correlación", f"{corr:.3f}")
else:
    st.info("No se encontró la columna 'Boca_Goals' en el CSV de partidos.")

st.markdown("""
- Valor **negativo** → más goles, **menos** llamados.  
- Valor **positivo** → más goles, **más** llamados.
""")

# -----------------------------
# 6) VISTA PREVIA DE DATOS
# -----------------------------
st.header("🔍 Vista previa de datos combinados")
cols_show = [c for c in ['Date','Rival',result_col,'Boca_Goals','Rival_Goals','cantidad_llamados'] if c in merged.columns]
st.dataframe(merged[cols_show].head(20))
