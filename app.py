
import streamlit as st
import pandas as pd

# Load data
@st.cache_data
def load_data():
    df = pd.read_excel("rate_card_data.xls")
    # Remove rows 107 to 109 (adjusting for zero-based index, these are 106, 107, 108)
    df = df.drop(index=[106, 107, 108], errors='ignore')
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("🔧 Uplift Parameters")
branches = df["Branch"].unique()
capabilities = df["Capability"].unique()
teams = df["Department / Team"].unique()
jobs = df["Job Title"].unique()

selected_branch = st.sidebar.selectbox("Select Branch", ["All"] + list(branches))
selected_capability = st.sidebar.selectbox("Select Capability", ["All"] + list(capabilities))
selected_team = st.sidebar.selectbox("Select Department / Team", ["All"] + list(teams))
selected_job = st.sidebar.selectbox("Select Job Title", ["All"] + list(jobs))

uplift_type = st.sidebar.radio("Uplift Type", ["Percentage", "Fixed $ per Day"])
uplift_value = st.sidebar.number_input("Enter uplift value", value=0.0)

# Apply filters
filtered_df = df.copy()
if selected_branch != "All":
    filtered_df = filtered_df[filtered_df["Branch"] == selected_branch]
if selected_capability != "All":
    filtered_df = filtered_df[filtered_df["Capability"] == selected_capability]
if selected_team != "All":
    filtered_df = filtered_df[filtered_df["Department / Team"] == selected_team]
if selected_job != "All":
    filtered_df = filtered_df[filtered_df["Job Title"] == selected_job]

# Calculate uplifted daily rate
if uplift_type == "Percentage":
    filtered_df["Uplifted Rate Daily"] = filtered_df["Charge Rate Daily"] * (1 + uplift_value / 100)
else:
    filtered_df["Uplifted Rate Daily"] = filtered_df["Charge Rate Daily"] + uplift_value

# Calculate new revenue (billable days already include headcount impact)
billable_cols = filtered_df.columns[14:26]
chargeability_cols = filtered_df.columns[26:38]

for month, bill_col, chg_col in zip(filtered_df.columns[38:], billable_cols, chargeability_cols):
    filtered_df[month] = filtered_df["Uplifted Rate Daily"] * filtered_df[bill_col] * filtered_df[chg_col]

# Summary
monthly_totals = filtered_df[filtered_df.columns[38:]].sum()
st.subheader("📊 Monthly Revenue Summary")
st.dataframe(monthly_totals)

st.subheader("📋 Detailed Data")
st.dataframe(filtered_df)
