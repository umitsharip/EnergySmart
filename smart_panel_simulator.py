from io import BytesIO
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from urdb_utils import get_filtered_urdb_tariffs_by_zip
from collections import defaultdict
from pv_utils import get_pv_generation
from greenbutton_utils import parse_green_button_xml

API_KEY = "4YeTbE6dmhqqnxt1WeznbYXg5QztPjuRWw766e8D"
zip_code = "92694"

st.set_page_config(page_title="Smart Panel ROI Simulator", layout="wide")

home_done = st.session_state.get("home_profile_complete", False)
utility_done = st.session_state.get("utility_info_complete", False)
profile = st.session_state.get("home_profile", {})

# Sidebar summary
with st.sidebar:
    st.header("Your summary")
    # st.header("Potential Energy Smart Benefits")

    # Only show features after Tab 2 is complete
    # if utility_done:
    #     has_battery = profile.get("has_battery", False)

    #     st.subheader("🔓 Features Unlocked")
    #     st.markdown("- ✅ Dynamic Load Balancing")
    #     st.markdown("- ✅ Maximum EV Charging")
    #     st.markdown("- ✅ Avoid Expensive Panel Upgrade")
    #     st.markdown("- ✅ Real-Time Energy Monitor")
    #     st.markdown("- ✅ TOU Bill Optimization")
    #     st.markdown("- ✅ Solar Optimization")
    #     st.markdown("- ✅ Max-Bill Guardrail")

    #     if has_battery:
    #         st.markdown("- ✅ Outage assist – Critical Load Selection")
    #         st.markdown("- ✅ Outage assist – Battery Runtime Estimator")

    #     st.markdown("- ✅ Arc / Ground Fault Protection")

    # st.subheader("📊 Key Metrics")
    benefit_report = st.session_state.get("benefit_report", {})
    est_savings = benefit_report.get("monthly_savings", "--")
    payback     = benefit_report.get("payback_period", "--")
    vpp         = benefit_report.get("vpp_earnings", "--")

    st.metric("Est. Monthly Savings", f"~${est_savings}" if isinstance(est_savings, (int, float)) else est_savings)
    st.metric("Payback Period", f"~{payback} months" if isinstance(payback, (int, float)) else payback)
    st.metric("Yearly VPP Earnings", f"~${vpp}" if isinstance(vpp, (int, float)) else vpp)

# Tabs
tab1_label = "🏠 Home Profile" + (" ✅" if home_done else "")
tab2_label = "⚡ Utility Setup" + (" ✅" if utility_done else "")
tab3_label = "📉 Benefit Report"
tab4_label = "🧪 Deep Dive"
tab1, tab2, tab3, tab4 = st.tabs([tab1_label, tab2_label, tab3_label, tab4_label])

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

    st.markdown("🏠 **Home Details**")
    zip_code = st.text_input("ZIP Code", zip_code)
    sqft = st.slider("Home Size (sqft)", 500, 5000, 1800)
    residents = st.selectbox("Number of Residents", [1, 2, 3, 4, "5+"])

    # --- Solar System Details ---
    st.markdown("☀️ **Solar Panel Details**")
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
            monthly_generation = st.session_state.get("monthly_pv_gen", [])

    # --- Battery ---
    st.markdown("🔋 **Battery System Details**")
    has_battery = st.radio("Do you have a backup battery system?", ["No", "Yes"])
    battery_kw = 0
    battery_kwh = 0

    if has_battery == "Yes":
        battery_kw = st.number_input(
            "Continuous discharge rate (kW)", 
            min_value=1.0, max_value=30.0, value=10.0, step=0.5,
            help="How much power your battery can continuously supply"
        )
        battery_kwh = st.number_input(
            "Usable battery capacity (kWh)", 
            min_value=1.0, max_value=100.0, value=13.5, step=1.0,
            help="Total energy stored, e.g. 13.5 kWh for Tesla Powerwall"
        )

    # --- EV logic ---
    st.markdown("🚙 **EV Ownership details Details**")
    has_ev = st.radio("Do you own an Electric Vehicle?", ["No", "Yes"])
    num_evs = 0
    ev_weekly_miles = 0
    ev_monthly_kwh = 0

    if has_ev == "Yes":
        num_evs = st.number_input("How many EVs?", min_value=1, max_value=5, value=1, step=1)

        ev_weekly_miles = st.number_input(
            "What is your average total weekly driving distance? (miles)",
            min_value=0, value=150, step=10
        )

        ev_monthly_kwh = round((ev_weekly_miles * 4.3) / 3, 1)  # 4.3 weeks/month, 3 mi/kWh

        st.caption(f"🔋 Estimated EV energy usage (estimated EV efficiency 3 miles/kWh): **{ev_monthly_kwh} kWh/month**")

    # --- Other devices ---
    st.markdown("🔌 **Major Loads**")
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
            "battery_kwh": battery_kwh if has_battery == "Yes" else 0,
            "has_ev": has_ev == "Yes",
            "num_evs": num_evs,
            "ev_weekly_miles": ev_weekly_miles,
            "ev_monthly_kwh": ev_monthly_kwh,
            "devices": devices
        }
        st.session_state["home_profile_complete"] = True
        st.success("✅ Home Profile Saved!")

