import os
import requests
import pytest
import json
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.timeout(20)
@pytest.mark.skipif(not os.getenv("FRED_API_KEY"), reason="FRED_API_KEY not set")
def test_fred_county_gdp():
    api_key = os.getenv("FRED_API_KEY")
    state_fips = os.getenv("FRED_TEST_STATE_FIPS", "12")  # Default to Florida
    county_fips = os.getenv("FRED_TEST_COUNTY_FIPS", "001")  # Default to Alachua County

    print(f"Using FRED_TEST_STATE_FIPS: {state_fips}")
    print(f"Using FRED_TEST_COUNTY_FIPS: {county_fips}")

    # Construct the series ID for Real Gross Domestic Product: All Industries by County
    series_id = f"REALGDPALL{state_fips}{county_fips}"

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
