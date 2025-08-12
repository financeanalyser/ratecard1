
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Rate Card Analyser", layout="wide")
st.title("📊 Rate Card Revenue & Margin Uplift Analyser")

# ---------- Data Loading ----------
@st.cache_data
def load_data(path: str = "rate_card_data.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path)
    # Clean headers
    df.columns = df.columns.astype(str).str.strip()
    # Drop any pre-summed total rows by name pattern
    if "Job Title" in df.columns:
        df = df[~df["Job Title"].astype(str).str.contains("total", case=False, na=False)]
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Unable to load 'rate_card_data.xlsx'. Please ensure it exists in the app directory. Error: {e}")
    st.stop()

# Identify revenue columns (those ending with '.2') and ensure consistent order
revenue_cols = [c for c in df.columns if c.endswith(".2")]
if not revenue_cols:
    st.error("No revenue columns detected. Expected monthly revenue columns with a '.2' suffix (e.g., '2025-07-01 00:00:00.2').")
    st.stop()

# Sort revenue columns by their datetime component if possible
def _col_to_dt(col: str):
    # Strip the trailing ".2" and try to parse
    try:
        base = col.rsplit(".2", 1)[0]
        return pd.to_datetime(base)
    except Exception:
        return pd.NaT

rev_dt = pd.Series({c: _col_to_dt(c) for c in revenue_cols})
revenue_cols = [c for c in rev_dt.sort_values().index]

# ---------- Sidebar Controls ----------
st.sidebar.header("🔧 Uplift Parameters")

# Filters (robust to missing columns)
def safe_unique(col):
    return df[col].dropna().unique() if col in df.columns else []

branches = safe_unique("Branch")
capabilities = safe_unique("Capability")
teams = safe_unique("Department / Team")
jobs = safe_unique("Job Title")

selected_branch = st.sidebar.multiselect("Branch", branches.tolist() if len(branches) else [], default=branches.tolist() if len(branches) else [])
selected_capability = st.sidebar.multiselect("Capability", capabilities.tolist() if len(capabilities) else [], default=capabilities.tolist() if len(capabilities) else [])
selected_team = st.sidebar.multiselect("Department / Team", teams.tolist() if len(teams) else [], default=teams.tolist() if len(teams) else [])
selected_job = st.sidebar.multiselect("Job Title", jobs.tolist() if len(jobs) else [], default=jobs.tolist() if len(jobs) else [])

uplift_type = st.sidebar.radio("Choose uplift type", ["% Increase", "$ Increase"])
if uplift_type == "% Increase":
    uplift_value = st.sidebar.number_input("Rate Uplift (%)", min_value=0.0, max_value=100.0, value=5.0)
else:
    uplift_value = st.sidebar.number_input("Uplift ($ per day)", min_value=0.0, value=50.0)

# Effective month selector (use revenue cols)
month_label_map = {c: _col_to_dt(c).strftime("%b %Y") if pd.notna(_col_to_dt(c)) else c for c in revenue_cols}
effective_month_display = st.sidebar.selectbox("Effective From Month", options=[month_label_map[c] for c in revenue_cols])
# Map back to original column key
reverse_month_map = {v: k for k, v in month_label_map.items()}
effective_month = reverse_month_map[effective_month_display]

# ---------- Filtering ----------
mask = pd.Series(True, index=df.index)
if len(branches):
    mask &= df["Branch"].isin(selected_branch)
if len(capabilities):
    mask &= df["Capability"].isin(selected_capability)
if len(teams):
    mask &= df["Department / Team"].isin(selected_team)
if len(jobs):
    mask &= df["Job Title"].isin(selected_job)

df_base = df.copy()
df_affected = df.loc[mask].copy()
df_unaffected = df.loc[~df.index.isin(df_affected.index)].copy()  # ensure no overlap

# ---------- Apply Uplift Correctly (no double counting headcount) ----------
start_idx = df.columns.get_loc(effective_month)
rev_cols_from_effective = [c for c in revenue_cols if df.columns.get_loc(c) >= start_idx]

rate_col = "Charge Rate Daily"
cost_col = "Cost rate Daily"

if uplift_type == "% Increase":
    factor = 1 + uplift_value / 100.0
    for col in rev_cols_from_effective:
        df_affected[col] = df_affected[col] * factor
else:
    # For fixed $/day uplift, apply proportional revenue uplift based on daily rate per row
    if rate_col not in df_affected.columns:
        st.error(f"'{rate_col}' column not found. Cannot apply $ uplift.")
        st.stop()
    # Avoid division by zero
    safe_rate = df_affected[rate_col].replace(0, np.nan)
    ratio = (uplift_value / safe_rate).fillna(0.0)
    for col in rev_cols_from_effective:
        df_affected[col] = df_affected[col] * (1 + ratio)

# Merge uplifted + unaffected
df_uplifted = pd.concat([df_affected, df_unaffected], ignore_index=True)

# ---------- Summaries ----------
orig_total = df_base[rev_cols_from_effective].sum(numeric_only=True).sum()
uplift_total = df_uplifted[rev_cols_from_effective].sum(numeric_only=True).sum()
incremental = uplift_total - orig_total

# Margin impact on affected roles (using new rate only, independent of month)
if cost_col in df_affected.columns and rate_col in df_affected.columns:
    if uplift_type == "% Increase":
        new_rate = df_affected[rate_col] * (1 + uplift_value / 100.0)
    else:
        new_rate = df_affected[rate_col] + uplift_value
    with np.errstate(divide='ignore', invalid='ignore'):
        new_margin_pct = ((new_rate - df_affected[cost_col]) / new_rate) * 100.0
    avg_margin = float(np.nanmean(new_margin_pct))
else:
    avg_margin = float("nan")

# ---------- Output ----------
st.subheader("📈 Summary (from selected month onward)")
c1, c2, c3 = st.columns(3)
c1.metric("Original Revenue", f"${orig_total:,.0f}")
c2.metric("Uplifted Revenue", f"${uplift_total:,.0f}", delta=f"${incremental:,.0f}")
c3.metric("Avg. New Margin % (Affected Roles)", f"{avg_margin:.2f}%" if not np.isnan(avg_margin) else "N/A")

# Monthly comparison (pretty month labels)
monthly = pd.DataFrame({
    "Month": [month_label_map[c] for c in rev_cols_from_effective],
    "Original": [df_base[c].sum() for c in rev_cols_from_effective],
    "Uplifted": [df_uplifted[c].sum() for c in rev_cols_from_effective],
})
monthly["Delta"] = monthly["Uplifted"] - monthly["Original"]

st.subheader("🗓️ Monthly Revenue Comparison")
st.dataframe(
    monthly.style.format({"Original": "$,.0f", "Uplifted": "$,.0f", "Delta": "$,.0f"}),
    use_container_width=True
)

# Detailed breakdown by role (show all revenue cols, formatted)
st.subheader("📋 Detailed Uplifted Revenue by Role")
display_cols = [c for c in ["Branch", "Capability", "Department / Team", "Job Title"] if c in df_uplifted.columns] + revenue_cols
st.dataframe(
    df_uplifted[display_cols].style.format({col: "$,.0f" for col in revenue_cols}),
    use_container_width=True
)
