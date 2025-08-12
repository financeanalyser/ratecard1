
import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    df = pd.read_excel("rate_card_data.xls")
    # Remove total rows if present
    df = df[df['Branch'].notna()]
    return df

df = load_data()

st.title("📊 Rate Card Uplift Model")

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

uplift_type = st.sidebar.radio("Uplift Type", ["Percentage (%)", "Absolute ($ per day)"])
uplift_value = st.sidebar.number_input("Uplift Value", value=0.0, step=0.1)

# Filter data
filtered_df = df.copy()
if selected_branch != "All":
    filtered_df = filtered_df[filtered_df["Branch"] == selected_branch]
if selected_capability != "All":
    filtered_df = filtered_df[filtered_df["Capability"] == selected_capability]
if selected_team != "All":
    filtered_df = filtered_df[filtered_df["Department / Team"] == selected_team]
if selected_job != "All":
    filtered_df = filtered_df[filtered_df["Job Title"] == selected_job]

# Identify month columns
month_cols = [col for col in filtered_df.columns if isinstance(col, pd.Timestamp) or "202" in str(col)]

# Calculate new revenue ignoring headcount (billable days already includes it)
charge_rate_col = "Charge Rate Daily"
chargeability_start = month_cols.index(month_cols[0]) + len(month_cols) // 3
revenue_start = month_cols.index(month_cols[0]) + (len(month_cols) // 3) * 2

new_revenues = []
for idx, row in filtered_df.iterrows():
    charge_rate = row[charge_rate_col]
    if uplift_type == "Percentage (%)":
        charge_rate *= (1 + uplift_value / 100)
    else:
        charge_rate += uplift_value

    monthly_revenue = []
    for month in range(len(month_cols) // 3):
        billable_days = row[month_cols[month]]
        chargeability = row[month_cols[month + len(month_cols) // 3]]
        revenue = charge_rate * billable_days * chargeability
        monthly_revenue.append(revenue)
    new_revenues.append(monthly_revenue)

# Create a DataFrame for results
results_df = pd.DataFrame(new_revenues, columns=[f"Month {i+1}" for i in range(len(month_cols) // 3)])
results_df["Total Revenue"] = results_df.sum(axis=1)

# Show summary
st.subheader("💡 Uplifted Revenue Summary")
st.dataframe(results_df.style.format("${:,.0f}"))

st.subheader("📄 Detailed Data")
st.dataframe(filtered_df)
