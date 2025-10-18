import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

def load_data(calls_filepath, matches_filepath):
    """Loads the calls and matches data into pandas DataFrames."""
    df_calls = pd.read_csv(calls_filepath, encoding='latin1')
    df_matches = pd.read_excel(matches_filepath, header=None)

    # Preprocess matches data
    df_matches = df_matches.iloc[1:].copy()
    df_matches = df_matches[0].str.split(',', expand=True)
    df_matches.columns = ['Date', 'Tournament', 'Instance', 'Rival', 'Boca_Goals', 'Rival_Goals', 'Result', 'Stadium', 'Home_or_Away', 'Win_Draw_Loss']

    return df_calls, df_matches

def preprocess_dates(df_calls, df_matches):
    """Cleans and formats date columns in both DataFrames."""
    df_calls['llamado_fecha'] = pd.to_datetime(df_calls['llamado_fecha']).dt.date
    df_matches['Date'] = pd.to_datetime(df_matches['Date']).dt.date
    return df_calls, df_matches

def merge_data(df_calls, df_matches):
    """Merges the two DataFrames based on the dates."""
    df_merged = pd.merge(df_calls, df_matches, left_on='llamado_fecha', right_on='Date', how='inner')
    return df_merged

def analyze_calls(df_calls, df_merged, df_matches):
    """Analyzes domestic violence calls on weekend days with and without Boca matches."""
    df_calls['llamado_fecha'] = pd.to_datetime(df_calls['llamado_fecha'])
    df_calls['weekday'] = df_calls['llamado_fecha'].dt.dayofweek
    df_weekends = df_calls[df_calls['weekday'].isin([5, 6])].copy()

    boca_match_dates = df_matches['Date'].unique()
    df_weekends_no_boca = df_weekends[~df_weekends['llamado_fecha'].dt.date.isin(boca_match_dates)].copy()

    num_calls_boca_playing = df_merged.shape[0]
    num_calls_boca_not_playing_weekend = df_weekends_no_boca.shape[0]

    num_boca_playing_weekend_days = df_merged['llamado_fecha'].nunique()
    num_boca_not_playing_weekend_days = df_weekends_no_boca['llamado_fecha'].nunique()

    avg_calls_boca_playing_weekend = num_calls_boca_playing / num_boca_playing_weekend_days if num_boca_playing_weekend_days > 0 else 0
    avg_calls_boca_not_playing_weekend = num_calls_boca_not_playing_weekend / num_boca_not_playing_weekend_days if num_boca_not_playing_weekend_days > 0 else 0

    analysis_results = {
        "num_calls_boca_playing": num_calls_boca_playing,
        "num_boca_playing_weekend_days": num_boca_playing_weekend_days,
        "avg_calls_boca_playing_weekend": avg_calls_boca_playing_weekend,
        "num_calls_boca_not_playing_weekend": num_calls_boca_not_playing_weekend,
        "num_boca_not_playing_weekend_days": num_boca_not_playing_weekend_days,
        "avg_calls_boca_not_playing_weekend": avg_calls_boca_not_playing_weekend
    }

    return analysis_results

def visualize_data(df_calls, df_matches):
    """Creates visualizations for the original DataFrames."""
    fig1, ax1 = plt.subplots(figsize=(15, 6))
    calls_per_day = df_calls.groupby('llamado_fecha').size()
    ax1.plot(calls_per_day.index, calls_per_day.values)
    ax1.set_title('Domestic Violence Calls Over Time')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Number of Calls')
    ax1.grid(True)

    fig2, ax2 = plt.subplots(figsize=(15, 2))
    ax2.scatter(df_matches['Date'], [1] * len(df_matches), marker='|', s=100)
    ax2.set_title('Boca Juniors Match Dates')
    ax2.set_xlabel('Date')
    ax2.set_yticks([])
    ax2.grid(True)

    return fig1, fig2

def main():
    """Main function to run the data processing and analysis."""
    st.title("Domestic Violence Calls and Boca Juniors Matches Analysis")

    calls_filepath = "/content/Llamados Violencia Familiar hasta Agosto 2024 Argentina.csv"
    matches_filepath = "/content/Boca_2024_Whole_Year.csv.xlsx"

    df_calls, df_matches = load_data(calls_filepath, matches_filepath)
    df_calls, df_matches = preprocess_dates(df_calls, df_matches)
    df_merged = merge_data(df_calls, df_matches)
    analysis_results = analyze_calls(df_calls, df_merged, df_matches)
    fig1, fig2 = visualize_data(df_calls, df_matches)

    st.write("Analysis Results:")
    st.write(f"Number of domestic violence calls on weekend days Boca played: {analysis_results['num_calls_boca_playing']}")
    st.write(f"Number of unique weekend days Boca played: {analysis_results['num_boca_playing_weekend_days']}")
    st.write(f"Average calls per weekend day Boca played: {analysis_results['avg_calls_boca_playing_weekend']:.2f}")
    st.write("-" * 30)
    st.write(f"Number of domestic violence calls on weekend days Boca did not play: {analysis_results['num_calls_boca_not_playing_weekend']}")
    st.write(f"Number of unique weekend days Boca did not play: {analysis_results['num_boca_not_playing_weekend_days']}")
    st.write(f"Average calls per weekend day Boca did not play: {analysis_results['avg_calls_boca_not_playing_weekend']:.2f}")

    st.pyplot(fig1)
    st.pyplot(fig2)

if __name__ == '__main__':
    main()

