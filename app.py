import streamlit as st
import pandas as pd
import plotly.express as px

# Title
st.title("Music Data Explorer")

# Load data
df = pd.read_csv("WorldHits.csv")

# Feature selector (added Duration)
feature = st.selectbox(
    "Select a feature:",
    ["energy", "danceability", "loudness", "tempo", "valence", "duration"]
)

# --- Keep current visualization: line chart of yearly average ---
fig_line = px.line(
    df.groupby("year")[feature].mean().reset_index(),
    x="year",
    y=feature,
    title=f"{feature} Over Time (Yearly Average)"
)
st.plotly_chart(fig_line, use_container_width=True)

# --- New visualization: box plots by musical key ---
fig_box = px.box(
    df,
    x="key",
    y=feature,
    points="all",
    title=f"{feature} by Musical Key"
)
st.plotly_chart(fig_box, use_container_width=True)
