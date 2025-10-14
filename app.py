import streamlit as st
import pandas as pd
import plotly.express as px

# Title
st.title("🎵 Music Data Explorer")

# Load data
df = pd.read_csv('WorldHits.csv')

# Let user select which column to plot
column = st.selectbox(
    "Select a feature to plot over time:",
    ['energy', 'danceability', 'loudness', 'tempo', 'valence']
)

# Create the line chart
fig = px.line(
    df.groupby('year')[column].mean().reset_index(),
    x='year',
    y=column,
    title=f'{column.capitalize()} Over Time'
)

# Display the chart
st.plotly_chart(fig)

st.write(f"Average {column}: {df[column].mean():.2f}")
