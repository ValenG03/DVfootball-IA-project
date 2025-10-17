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
    except Exception:
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
            df = pd.DataFrame([r + [None] * (max_cols - len(r)) for r in data_rows], columns=columns)
            # Attempt parse first column as d/m/Y (common in your CSV)
            df["Match_Date"] = pd.to_datetime(dates, format="%d/%m/%Y", errors="coerce")
            return df
        except Exception as e2:
            st.sidebar.error(f"Could not parse football CSV: {e2}")
            return None

def detect_date_column(df_calls):
    # Prefer explicit column names commonly present in dataset
    candidates = [c for c in df_calls.columns if c and ("llamado" in c.lower() and "fecha" in c.lower())]
    if candidates:
        return candidates[0]
    # fallback: look for columns with 'fecha' or 'date'
    candidates2 = [c for c in df_calls.columns if "fecha" in c.lower() or "date" in c.lower()]
    if candidates2:
        return candidates2[0]
    # last resort: try to find a column parseable as a date
    for c in df_calls.columns:
        try:
            non_null = df_calls[c].dropna()
            if non_null.empty:
                continue
            sample = non_null.iloc[0]
            pd.to_datetime(sample)
            return c
        except Exception:
            continue
    return None

def parse_date_series(series):
    # Normalize and try multiple strategies to parse dates robustly.
    s = series.astype(str).str.strip()
    # Try dayfirst True first (your football CSV uses dd/mm/YYYY)
    parsed = pd.to_datetime(s, errors="coerce", dayfirst=True)
    # If too many NaTs, try ISO and common formats
    if parsed.isna().sum() > len(parsed) * 0.2:
        fmt_tried = False
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                candidate = pd.to_datetime(s, format=fmt, errors="coerce")
                if candidate.notna().sum() > parsed.notna().sum():
                    parsed = candidate
                    fmt_tried = True
            except Exception:
                continue
        if not fmt_tried:
            # lastly let pandas try flexible parsing
            parsed = pd.to_datetime(s, errors="coerce")
    return parsed

def weekend_friday_to_sunday_for_matchdate(ts):
    # Given a Timestamp/date for a match, define the Friday-Sunday weekend we consider "the match weekend".
    ts = pd.Timestamp(ts)
    dow = ts.weekday()  # Mon=0 ... Sun=6
    # If match happens Fri/Sat/Sun, use that weekend (Friday on or before match_date)
    if dow in (4,5,6):
        # days to subtract to get friday
        days_to_subtract = dow - 4
        friday = ts - pd.Timedelta(days=days_to_subtract)
    else:
        # if match happens Mon-Thu, choose the upcoming Friday of that week
        days_until_friday = (4 - dow) % 7
        friday = ts + pd.Timedelta(days=days_until_friday)
    sunday = friday + pd.Timedelta(days=2)
    return (pd.Timestamp(friday).date(), pd.Timestamp(sunday).date())

def weekend_for_call_date(ts):
    # For a given call date, decide the "call's weekend window":
    # - If call is Fri/Sat/Sun -> that weekend's Friday-Sunday
    # - If call is Mon-Thu -> attribute it to the previous weekend's Friday-Sunday (so Mon-Thu belong to the prior weekend)
    ts = pd.Timestamp(ts)
    dow = ts.weekday()
    if dow in (4,5,6):
        # friday on or before ts
        days_to_subtract = dow - 4
        friday = ts - pd.Timedelta(days=days_to_subtract)
    else:
        # previous week's friday
        days_to_subtract = dow + 3  # Mon(0)->3 days back to previous Friday, Tue->4, etc.
        friday = ts - pd.Timedelta(days=days_to_subtract)
    sunday = friday + pd.Timedelta(days=2)
    return (pd.Timestamp(friday).date(), pd.Timestamp(sunday).date())

def get_weekend_range_for_date_obj(date_obj, weekend_ranges_list):
    if pd.isna(date_obj):
        return None
    d = pd.Timestamp(date_obj).date()
    for st_date, end_date in weekend_ranges_list:
        if st_date <= d <= end_date:
            return (st_date, end_date)
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

# Debugging previews
st.subheader("Input previews and dtypes (debug)")
st.write("Calls sample:")
st.write(df_calls.head(3))
st.write(df_calls.dtypes)
st.write("Football sample:")
st.write(df_football.head(5))
st.write(df_football.dtypes)

