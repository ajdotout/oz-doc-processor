import os
import json
import requests
# import pytest # Removed pytest
from dotenv import load_dotenv

load_dotenv()


# Removed pytest decorators
def test_bls_timeseries_request_succeeds():
    api_url = os.getenv("BLS_API_URL", "https://api.bls.gov/publicAPI/v2/timeseries/data/")
    api_key = os.getenv("BLS_API_KEY")

    print(f"Using BLS_API_URL: {api_url}")
    print(f"Using BLS_API_KEY: {api_key}")

    state_fips = os.getenv("TEST_STATE_FIPS")
    county_fips = os.getenv("TEST_COUNTY_FIPS")
    if state_fips:
        print(f"Using TEST_STATE_FIPS: {state_fips}")
    if county_fips:
        print(f"Using TEST_COUNTY_FIPS: {county_fips}")

    # Unemployment rate (National) as a safe public series; replace/add MSA series later
    series_ids_str = os.getenv("BLS_TEST_SERIES_IDS", "LNS14000000")
    print(f"Using BLS_TEST_SERIES_IDS: {series_ids_str}")
    series_ids = series_ids_str.split(",")

    payload = {"seriesid": series_ids}
    if api_key:
        payload["registrationkey"] = api_key

    r = requests.post(api_url, json=payload, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"

    data = r.json()
    print(json.dumps(data, indent=4))
    assert data.get("status") == "REQUEST_SUCCEEDED", data
    assert "Results" in data and "series" in data["Results"], data
    series = data["Results"]["series"]
    assert isinstance(series, list) and len(series) >= 1
    first = series[0]
    assert first.get("seriesID") in series_ids
    assert isinstance(first.get("data"), list) and len(first["data"]) > 0

def test_bls_county_data_request_succeeds():
    api_url = os.getenv("BLS_API_URL", "https://api.bls.gov/publicAPI/v2/timeseries/data/")
    api_key = os.getenv("BLS_API_KEY")
    state_fips = os.getenv("TEST_STATE_FIPS")
    county_fips = os.getenv("TEST_COUNTY_FIPS")

    if not (state_fips and county_fips):
        print("Skipping county-level BLS test: TEST_STATE_FIPS or TEST_COUNTY_FIPS not set.")
        return

    # Construct the county-level series ID for Civilian Labor Force
    # Format: LAUCN[STATE_FIPS][COUNTY_FIPS]0000000000005 for Employed Persons (Not Seasonally Adjusted)
    # The '0000000000005' suffix is for 'Employed Persons' in the 'LAU' survey (Local Area Unemployment Statistics)
    # Other common suffixes for LAU are:
    # 03 for Unemployment Rate
    # 04 for Unemployed Persons
    # 06 for Civilian Labor Force
    
    # For now, we'll use 05 for Employed Persons as it's a common county-level series.
    county_series_id = f"LAUCN{state_fips}{county_fips}000000000005"
    print(f"Using county-level series ID: {county_series_id}")

    payload = {"seriesid": [county_series_id]}
    if api_key:
        payload["registrationkey"] = api_key

    r = requests.post(api_url, json=payload, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"

    data = r.json()
    print(json.dumps(data, indent=4))
    assert data.get("status") == "REQUEST_SUCCEEDED", data
    assert "Results" in data and "series" in data["Results"], data
    series = data["Results"]["series"]
    assert isinstance(series, list) and len(series) >= 1
    first = series[0]
    assert first.get("seriesID") == county_series_id
    assert isinstance(first.get("data"), list) and len(first["data"]) > 0

if __name__ == "__main__":
    # test_bls_timeseries_request_succeeds() # Commented out as user is not interested in national statistics
    test_bls_county_data_request_succeeds()
