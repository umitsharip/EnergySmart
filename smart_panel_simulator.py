import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from urdb_utils import get_filtered_urdb_tariffs_by_zip
from collections import defaultdict
from pv_utils import get_pv_generation

st.set_page_config(page_title="Smart Panel ROI Simulator", layout="wide")

# Sidebar summary
st.sidebar.header("Your Summary")
st.sidebar.metric("Est. Monthly Savings", "$62")
st.sidebar.metric("Payback Period", "18 months")
st.sidebar.metric("Yearly VPP Earnings", "$85")

API_KEY = "4YeTbE6dmhqqnxt1WeznbYXg5QztPjuRWw766e8D"

zip_code = "92694"

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

    zip_code = st.text_input("ZIP Code", zip_code)
    sqft = st.slider("Home Size (sqft)", 500, 5000, 1800)
    residents = st.selectbox("Number of Residents", [1, 2, 3, 4, "5+"])

    # --- Solar System Details ---
    has_solar = st.radio("Do you have solar?", ["No", "Yes"])
    system_kw = 0
    monthly_generation = []

    if has_solar == "Yes":
        system_kw = st.number_input("What is your solar panel system capacity? (kW)", min_value=1.0, max_value=20.0, value=3.0, step=1.0)

        manual_or_auto = st.radio("How would you like to provide your monthly solar generation?", ["Estimate for me", "I'll type it"])

        if manual_or_auto == "I'll type it":
            user_estimate = st.number_input("Estimated monthly solar generation (kWh)", min_value=0.0, step=10.0)
            monthly_generation = [user_estimate] * 12
        else:
            pvwatts_api_key = API_KEY
            if st.button("Estimate via PVWatts"):
                if pvwatts_api_key:
                    try:
                        monthly_gen, annual_gen, address = get_pv_generation(zip_code, system_kw, pvwatts_api_key)
                        st.session_state["monthly_pv_gen"] = monthly_gen
                        st.success(address)
                        st.success(f"Estimated monthly generation: {round(sum(monthly_gen)/12, 1)} kWh/month")
                    except Exception as e:
                        st.error(f"Failed to get estimate: {e}")
                else:
                    st.warning("Please enter your PVWatts API key.")

            # if "monthly_pv_gen" in st.session_state:
            #     st.markdown("#### Estimated Monthly Solar Generation")
            #     st.bar_chart(pd.Series(st.session_state["monthly_pv_gen"], index=[
            #         "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            #     ]))
            #     monthly_generation = st.session_state["monthly_pv_gen"]

    # --- Battery ---
    has_battery = st.radio("Do you have a battery?", ["No", "Yes"])
    battery_kw = 0
    if has_battery == "Yes":
        battery_kw = st.number_input("What is your battery backup capacity? (kW)", min_value=1.0, max_value=30.0, value=10.0, step=0.5)

    # --- EV logic ---
    has_ev = st.radio("Do you own an Electric Vehicle?", ["No", "Yes"])
    num_evs = st.number_input("How many EVs?", min_value=1, max_value=5, value=1, step=1) if has_ev == "Yes" else 0

    # --- Other devices ---
    devices = st.multiselect(
        "Which other energy-intensive devices do you use?",
        ["Heat Pump Water Heater", "Pool Pump", "A/C", "Washer/Dryer"]
    )

    # --- Save everything ---
    if st.button("Save"):
        st.session_state["home_profile"] = {
            "zip_code": zip_code,
            "sqft": sqft,
            "residents": residents,
            "has_solar": has_solar == "Yes",
            "system_kw": system_kw if has_solar == "Yes" else 0,
            "monthly_pv_gen": monthly_generation,
            "has_battery": has_battery == "Yes",
            "battery_kw": battery_kw if has_battery == "Yes" else 0,
            "has_ev": has_ev == "Yes",
            "num_evs": num_evs,
            "devices": devices
        }
        st.session_state["home_profile_complete"] = True
        st.success("✅ Home Profile Saved!")

with tab2:
    st.header("Step 2: Current Utility Setup")
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