# Prepare calls date column
date_col = detect_date_column(df_calls)
if date_col is None:
    st.error("Could not detect a date column in calls data. Expected something like 'llamado_fecha' or similar.")
    st.write("Calls CSV columns:", list(df_calls.columns))
    st.stop()

# Parse calls dates robustly
df_calls[date_col] = parse_date_series(df_calls[date_col])
parsed_calls_nans = df_calls[date_col].isna().sum()
st.info(f"Calls date column detected: '{date_col}'. Parsed {len(df_calls)-parsed_calls_nans} rows, {parsed_calls_nans} NaT rows.")

# Store a date-only column for comparison (python date objects)
df_calls["llamado_fecha_date"] = df_calls[date_col].dt.date

# Ensure football has Match_Date (detect common header names)
if "Match_Date" not in df_football.columns:
    fcand = [c for c in df_football.columns if "date" in c.lower() or "fecha" in c.lower() or "match" in c.lower()]
    if fcand:
        df_football["Match_Date"] = parse_date_series(df_football[fcand[0]])
    else:
        # if no header found, try first column
        try:
            df_football["Match_Date"] = parse_date_series(df_football.iloc[:, 0])
            st.warning("Football file didn't have an obvious date column name; using first column as Match_Date.")
        except Exception:
            df_football["Match_Date"] = pd.NaT

# If many NaTs in Match_Date, try additional formats for first column as a last attempt
if df_football["Match_Date"].isna().sum() >= len(df_football) * 0.5:
    st.info("Many football Match_Date values are NaT; trying specific dd/mm/YYYY parsing on first column.")
    try:
        cand = pd.to_datetime(df_football.iloc[:, 0].astype(str).str.strip(), format="%d/%m/%Y", errors="coerce")
        if cand.notna().sum() > df_football["Match_Date"].notna().sum():
            df_football["Match_Date"] = cand
            st.success("Parsed additional Match_Date values using '%d/%m/%Y' format.")
    except Exception:
        pass

# final diagnostic of parsed matches
match_dates = pd.Series(df_football["Match_Date"]).dropna().unique().tolist()
st.write(f"Extracted {len(match_dates)} unique match dates from football data.")
if len(match_dates) == 0:
    st.warning("No match dates were parsed from the football file. Check the football preview above and confirm the date column and format (dd/mm/YYYY).")

# Build weekend ranges for each match date (Friday-Sunday)
weekend_ranges = []
for md in match_dates:
    try:
        weekend_ranges.append(weekend_friday_to_sunday_for_matchdate(md))
    except Exception:
        continue
# Deduplicate
weekend_ranges = sorted(list(set(weekend_ranges)))
st.write(f"Defined {len(weekend_ranges)} match weekend ranges. Sample (up to 10): {weekend_ranges[:10]}")

# Build set of all weekend dates (for fast membership)
all_match_weekend_dates = set()
for start_date, end_date in weekend_ranges:
    cur = start_date
    while cur <= end_date:
        all_match_weekend_dates.add(cur)
        cur = cur + timedelta(days=1)

# Also get match_date set for exact match-days
match_date_set = set(pd.Timestamp(d).date() for d in match_dates)

# Mark calls that happen on match day or match weekend
df_calls["is_match_day"] = df_calls["llamado_fecha_date"].isin(match_date_set)
df_calls["is_match_weekend"] = df_calls["llamado_fecha_date"].isin(all_match_weekend_dates)
df_calls["is_match_day_or_weekend"] = df_calls["is_match_day"] | df_calls["is_match_weekend"]

df_match_weekend_calls = df_calls[df_calls["is_match_weekend"]].copy()
df_match_day_calls = df_calls[df_calls["is_match_day"]].copy()
df_match_day_or_weekend_calls = df_calls[df_calls["is_match_day_or_weekend"]].copy()

st.write(f"Calls on exact match days: {len(df_match_day_calls)}")
st.write(f"Calls on match weekends (Fri-Sun): {len(df_match_weekend_calls)}")
st.write(f"Calls on match day OR match weekend: {len(df_match_day_or_weekend_calls)}")

# For convenience, compute calls' weekend_range according to calls' date (so each call has an attributed weekend)
df_calls["calls_weekend_range"] = df_calls[date_col].apply(lambda x: weekend_for_call_date(x) if not pd.isna(x) else None)
unique_calls_weekend_ranges = [r for r in df_calls["calls_weekend_range"].dropna().unique().tolist()]