!pip install streamlit

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

def load_data(calls_filepath, matches_filepath):
    """Loads the calls and matches data into pandas DataFrames."""
    df_calls = pd.read_csv(calls_filepath, encoding='latin1')
    df_matches = pd.read_excel(matches_filepath, header=None)

    # Preprocess matches data
    df_matches = df_matches.iloc[1:].copy()
    df_matches = df_matches[0].str.split(',', expand=True)
    df_matches.columns = ['Date', 'Tournament', 'Instance', 'Rival', 'Boca_Goals', 'Rival_Goals', 'Result', 'Stadium', 'Home_or_Away', 'Win_Draw_Loss']

    return df_calls, df_matches

def preprocess_dates(df_calls, df_matches):
    """Cleans and formats date columns in both DataFrames."""
    df_calls['llamado_fecha'] = pd.to_datetime(df_calls['llamado_fecha']).dt.date
    df_matches['Date'] = pd.to_datetime(df_matches['Date']).dt.date
    return df_calls, df_matches

def merge_data(df_calls, df_matches):
    """Merges the two DataFrames based on the dates."""
    df_merged = pd.merge(df_calls, df_matches, left_on='llamado_fecha', right_on='Date', how='inner')
    return df_merged

def analyze_calls(df_calls, df_merged, df_matches):
    """Analyzes domestic violence calls on weekend days with and without Boca matches."""
    df_calls['llamado_fecha'] = pd.to_datetime(df_calls['llamado_fecha'])
    df_calls['weekday'] = df_calls['llamado_fecha'].dt.dayofweek
    df_weekends = df_calls[df_calls['weekday'].isin([5, 6])].copy()

    boca_match_dates = df_matches['Date'].unique()
    df_weekends_no_boca = df_weekends[~df_weekends['llamado_fecha'].dt.date.isin(boca_match_dates)].copy()

    num_calls_boca_playing = df_merged.shape[0]
    num_calls_boca_not_playing_weekend = df_weekends_no_boca.shape[0]

    num_boca_playing_weekend_days = df_merged['llamado_fecha'].nunique()
    num_boca_not_playing_weekend_days = df_weekends_no_boca['llamado_fecha'].nunique()

    avg_calls_boca_playing_weekend = num_calls_boca_playing / num_boca_playing_weekend_days if num_boca_playing_weekend_days > 0 else 0
    avg_calls_boca_not_playing_weekend = num_calls_boca_not_playing_weekend / num_boca_not_playing_weekend_days if num_boca_not_playing_weekend_days > 0 else 0

    analysis_results = {
        "num_calls_boca_playing": num_calls_boca_playing,
        "num_boca_playing_weekend_days": num_boca_playing_weekend_days,
        "avg_calls_boca_playing_weekend": avg_calls_boca_playing_weekend,
        "num_calls_boca_not_playing_weekend": num_calls_boca_not_playing_weekend,
        "num_boca_not_playing_weekend_days": num_boca_not_playing_weekend_days,
        "avg_calls_boca_not_playing_weekend": avg_calls_boca_not_playing_weekend
    }

    return analysis_results

def visualize_data(df_calls, df_matches):
    """Creates visualizations for the original DataFrames."""
    fig1, ax1 = plt.subplots(figsize=(15, 6))
    calls_per_day = df_calls.groupby('llamado_fecha').size()
    ax1.plot(calls_per_day.index, calls_per_day.values)
    ax1.set_title('Domestic Violence Calls Over Time')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Number of Calls')
    ax1.grid(True)

    fig2, ax2 = plt.subplots(figsize=(15, 2))
    ax2.scatter(df_matches['Date'], [1] * len(df_matches), marker='|', s=100)
    ax2.set_title('Boca Juniors Match Dates')
    ax2.set_xlabel('Date')
    ax2.set_yticks([])
    ax2.grid(True)

    return fig1, fig2

def main():
    """Main function to run the data processing and analysis."""
    st.title("Domestic Violence Calls and Boca Juniors Matches Analysis")

    calls_filepath = "/content/Llamados Violencia Familiar hasta Agosto 2024 Argentina.csv"
    matches_filepath = "/content/Boca_2024_Whole_Year.csv.xlsx"

    df_calls, df_matches = load_data(calls_filepath, matches_filepath)
    df_calls, df_matches = preprocess_dates(df_calls, df_matches)
    df_merged = merge_data(df_calls, df_matches)
    analysis_results = analyze_calls(df_calls, df_merged, df_matches)
    fig1, fig2 = visualize_data(df_calls, df_matches)

    st.write("Analysis Results:")
    st.write(f"Number of domestic violence calls on weekend days Boca played: {analysis_results['num_calls_boca_playing']}")
    st.write(f"Number of unique weekend days Boca played: {analysis_results['num_boca_playing_weekend_days']}")
    st.write(f"Average calls per weekend day Boca played: {analysis_results['avg_calls_boca_playing_weekend']:.2f}")
    st.write("-" * 30)
    st.write(f"Number of domestic violence calls on weekend days Boca did not play: {analysis_results['num_calls_boca_not_playing_weekend']}")
    st.write(f"Number of unique weekend days Boca did not play: {analysis_results['num_boca_not_playing_weekend_days']}")
    st.write(f"Average calls per weekend day Boca did not play: {analysis_results['avg_calls_boca_not_playing_weekend']:.2f}")

    st.pyplot(fig1)
    st.pyplot(fig2)

if __name__ == '__main__':
    main()


