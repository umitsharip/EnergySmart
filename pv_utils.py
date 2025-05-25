# pv_utils.py
import requests

GCP_API_KEY = "AIzaSyDXc2YBTobbyySrM-CgMpx5NvkMC3ZAPn0"

def get_geocode_from_zip(zip_code: str):
    """
    Given a ZIP code and Google Maps API key, returns the lat/lng and formatted address.
    
    Args:
        zip_code (str): The ZIP code to geocode.
        api_key (str): Your Google Maps API key.
    
    Returns:
        dict: Dictionary with 'lat', 'lng', and 'formatted_address' or None if not found.
    """
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": zip_code,
        "key": GCP_API_KEY
    }
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print(f"Request failed with status: {response.status_code}")
        return None

    data = response.json()
    if data["status"] != "OK" or not data["results"]:
        print(f"Geocoding failed: {data['status']}")
        return None

    location = data["results"][0]["geometry"]["location"]
    formatted_address = data["results"][0]["formatted_address"]
    return {
        "lat": location["lat"],
        "lng": location["lng"],
        "formatted_address": formatted_address
    }

def get_pv_generation(zip_code, system_kw, nrel_api_key):
    """
    Get estimated solar generation using PVWatts and Google Maps geocode.
    
    Args:
        zip_code (str): ZIP code of the location
        system_kw (float): Installed PV system size
        nrel_api_key (str): NREL PVWatts API key
    
    Returns:
        tuple: (monthly_kWh_list, annual_kWh_total, formatted_address)
    """
    geo = get_geocode_from_zip(zip_code)
    if geo is None:
        raise ValueError("Could not resolve ZIP to lat/lng")
    
    lat, lon = geo["lat"], geo["lng"]
    formatted_address = geo["formatted_address"]

    url = "https://developer.nrel.gov/api/pvwatts/v6.json"
    params = {
        "api_key": nrel_api_key,
        "system_capacity": system_kw,
        "module_type": 1, # standard
        "azimuth": 180, # typical
        "tilt": 20, # typical
        "array_type": 1, # fixed roof
        "losses": 14, # loss precent
        "lat": lat,
        "lon": lon,
    }
    r = requests.get(url, params=params)
    data = r.json()
    return data["outputs"]["ac_monthly"], data["outputs"]["ac_annual"], formatted_address