with tab2:
    if not home_done:
        st.warning("🚧 Please complete your Home Profile first.")
    else:
        # Utility Setup UI
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

                    # --- Average Monthly Bill ---
                    avg_monthly_bill = st.number_input("What's your average electricity bill per month? ($)", min_value=0.0, value=100.0, step=10.0)

                    if st.button("Save Utility Info"):
                        st.session_state["utility_info"] = {
                            "utility": selected_utility,
                            "tariff": selected_plan,
                            "avg_monthly_bill": avg_monthly_bill
                        }
                        st.session_state["utility_info_complete"] = True
                        st.success("✅ Utility info saved.")

with tab3:
    if not utility_done:
        st.warning("🚧 Complete Utility Setup to access this section.")
    else:
        st.header("Step 3: Your Smart-Panel Benefit Report")

        profile   = st.session_state["home_profile"]
        utility   = st.session_state["utility_info"]
        base_bill = utility["avg_monthly_bill"]

        # ---------- % assumptions backed by public studies ----------
        pct_tou        = 0.15   # 15 % TOU shift, mid-range of 10-25 % :contentReference[oaicite:0]{index=0}
        pct_monitor    = 0.05   # 5 % behaviour drop (ENERGYSTAR smart-meter study 3-8 %) :contentReference[oaicite:1]{index=1}
        pct_batt_peak  = 0.07   # 7 % peak-shave midpoint 5-10 % :contentReference[oaicite:2]{index=2}
        pct_solar_opt  = 0.05   # 5 % extra self-use (NEM 3.0 optimiser, utility white-paper)
        pct_dynamic_ev = 0.00   # convenience feature – no direct bill line item here

        vpp_annual     = 100    # California DR/VPP typical $50-$150 :contentReference[oaicite:3]{index=3}
        hardware_cost  = 1800   # assumed installed retrofit kit cost ($)

        # ---------- Which savings apply? ----------
        total_pct = 0
        monetary  = []
        lifestyle = []
        safety    = []

        # ➜ Cost-cutting features (include % in **green bold**)
        monetary.append((f"TOU Bill Optimization (**<span style='color:green;font-weight:bold'>{int(pct_tou*100)} %</span>**)",
                         "Schedules flexible loads (EV, HPWH, pool) into off-peak windows."))

        monetary.append((f"Real-Time Energy Monitor (**<span style='color:green;font-weight:bold'>{int(pct_monitor*100)} %</span>**)",
                         "Live $/hr cost nudges smarter behaviour."))

        monetary.append(("Tariff Advisor",
                         "Every month the panel analyses your usage and recommends the cheapest plan available."))

        monetary.append(("Avoid Panel-Upgrade (Dynamic Load Balancing)",
                         "Staggers big appliances so the main breaker never overloads — avoids a $3-5 k panel upsizing."))

        if profile["has_solar"]:
            monetary.append((f"Solar Export Optimizer (NEM 3.0) (**<span style='color:green;font-weight:bold'>{int(pct_solar_opt*100)} %</span>**)",
                             "Uses midday surplus to charge EV / battery, slashing low-value exports."))

        if profile["has_battery"]:
            monetary.append((f"Battery Peak Shaving (**<span style='color:green;font-weight:bold'>{int(pct_batt_peak*100)} %</span>**)",
                             "Discharges for the 3-4 priciest hours each day."))
            safety.append(("Outage assist – Critical-Load Selection",
                           "Choose which breakers stay powered when the grid goes down."))
            safety.append(("Outage assist – Battery Runtime Estimator",
                           f"Based on your {profile['battery_kwh']} kWh pack, shows remaining backup hours."))

        monetary.append((f"VPP Revenue Toggle (**<span style='color:green;font-weight:bold'>${vpp_annual}/yr</span>**)",
                        "Opt-in to utility demand-response events."))

        if profile["has_ev"]:
            lifestyle.append(("Dynamic EV Charge Speed",
                              "Auto-ramps amps up when the house is quiet, finishes faster without trips."))

        safety.extend([
            ("Arc / Ground-Fault Protection", "High-frequency DSP catches wiring faults in <50 ms."),
            ("Millisecond Islanding", "Keeps lights on during a blackout without a clunky transfer switch.")
        ])

        # ---------- Display feature sections ----------
        def section(title, items):
            if items:
                st.subheader(title)
                for name, desc in items:
                    st.markdown(f"**• {name}**  \n{desc}", unsafe_allow_html=True)

        section("💵 Cost-Cutting & Earnings Estimates", monetary)
        section("🛋️  Comfort & Convenience", lifestyle)
        section("🛡️  Safety & Resilience", safety)

        st.markdown("---")

        st.write("Click to run the estimate:")

        if st.button("💰 Estimate my savings"):
            # ---------- % assumptions ----------
            profile   = st.session_state["home_profile"]
            utility   = st.session_state["utility_info"]
            base_bill = utility["avg_monthly_bill"]

            # ---------- Savings math ----------
            total_pct = pct_tou + pct_monitor
            if profile["has_battery"]: total_pct += pct_batt_peak
            if profile["has_solar"]:   total_pct += pct_solar_opt

            monthly_savings = round(base_bill * total_pct, 2)
            after_bill      = round(base_bill - monthly_savings, 2)
            payback_months  = round(hardware_cost / (monthly_savings + vpp_annual/12), 1)

            # ---------- Headline metrics ----------
            st.markdown("### Results")
            col1, col2, col3 = st.columns(3)
            col1.metric("Monthly Bill (Before)", f"${base_bill}")
            col2.metric("Monthly Bill (After)", f"~${after_bill}")
            col3.metric("Monthly Estimated Savings", f"~${monthly_savings}")

            col4, col5, col6 = st.columns(3)
            col4.metric("Payback Period", f"~{payback_months} months")
            col5.metric("VPP Earnings", f"~${vpp_annual}/yr")
            col6.metric("Annual Savings", f"~${round(monthly_savings*12+vpp_annual,0)}")

            # ---------- Save for sidebar ----------
            st.session_state["benefit_report"] = {
                "monthly_savings": monthly_savings,
                "payback_period":  payback_months,
                "vpp_earnings":    vpp_annual
            }

            st.success("Estimated savings!")

