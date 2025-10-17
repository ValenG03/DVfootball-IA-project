# Streamlit app for analyzing calls vs Boca Juniors match weekends
# Place this file next to your CSVs or upload them via the UI.
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import csv
import io
from datetime import datetime, timedelta

st.set_page_config(page_title="Boca Matches vs Calls Analysis", layout="wide")

st.title("Boca Juniors Match Weekends vs Domestic Violence Calls")
st.markdown(
    "Analyze domestic violence call volumes on Boca Juniors match weekends vs non-match weekends. "
    "Upload the two CSVs or use local files."
)

# Sidebar: file upload or local path option
st.sidebar.header("Data inputs")
use_upload = st.sidebar.radio("Provide data via:", ("Upload files", "Local files (path)"))

calls_file = None
football_file = None

if use_upload == "Upload files":
    calls_upload = st.sidebar.file_uploader(
        "Upload llamados-violencia-familiar-202407-Argentina.csv", type=["csv"]
    )
    football_upload = st.sidebar.file_uploader(
        "Upload Boca Juniors Results Tournament May-Dic-2024.csv", type=["csv"]
    )
    if calls_upload:
        calls_file = io.StringIO(calls_upload.getvalue().decode("utf-8", errors="replace"))
    if football_upload:
        # football file may be latin1 encoded; try to decode safely
        try:
            football_file = io.StringIO(football_upload.getvalue().decode("latin1"))
        except Exception:
            football_file = io.StringIO(football_upload.getvalue().decode("utf-8", errors="replace"))
else:
    st.sidebar.markdown("Provide local file paths (relative to where you run streamlit).")
    calls_path = st.sidebar.text_input("Calls CSV path", value="llamados-violencia-familiar-202407-Argentina.csv")
    football_path = st.sidebar.text_input("Football CSV path", value="Boca Juniors Results Tournament May-Dic-2024.csv")
    if calls_path:
        calls_file = calls_path
    if football_path:
        football_file = football_path

@st.cache_data
def load_calls(csv_input):
    try:
        df = pd.read_csv(csv_input, low_memory=False)
        st.sidebar.success("Calls CSV loaded using pandas.read_csv")
        return df
    except Exception as e:
        st.sidebar.warning(f"Failed reading calls CSV with pandas: {e}")
        # try manual fallback
        try:
            content = pd.read_table(csv_input, sep=",", engine="python", encoding="utf-8")
            return content
        except Exception:
            st.sidebar.error("Unable to read calls CSV. Please check encoding or file format.")
            return None

@st.cache_data
def load_football(csv_input):
    # Football CSV may have irregular columns; try pandas first, then fallback to manual parsing.
    try:
        df = pd.read_csv(csv_input, encoding="latin1", low_memory=False)
        st.sidebar.success("Football CSV loaded using pandas.read_csv (latin1)")
        return df
    except Exception as e:
        st.sidebar.info("Falling back to robust CSV parsing for football results.")
        try:
            # try reading as text then csv.reader
            if isinstance(csv_input, str):
                f = open(csv_input, "r", encoding="latin1", errors="replace")
            else:
                # file-like
                csv_input.seek(0)
                f = io.TextIOWrapper(csv_input.buffer, encoding="latin1", errors="replace") if hasattr(csv_input, "buffer") else csv_input
            reader = csv.reader(f)
            header = next(reader, None)
            dates = []
            data_rows = []
            for row in reader:
                if not row:
                    continue
                dates.append(row[0])
                data_rows.append(row[1:])
            max_cols = max((len(r) for r in data_rows), default=0)
            columns = [f"col_{i}" for i in range(max_cols)]
            df = pd.DataFrame([r + [None] * (max_cols - len(r)) for r in data_rows], columns=columns)
            df["Match_Date"] = pd.to_datetime(dates, format="%d/%m/%Y", errors="coerce")
            return df
        except Exception as e2:
            st.sidebar.error(f"Could not parse football CSV: {e2}")
            return None

