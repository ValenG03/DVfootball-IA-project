import streamlit as st
import pandas as pd
import os

data/
  ├─ Boca_2024_Whole_Year.csv
  └─ Llamados Violencia Familiar hasta Agosto 2024 Argentina.csv


# ---------- CARGA DE DATOS ----------
@st.cache_data
def load_data(calls_path, matches_path):
    try:
        df_calls = pd.read_csv(calls_path, encoding='latin1')
        df_matches = pd.read_csv(matches_path, encoding='latin1')
        return df_calls, df_matches
    except FileNotFoundError:
        st.error("❌ No se encontraron los archivos CSV en las rutas indicadas.")
        return None, None
    except Exception as e:
        st.error(f"⚠️ Error al leer los archivos: {e}")
        return None, None


# ---------- INTERFAZ PRINCIPAL ----------
def main():
    st.title("📊 Boca Juniors 2024 - Análisis de Datos y Violencia Doméstica")
    st.write("Esta app combina datos de **resultados deportivos** con estadísticas de **violencia doméstica** (Línea 137/144).")

    # --- OPCIONES DE CARGA ---
    st.sidebar.header("🔧 Configuración de archivos")

    uploaded_calls = st.sidebar.file_uploader("Subí el archivo de llamadas (CSV)", type=["csv"])
    uploaded_matches = st.sidebar.file_uploader("Subí el archivo de resultados deportivos (CSV)", type=["csv"])

    default_calls = "data/linea137_2024.csv"
    default_matches = "data/boca_matches_2024.csv"

    # --- SELECCIÓN AUTOMÁTICA SI EXISTEN LOS ARCHIVOS ---
    if uploaded_calls is not None and uploaded_matches is not None:
        df_calls = pd.read_csv(uploaded_calls, encoding="latin1")
        df_matches = pd.read_csv(uploaded_matches, encoding="latin1")
    elif os.path.exists(default_calls) and os.path.exists(default_matches):
        df_calls, df_matches = load_data(default_calls, default_matches)
    else:
        st.warning("📂 Subí ambos archivos CSV o colócalos en la carpeta `/data`.")
        return

    # --- MUESTRA DE DATOS ---
    st.subheader("📈 Datos de violencia (Línea 137/144)")
    st.dataframe(df_calls.head())

    st.subheader("⚽ Resultados de Boca Juniors 2024")
    st.dataframe(df_matches.head())

    # --- ANÁLISIS BÁSICO ---
    st.header("📊 Análisis Exploratorio")
    st.write("Comparación mensual entre llamadas de emergencia y resultados del club.")

    # Supongamos que hay columnas 'mes' en ambos CSV:
    if "mes" in df_calls.columns and "mes" in df_matches.columns:
        merged = pd.merge(df_matches, df_calls, on="mes", how="inner")
        st.write("✅ Datos combinados correctamente:")
        st.dataframe(merged)
    else:
        st.warning("No se pudo combinar: faltan columnas 'mes' en uno o ambos archivos.")


if __name__ == "__main__":
    main()