with tab4:
    if not utility_done:
        st.warning("🚧 Complete Utility Setup to access this section.")
    else:
        st.header("Step 4: Deep Dive — Real Usage Analysis (California only)")
        st.info("⚠️ Detailed bill modelling currently supports CA utilities that provide "
                "Green Button ‘Download My Data’ XML files.")

        # -------- Upload or sample file ----------
        gb_file = st.file_uploader("Upload your Green Button XML", type=("xml",))
        sample_link = ("https://s3-us-west-2.amazonaws.com/"
                       "technical.greenbuttonalliance.org/library/sample-data/"
                       "Coastal_Multi_Family_Jan_1_2011_to_Jan_1_2012_RetailCustomer_5.xml")

        if gb_file is None:
            if st.button("🔍 Load sample data"):
                import requests, tempfile, os
                r = requests.get(sample_link, timeout=10)
                if r.ok:
                    gb_file = BytesIO(r.content)
                    st.success("Sample loaded.")
                else:
                    st.error("Failed to fetch sample.")

        if gb_file:
            try:
                df = parse_green_button_xml(gb_file.read())
            except Exception as e:
                st.error(f"Could not parse XML: {e}")
                st.stop()

            # --------- Basic stats ----------
            annual_kwh = round(df["kWh"].sum(), 1)
            daily_avg  = round(df["kWh"].resample("D").sum().mean(), 2)
            st.success(f"{len(df):,} intervals • {annual_kwh} kWh/yr • ~{daily_avg} kWh/day")

            # --------- Plot average daily profile ----------
            daily_shape = df.groupby(df.index.hour)["kWh"].mean().reset_index()
            st.altair_chart(
                alt.Chart(daily_shape).mark_area().encode(
                    x=alt.X("timestamp:O", title="Hour"),
                    y=alt.Y("kWh:Q", title="Avg kWh")
                ).properties(width=650, height=280), use_container_width=True)

            # --------- Peak vs. off-peak split ----------
            plan = st.session_state["utility_info"]["tariff"]
            weekday_sched = plan["energyweekdayschedule"][0]  # list of 24 ints
            peak_tier     = max(weekday_sched)
            peak_hours    = [h for h, t in enumerate(weekday_sched) if t == peak_tier]

            df["is_peak"] = df.index.hour.isin(peak_hours)
            peak_kwh  = df[df.is_peak]["kWh"].sum()
            off_kwh   = df[~df.is_peak]["kWh"].sum()
            st.write(f"**Load split:** {peak_kwh/annual_kwh:.1%} peak • {off_kwh/annual_kwh:.1%} off-peak")

            # --------- Quick cost-before vs cost-after demo ----------
            peak_rate = plan["energyratestructure"][peak_tier][0]["rate"]
            off_rate  = plan["energyratestructure"][min(weekday_sched)][0]["rate"]
            cost_today = peak_kwh*peak_rate + off_kwh*off_rate

            shifted_kwh = peak_kwh * 0.40   # assume 40 % shift
            new_peak_kwh = peak_kwh - shifted_kwh
            new_off_kwh  = off_kwh + shifted_kwh
            cost_after   = new_peak_kwh*peak_rate + new_off_kwh*off_rate

            st.metric("Annual Cost (today)",     f"${cost_today:,.0f}")
            st.metric("Projected Cost (Smart Panel)", f"${cost_after:,.0f}",
                      delta=f"-${cost_today - cost_after:,.0f}")

            # ---------- Tariff recommendation mock ----------
            st.divider()
            st.subheader("Tariff Recommendation (demo)")
            st.write("Based on your 8760-hour profile we scanned 45 residential tariffs "
                     "in your ZIP and found **EV-TOU-5** would shave another **$120 / yr** "
                     "if EV charging stays off-peak.")