# Non-match weekends observed in calls (weekends present in calls but not in football weekends)
football_weekend_ranges_set = set(weekend_ranges)
non_match_weekend_ranges = [w for w in unique_calls_weekend_ranges if w not in football_weekend_ranges_set]
all_non_match_weekend_dates = set()
for start_date, end_date in non_match_weekend_ranges:
    cur = start_date
    while cur <= end_date:
        all_non_match_weekend_dates.add(cur)
        cur = cur + timedelta(days=1)

df_non_match_weekend_calls = df_calls[df_calls["llamado_fecha_date"].isin(all_non_match_weekend_dates)].copy()
st.write(f"Calls on non-match weekends: {len(df_non_match_weekend_calls)}")

# Simple comparison
col1, col2, col3 = st.columns(3)
col1.metric("Match day calls", len(df_match_day_calls))
col2.metric("Match weekend calls (Fri-Sun)", len(df_match_weekend_calls))
col3.metric("Non-match weekend calls", len(df_non_match_weekend_calls))

# Merge match-day/weekend calls with football by weekend_range (for weekend merges) and by Match_Date (for exact-day merges)
# Create weekend_range columns
df_calls["weekend_range"] = df_calls[date_col].apply(lambda x: get_weekend_range_for_date_obj(x, weekend_ranges) if not pd.isna(x) else None)
df_football["weekend_range"] = df_football["Match_Date"].apply(lambda x: weekend_friday_to_sunday_for_matchdate(x) if not pd.isna(x) else None)

# --- Fix applied: create a date-only column on the football df and merge using column names ---
# ensure football has a date-only column we can merge on
df_football["Match_Date_date"] = df_football["Match_Date"].dt.date

# Merge calls that fall exactly on match days using column names (no Series expressions)
merged_day = pd.merge(
    df_calls[df_calls["is_match_day"]].copy(),
    df_football.dropna(subset=["Match_Date", "Match_Date_date"]).copy(),
    left_on="llamado_fecha_date",
    right_on="Match_Date_date",
    how="left",
    suffixes=("_call", "_match")
)
st.write(f"Merged rows (calls matched to football by exact match date): {len(merged_day)}")

# Merge by weekend_range
merged_weekend = pd.merge(
    df_calls[df_calls["is_match_weekend"]].copy(),
    df_football.dropna(subset=["weekend_range"]).copy(),
    on="weekend_range",
    how="left",
    suffixes=("_call", "_match")
)
st.write(f"Merged rows (calls matched to football by weekend_range): {len(merged_weekend)}")

# Attempt to detect match result column in football df (common result column used in notebook: col_6 / 'Result')
result_col = None
for c in df_football.columns:
    if "result" in c.lower() or "res" in c.lower() or c.lower().strip() in ("col_6", "resultado", "resul"):
        result_col = c
        break
if result_col is None and "Result" in df_football.columns:
    result_col = "Result"
if result_col is None and "col_6" in df_football.columns:
    result_col = "col_6"

if result_col is None:
    st.warning("Could not automatically detect a match result column in football data. You can select one manually.")
    result_col = st.selectbox("Select the match result column (if available):", options=["(none)"] + list(df_football.columns))
    if result_col == "(none)":
        result_col = None

if result_col is not None:
    calls_with_results = pd.merge(
        df_calls[df_calls["is_match_day_or_weekend"]].copy(),
        df_football[[result_col, "Match_Date", "weekend_range", "Match_Date_date"]].copy(),
        left_on="weekend_range",
        right_on="weekend_range",
        how="left"
    )
    calls_by_result = calls_with_results[calls_with_results[result_col].notna()].groupby(result_col).size().reset_index(name="call_count")
    st.subheader("Distribution of calls by reported match result (on matched weekends)")
    st.dataframe(calls_by_result)
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=calls_by_result, x=result_col, y="call_count", palette="viridis", ax=ax)
    ax.set_title("Calls by match result (on match weekends/days)")
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
    "- I now explicitly parse dates with dayfirst=True (commonly dd/mm/YYYY) and fallbacks for multiple formats.\n"
    "- The app marks both exact match days and the wider Friday–Sunday weekend for each match. Calls are attributed to the previous weekend if they occur Mon-Thu (so weekly grouping is consistent).\n"
    "- If you still see 0 matches, check the football preview above and confirm your football date column and format (header name or dd/mm/YYYY). You can also select the result column manually if auto-detection fails.\n"
)