def detect_date_column(df_calls):
    # Try to find a date column (common name: llamado_fecha)
    candidates = [c for c in df_calls.columns if "fecha" in c.lower() or "date" in c.lower()]
    if candidates:
        return candidates[0]
    # fallback: inspect dtypes
    for c in df_calls.columns:
        try:
            # try parse first non-null
            sample = df_calls[c].dropna().iloc[0]
            pd.to_datetime(sample)
            return c
        except Exception:
            continue
    return None

def get_friday_to_sunday_weekend(date_obj):
    day_of_week = date_obj.weekday()  # Monday=0 ... Sunday=6
    if day_of_week == 6:
        friday = date_obj - pd.Timedelta(days=2)
    elif day_of_week == 5:
        friday = date_obj - pd.Timedelta(days=1)
    elif day_of_week == 4:
        friday = date_obj
    else:
        days_until_friday = (4 - day_of_week) % 7
        friday = date_obj + pd.Timedelta(days=days_until_friday)
    sunday = friday + pd.Timedelta(days=2)
    return (friday.date(), sunday.date())

def get_weekend_range_for_date(date_obj, weekend_ranges_list):
    date_to_compare = date_obj.date() if hasattr(date_obj, "date") else date_obj
    for start_date, end_date in weekend_ranges_list:
        if start_date <= date_to_compare <= end_date:
            return (start_date, end_date)
    return None

# Load data
df_calls = None
df_football = None
if calls_file:
    df_calls = load_calls(calls_file)
if football_file:
    df_football = load_football(football_file)

if df_calls is None or df_football is None:
    st.warning("Waiting for both files to be provided and loaded. Upload both files or provide valid local paths.")
    st.stop()

# prepare calls dataframe date column
date_col = detect_date_column(df_calls)
if date_col is None:
    st.error("Could not detect a date column in calls data. Expected something like 'llamado_fecha' or similar.")
    st.write("Calls CSV columns:", list(df_calls.columns))
    st.stop()

try:
    df_calls[date_col] = pd.to_datetime(df_calls[date_col], errors="coerce")
except Exception:
    df_calls[date_col] = pd.to_datetime(df_calls[date_col].astype(str), errors="coerce")

df_calls["llamado_fecha_date"] = df_calls[date_col].dt.date

# ensure football has Match_Date
if "Match_Date" not in df_football.columns:
    # try to find a date-like column
    fcand = [c for c in df_football.columns if "date" in c.lower() or "fecha" in c.lower() or "match" in c.lower()]
    if fcand:
        try:
            df_football["Match_Date"] = pd.to_datetime(df_football[fcand[0]], errors="coerce")
        except Exception:
            df_football["Match_Date"] = pd.to_datetime(df_football[fcand[0]].astype(str), errors="coerce")
    else:
        st.warning("Football file doesn't contain 'Match_Date' column; attempting to use a first column as dates.")
        try:
            df_football["Match_Date"] = pd.to_datetime(df_football.iloc[:, 0], errors="coerce")
        except Exception:
            df_football["Match_Date"] = pd.NaT

match_dates = df_football["Match_Date"].dropna().unique().tolist()
st.write(f"Extracted {len(match_dates)} unique match dates from football data.")

# Create weekend ranges for match dates
weekend_ranges = []
for match_date in match_dates:
    day_of_week = match_date.dayofweek
    if day_of_week in [4, 5, 6]:
        friday = match_date - pd.Timedelta(days=(day_of_week - 4))
    else:
        friday = match_date + pd.Timedelta(days=(4 - day_of_week))
    sunday = friday + pd.Timedelta(days=2)
    weekend_ranges.append((friday.date(), sunday.date()))
st.write(f"Defined {len(weekend_ranges)} match weekend ranges.")

# filter calls on match weekends
all_weekend_dates = set()
for start_date, end_date in weekend_ranges:
    current = start_date
    while current <= end_date:
        all_weekend_dates.add(current)
        current = current + timedelta(days=1)

