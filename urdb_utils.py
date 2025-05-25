# urdb_utils.py
import requests
import pandas as pd
import datetime
import time

def get_filtered_urdb_tariffs_by_zip(zip_code, api_key, sector="Residential"):
    """
    Get URDB tariffs and filter/group by utility.

    Returns:
        dict: { utility_name: [ {name, rates, schedule, fixed_charge...}, ... ] }
    """
    url = "https://api.openei.org/utility_rates"
    params = {
        "version": 7,
        "format": "json",
        "api_key": api_key,
        "address": zip_code,
        "sector": sector,
        "detail": "full",
        "approved": "true",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RuntimeError(f"URDB API error: {e}")

    today_unix = int(time.time())
    grouped = {}

    for item in data.get("items", []):
        if "enddate" in item and item["enddate"] is not None:
            if int(item["enddate"]) < today_unix:
                continue

        utility = item.get("utility")
        if not utility:
            continue

        trimmed = {
            "name": item.get("name"),
            "energyratestructure": item.get("energyratestructure"),
            "energyweekdayschedule": item.get("energyweekdayschedule"),
            "energyweekendschedule": item.get("energyweekendschedule"),
            "fixedchargeunits": item.get("fixedchargeunits"),
            "fixedchargefirstmeter": item.get("fixedchargefirstmeter"),
        }

        if utility not in grouped:
            grouped[utility] = []

        grouped[utility].append(trimmed)

    return grouped

def get_urdb_tariffs_by_zip(zip_code, api_key, sector="Residential"):
    url = "https://api.openei.org/utility_rates"
    params = {
        "version": 7,
        "format": "json",
        "api_key": api_key,
        "address": zip_code,
        "sector": sector,
        "approved": "true",
        "detail": "full",
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "items" not in data:
        return pd.DataFrame(columns=["Utility", "Tariff Name", "Rate Type", "Fixed Charge", "Energy Rate", "TOU"])

    rows = []
    for item in data["items"]:
        rate_structure = item.get("energyratestructure", [{}])[0]
        rate = rate_structure.get("rate", ["N/A"])[0] if isinstance(rate_structure, dict) else "N/A"
        rows.append({
            "Utility": item.get("utility_name"),
            "Tariff Name": item.get("name"),
            "Rate Type": item.get("rate_type"),
            "Fixed Charge": item.get("fixedmonthlycharge"),
            "Energy Rate": rate,
            "TOU": "Yes" if item.get("tou") else "No"
        })

    return pd.DataFrame(rows)
