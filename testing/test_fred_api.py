import os
import requests
# import pytest # Removed pytest
import json
from dotenv import load_dotenv

load_dotenv()


# Removed pytest decorators
def check_fred_series_exists(api_key, series_id):
    url = (
        "https://api.stlouisfed.org/fred/series/search"
        f"?search_text={series_id}&api_key={api_key}&file_type=json"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()  # Raise an exception for HTTP errors
    data = r.json()
    
    # Check if 'series' key exists and if any series in the list has a matching ID
    if "seriess" in data and isinstance(data["seriess"], list):
        for series in data["seriess"]:
            if series.get("id") == series_id:
                print(f"Series ID '{series_id}' exists.")
                return True
    print(f"Series ID '{series_id}' does not exist.")
    return False

def test_fred_county_gdp():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not set, skipping test_fred_county_gdp")
        return
    state_fips = os.getenv("TEST_STATE_FIPS")
    if not state_fips:
        print("TEST_STATE_FIPS not set, skipping test_fred_county_gdp")
        return
    county_fips = os.getenv("TEST_COUNTY_FIPS")
    if not county_fips:
        print("TEST_COUNTY_FIPS not set, skipping test_fred_county_gdp")
        return

    print(f"Using FRED_TEST_STATE_FIPS: {state_fips}")
    print(f"Using FRED_TEST_COUNTY_FIPS: {county_fips}")

    # Construct the series ID for Real Gross Domestic Product: All Industries by County
    series_id = f"REALGDPALL{state_fips}{county_fips}"

    if not check_fred_series_exists(api_key, series_id):
        print(f"Skipping data request for non-existent series: {series_id}")
        return

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    print(f"--- FRED GDP Data for Series ID: {series_id} ---")
    print(json.dumps(data, indent=4))
    assert "observations" in data and isinstance(data["observations"], list)
    assert len(data["observations"]) > 0

def test_fred_county_population():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not set, skipping test_fred_county_population")
        return
    state_fips = os.getenv("TEST_STATE_FIPS_POP")
    if not state_fips:
        print("TEST_STATE_FIPS_POP not set, skipping test_fred_county_population")
        return
    county_fips = os.getenv("TEST_COUNTY_FIPS_POP")
    if not county_fips:
        print("TEST_COUNTY_FIPS_POP not set, skipping test_fred_county_population")
        return

    print(f"Using FRED_TEST_STATE_FIPS_POP: {state_fips}")
    print(f"Using FRED_TEST_COUNTY_FIPS_POP: {county_fips}")

    # Construct the series ID for Resident Population
    # Based on search results, a common pattern is [STATE_FIPS][COUNTY_FIPS]POP
    series_id = f"{state_fips}{county_fips}POP"

    if not check_fred_series_exists(api_key, series_id):
        print(f"Skipping data request for non-existent series: {series_id}")
        return

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    print(f"--- FRED Population Data for Series ID: {series_id} ---")
    print(json.dumps(data, indent=4))
    assert "observations" in data and isinstance(data["observations"], list)
    assert len(data["observations"]) > 0


if __name__ == "__main__":
    test_fred_county_gdp()
    test_fred_county_population()