df_calls["is_match_weekend"] = df_calls["llamado_fecha_date"].isin(all_weekend_dates)
df_match_weekend_calls = df_calls[df_calls["is_match_weekend"].copy()]
st.write(f"Calls on match weekends: {len(df_match_weekend_calls)}")

# compute non-match weekends observed in calls
df_calls["calls_weekend_range"] = df_calls[date_col].apply(get_friday_to_sunday_weekend)
unique_calls_weekend_ranges = df_calls["calls_weekend_range"].dropna().unique().tolist()
football_weekend_ranges_set = set(weekend_ranges)
non_match_weekend_ranges = [
    weekend for weekend in unique_calls_weekend_ranges
    if weekend not in football_weekend_ranges_set
]
# gather their dates
all_non_match_weekend_dates = set()
for start_date, end_date in non_match_weekend_ranges:
    current = start_date
    while current <= end_date:
        all_non_match_weekend_dates.add(current)
        current = current + timedelta(days=1)

df_non_match_weekend_calls = df_calls[df_calls["llamado_fecha_date"].isin(all_non_match_weekend_dates)].copy()
st.write(f"Calls on non-match weekends: {len(df_non_match_weekend_calls)}")

# Simple comparison
col1, col2 = st.columns(2)
col1.metric("Match weekend calls", len(df_match_weekend_calls))
col2.metric("Non-match weekend calls", len(df_non_match_weekend_calls))

# Merge match-weekend calls with football by weekend_range
df_match_weekend_calls["weekend_range"] = df_match_weekend_calls[date_col].apply(lambda x: get_weekend_range_for_date(x, weekend_ranges))
df_football["weekend_range"] = df_football["Match_Date"].apply(lambda x: get_weekend_range_for_date(x, weekend_ranges))
merged_df = pd.merge(df_match_weekend_calls, df_football, on="weekend_range", how="inner")
st.write(f"Merged calls-with-matches rows: {len(merged_df)}")

# Attempt to detect match result column in football df (common result column used in notebook: col_6)
result_col = None
for c in df_football.columns:
    if "result" in c.lower() or "res" in c.lower() or c.lower().strip() in ("col_6", "resultado", "resul"):
        result_col = c
        break
# fallback to 'col_6' if present
if result_col is None and "col_6" in df_football.columns:
    result_col = "col_6"

if result_col is None:
    st.warning("Could not automatically detect a match result column in football data. You can select one manually.")
    result_col = st.selectbox("Select the match result column (if available):", options=["(none)"] + list(df_football.columns))
    if result_col == "(none)":
        result_col = None

if result_col is not None:
    valid_results = ['W', 'L', 'T', 'D', 'Win', 'Loss', 'Draw']
    calls_by_result = merged_df[merged_df[result_col].notna()].groupby(result_col).size().reset_index(name="call_count")
    st.subheader("Distribution of calls by reported match result")
    st.dataframe(calls_by_result)
    # Plot
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=calls_by_result, x=result_col, y="call_count", palette="viridis", ax=ax)
    ax.set_title("Calls by match result (on match weekends)")
    st.pyplot(fig)
else:
    st.info("Skipping calls-by-result analysis because no result column is available.")

# Plot overall comparison of match vs non-match volumes
st.subheader("Comparison of call volumes")
DF_call_volume = pd.DataFrame({
    "Weekend Type": ["Match Weekend", "Non-Match Weekend"],
    "Call Count": [len(df_match_weekend_calls), len(df_non_match_weekend_calls)]
})
fig2, ax2 = plt.subplots(figsize=(6,4))
sns.barplot(data=DF_call_volume, x="Weekend Type", y="Call Count", palette="viridis", ax=ax2)
ax2.set_title("Call volume: Match vs Non-Match weekends")
st.pyplot(fig2)

# Optionally show raw data
with st.expander("Show sample of calls data"):
    st.dataframe(df_calls.head(200))

