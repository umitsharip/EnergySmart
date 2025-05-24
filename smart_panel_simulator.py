import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Smart Panel ROI Simulator", layout="wide")

# Sidebar summary
st.sidebar.header("Your Summary")
st.sidebar.metric("Est. Monthly Savings", "$62")
st.sidebar.metric("Payback Period", "18 months")
st.sidebar.metric("Yearly VPP Earnings", "$85")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Home Profile", "Utility Setup", "Smart Panel Outcomes", "Load Schedule", "Customize + Save"])

with tab1:
    st.header("Step 1: Tell us about your home")
    zip_code = st.text_input("ZIP Code", "90210")
    sqft = st.slider("Home Size (sqft)", 500, 5000, 1800)
    residents = st.selectbox("Number of Residents", [1, 2, 3, 4, "5+"])
    has_solar = st.radio("Do you have solar?", ["Yes", "No"])
    has_battery = st.radio("Do you have a battery?", ["Yes", "No"])
    devices = st.multiselect("Which energy-intensive devices do you use?", ["EV", "Heat Pump Water Heater", "Pool Pump", "A/C", "Washer/Dryer"])

with tab2:
    st.header("Step 2: Current Utility Setup")
    utility = st.selectbox("Your Utility Provider", ["PG&E", "SCE", "ConEd", "Other"])
    tariff = st.selectbox("Current Tariff Plan", ["Flat Rate", "TOU-A", "TOU-C", "Unknown"])
    bill = st.slider("Average Monthly Bill ($)", 50, 1000, 200)
    rate = st.number_input("Energy Rate ($/kWh, optional)", min_value=0.0, value=0.25, step=0.01)
    bill_upload = st.file_uploader("Upload Utility Bill (PDF)", type=["pdf"])

with tab3:
    st.header("Step 3: Smart Panel Benefits")
    col1, col2, col3 = st.columns(3)
    col1.metric("Est. Monthly Bill (Before)", "$200")
    col2.metric("Est. Monthly Bill (After)", "$138")
    col3.metric("Est. Annual Savings", "$744")

    col4, col5, col6 = st.columns(3)
    col4.metric("Payback Period", "18 months")
    col5.metric("VPP Earnings (yr)", "$85")
    col6.metric("Blackout Runtime", "8 hours")

    st.subheader("Estimated Peak Load Reduction")
    st.progress(0.45)

    st.subheader("CO₂ Avoided Annually")
    st.metric("Estimated Savings", "520 kg")

with tab4:
    st.header("Step 4: Load Schedule Optimization")
    st.caption("Below is a simulated daily schedule showing how smart panel shifts usage to save costs.")
    hours = list(range(24))
    usage_before = [np.random.randint(2, 8) if 17 <= h <= 21 else np.random.randint(1, 4) for h in hours]
    usage_after = [x - 1 if 17 <= h <= 21 else x + 0.5 for h, x in enumerate(usage_before)]
    df = pd.DataFrame({"Hour": hours, "Before Smart Panel": usage_before, "After Smart Panel": usage_after})
    df_melt = df.melt("Hour", var_name="Scenario", value_name="kWh Used")

    chart = alt.Chart(df_melt).mark_line(point=True).encode(
        x="Hour",
        y="kWh Used",
        color="Scenario"
    ).properties(width=700, height=400)

    st.altair_chart(chart)

with tab5:
    st.header("Step 5: Customize and Save")
    budget_cap = st.number_input("Monthly Budget Cap ($)", value=150)
    critical_loads = st.multiselect("Which loads should stay on during blackouts?", ["Fridge", "Wi-Fi", "Lighting", "Medical Devices"])
    goal = st.radio("Your Priority", ["Lower Bills", "Resilience", "Max ROI"])
    st.download_button("Download My Smart Panel Plan (PDF)", data="Simulated PDF output", file_name="smart_panel_plan.pdf")

    st.success("Your plan is ready! You can share this with your installer.")
