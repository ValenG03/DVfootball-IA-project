import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# CONFIGURACIÓN BÁSICA
# -----------------------------
st.set_page_config(page_title="Fútbol y Violencia Doméstica", layout="wide")

st.title("⚽ Fútbol y Violencia Doméstica en Argentina (2024)")
st.markdown("""
Este análisis explora si los resultados de **Boca Juniors** durante 2024 se relacionan con 
los **llamados policiales por violencia doméstica** en los mismos días de partido.
""")

# -----------------------------
# CARGA DE DATOS
# -----------------------------
@st.cache_data
def load_data():
    df_matches = pd.read_excel("Boca_2024_Whole_Year.csv.xlsx")
    df_calls = pd.read_csv("llamados-violencia-familiar-202407-Argentina.csv")
    return df_matches, df_calls

try:
    df_matches, df_calls = load_data()
except Exception as e:
    st.error(f"Error al cargar archivos: {e}")
    st.stop()

st.success("Archivos cargados correctamente ✅")

# -----------------------------
# PREPROCESAMIENTO
# -----------------------------
df_matches['Date'] = pd.to_datetime(df_matches['Date'], errors='coerce')
df_calls['fecha'] = pd.to_datetime(df_calls['fecha'], errors='coerce')

# Filtrar llamados solo de los días con partidos
merged = pd.merge(df_matches, df_calls, left_on='Date', right_on='fecha', how='inner')

# -----------------------------
# ANÁLISIS CUANTITATIVO
# -----------------------------
st.header("📊 Comparación de resultados y llamados")

# Conteo promedio de llamados según resultado
calls_by_result = merged.groupby('Result')['cantidad_llamados'].mean().reset_index()

fig, ax = plt.subplots()
ax.bar(calls_by_result['Result'], calls_by_result['cantidad_llamados'])
ax.set_xlabel("Resultado de Boca")
ax.set_ylabel("Promedio de llamados por día")
ax.set_title("Promedio de llamados según resultado del partido")
st.pyplot(fig)

# -----------------------------
# TENDENCIA TEMPORAL
# -----------------------------
st.header("📅 Evolución temporal de llamados los días de partido")

fig2, ax2 = plt.subplots()
ax2.plot(merged['Date'], merged['cantidad_llamados'], marker='o', linestyle='-')
ax2.set_xlabel("Fecha del partido")
ax2.set_ylabel("Cantidad de llamados")
ax2.set_title("Tendencia de llamados en días de partidos")
st.pyplot(fig2)

# -----------------------------
# CORRELACIÓN
# -----------------------------
st.header("📈 Correlación entre goles y violencia")

corr = merged['Boca_Goals'].corr(merged['cantidad_llamados'])
st.metric("Coeficiente de correlación (Boca_Goals vs Llamados)", f"{corr:.3f}")

st.markdown("""
Un valor **negativo** sugiere que cuando **Boca gana o mete más goles**, los llamados tienden a **disminuir**.
Un valor **positivo** indicaría lo contrario.
""")

# -----------------------------
# DATOS VISIBLES
# -----------------------------
st.header("🔍 Datos combinados (vista previa)")
st.dataframe(merged[['Date', 'Rival', 'Result', 'Boca_Goals', 'Rival_Goals', 'cantidad_llamados']].head(10))