with st.expander("Show sample of football data"):
    st.dataframe(df_football.head(200))

st.markdown("---")
st.markdown("Notes:")
st.markdown(
    "- The football file format may vary; the app tries to detect date/result columns but may need manual guidance.\n"
    "- If parsing fails for the football file, try saving it with a stable delimiter/encoding and re-uploading.\n"
)

# Streamlit app for analyzing calls vs Boca Juniors match weekends
# Place this file next to your CSVs or upload them via the UI.
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import csv
import io
from datetime import timedelta

st.set_page_config(page_title="Boca Matches vs Calls Analysis", layout="wide")

st.title("Boca Juniors Match Weekends vs Domestic Violence Calls")
st.markdown(
    "Analyze domestic violence call volumes on Boca Juniors match weekends vs non-match weekends. "
    "Upload the two CSVs or use local files."
)

# Sidebar: file upload or local path option
st.sidebar.header("Data inputs")
use_upload = st.sidebar.radio("Provide data via:", ("Upload files", "Local files (path)"))

calls_file = None
football_file = None

if use_upload == "Upload files":
    calls_upload = st.sidebar.file_uploader(
        "Upload llamados-violencia-familiar-202407-Argentina.csv", type=["csv"]
    )
    football_upload = st.sidebar.file_uploader(
        "Upload Boca Juniors Results Tournament May-Dic-2024.csv", type=["csv"]
    )
    if calls_upload:
        calls_file = io.StringIO(calls_upload.getvalue().decode("utf-8", errors="replace"))
    if football_upload:
        # football file may be latin1 encoded; try to decode safely
        try:
            football_file = io.StringIO(football_upload.getvalue().decode("latin1"))
        except Exception:
            football_file = io.StringIO(football_upload.getvalue().decode("utf-8", errors="replace"))
else:
    st.sidebar.markdown("Provide local file paths (relative to where you run streamlit).")
    calls_path = st.sidebar.text_input("Calls CSV path", value="llamados-violencia-familiar-202407-Argentina.csv")
    football_path = st.sidebar.text_input("Football CSV path", value="Boca Juniors Results Tournament May-Dic-2024.csv")
    if calls_path:
        calls_file = calls_path
    if football_path:
        football_file = football_path

@st.cache_data
def load_calls(csv_input):
    # attempt pandas read first, fallback to python engine if needed
    try:
        df = pd.read_csv(csv_input, low_memory=False)
        st.sidebar.success("Calls CSV loaded using pandas.read_csv")
        return df
    except Exception as e:
        st.sidebar.warning(f"Failed reading calls CSV with pandas: {e}")
        try:
            content = pd.read_table(csv_input, sep=",", engine="python", encoding="utf-8")
            return content
        except Exception:
            st.sidebar.error("Unable to read calls CSV. Please check encoding or file format.")
            return None

@st.cache_data
def load_football(csv_input):
    # try pandas read first (latin1 often for spreadsheets exported from Excel)
    try:
        df = pd.read_csv(csv_input, encoding="latin1", low_memory=False)
        st.sidebar.success("Football CSV loaded using pandas.read_csv (latin1)")
        return df
    except Exception as e:
        st.sidebar.info("Falling back to robust CSV parsing for football results.")
        try:
            if isinstance(csv_input, str):
                f = open(csv_input, "r", encoding="latin1", errors="replace")
            else:
                csv_input.seek(0)
                f = io.TextIOWrapper(csv_input.buffer, encoding="latin1", errors="replace") if hasattr(csv_input, "buffer") else csv_input
            reader = csv.reader(f)
            header = next(reader, None)
            dates = []
            data_rows = []
            for row in reader:
                if not row:
                    continue
                dates.append(row[0])
                data_rows.append(row[1:])
            max_cols = max((len(r) for r in data_rows), default=0)
            columns = [f"col_{i}" for i in range(max_cols)]
            df = pd.DataFrame([r + [None] *
