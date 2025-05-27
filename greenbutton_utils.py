import xml.etree.ElementTree as ET
from io import BytesIO
import datetime as dt
import pandas as pd

def parse_green_button_xml(xml_bytes):
    """Return DataFrame with timestamp index and kWh column."""
    tree = ET.parse(BytesIO(xml_bytes))
    root = tree.getroot()

    ns = {"espi": "http://naesb.org/espi"}
    rows = []
    for reading in root.findall(".//espi:IntervalReading", ns):
        start = int(reading.find(".//espi:timePeriod/espi:start", ns).text)
        val   = int(reading.find("espi:value", ns).text)  # usually watt-hours
        rows.append({"timestamp": dt.datetime.utcfromtimestamp(start),
                     "kWh": val / 1000})                 # convert Wh→kWh

    return pd.DataFrame(rows).set_index("timestamp").sort_index()
