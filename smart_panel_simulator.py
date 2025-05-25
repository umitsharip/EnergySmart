import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from urdb_utils import get_filtered_urdb_tariffs_by_zip
from collections import defaultdict

st.set_page_config(page_title="Smart Panel ROI Simulator", layout="wide")

# Sidebar summary
st.sidebar.header("Your Summary")
st.sidebar.metric("Est. Monthly Savings", "$62")
st.sidebar.metric("Payback Period", "18 months")
st.sidebar.metric("Yearly VPP Earnings", "$85")

API_KEY = "4YeTbE6dmhqqnxt1WeznbYXg5QztPjuRWw766e8D"

GCP_API_KEY = "AIzaSyDXc2YBTobbyySrM-CgMpx5NvkMC3ZAPn0"

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Home Profile", "Utility Setup", "Smart Panel Outcomes", "Load Schedule", "Customize + Save"])

def hour_to_ampm(hour):
    """Convert 24h integer to 12h AM/PM format."""
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{hour12} {suffix}"

def collapse_schedule(schedule, rate_structure):
    """Collapse hourly schedule into ranges with same rate (12h format)."""
    if not schedule:
        return []

    hours = list(range(24))
    tier_sequence = schedule[0]
    ranges = []
    start = 0

    for i in range(1, len(hours)):
        if tier_sequence[i] != tier_sequence[start]:
            ranges.append((start, i-1, tier_sequence[start]))
            start = i
    ranges.append((start, 23, tier_sequence[start]))

    readable = []
    for start, end, tier in ranges:
        try:
            rate = rate_structure[tier][0].get("rate", "N/A")
        except:
            rate = "N/A"
        readable.append({
            "Hours": f"{hour_to_ampm(start)} – {hour_to_ampm(end + 1)}",
            "Rate ($/kWh)": rate
        })
    return readable

with tab1:
    st.header("Step 1: Tell us about your home")

    zip_code = st.text_input("ZIP Code", "90210")
    sqft = st.slider("Home Size (sqft)", 500, 5000, 1800)
    residents = st.selectbox("Number of Residents", [1, 2, 3, 4, "5+"])
    has_solar = st.radio("Do you have solar?", ["Yes", "No"])
    has_battery = st.radio("Do you have a battery?", ["Yes", "No"])

    # EV logic
    has_ev = st.radio("Do you own an Electric Vehicle?", ["No", "Yes"])
    if has_ev == "Yes":
        num_evs = st.number_input("How many EVs?", min_value=1, max_value=5, value=1, step=1)
    else:
        num_evs = 0

    # Adjusted multiselect without EV
    devices = st.multiselect(
        "Which other energy-intensive devices do you use?",
        ["Heat Pump Water Heater", "Pool Pump", "A/C", "Washer/Dryer"]
    )

with tab2:
    st.header("Step 2: Current Utility Setup")
    zip_code = st.text_input("Enter ZIP Code", "92694")
    api_key = API_KEY

    if "tariff_groups" not in st.session_state:
        st.session_state.tariff_groups = {}

    if st.button("Fetch Utility Tariffs"):
        try:
            st.session_state.tariff_groups = get_filtered_urdb_tariffs_by_zip(zip_code, api_key)
            st.success("Tariffs fetched successfully.")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.session_state.tariff_groups:
        utilities = [""] + list(st.session_state.tariff_groups.keys())
        selected_utility = st.selectbox("Select Utility Company", utilities)

        if selected_utility and selected_utility != "":
            plans = st.session_state.tariff_groups[selected_utility]
            plan_names = [plan["name"] for plan in plans]
            selected_plan_name = st.selectbox("Select Tariff Plan", [""] + plan_names)

            if selected_plan_name:
                selected_plan = next(p for p in plans if p["name"] == selected_plan_name)

                st.markdown(f"### Tariff Plan Overview: **{selected_plan['name']}**")
                st.write(f"**Fixed Monthly Charge:** {selected_plan['fixedchargefirstmeter']} {selected_plan['fixedchargeunits']}")

                weekday = selected_plan.get("energyweekdayschedule")
                weekend = selected_plan.get("energyweekendschedule")
                rates = selected_plan.get("energyratestructure")

                # Compare schedules; if same, collapse and show one
                if weekday == weekend:
                    st.markdown("#### Daily Rate Schedule")
                    collapsed = collapse_schedule(weekday, rates)
                    st.dataframe(pd.DataFrame(collapsed))
                else:
                    st.markdown("#### Weekday Rate Schedule")
                    st.dataframe(pd.DataFrame(collapse_schedule(weekday, rates)))
                    st.markdown("#### Weekend Rate Schedule")
                    st.dataframe(pd.DataFrame(collapse_schedule(weekend, rates)))

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
