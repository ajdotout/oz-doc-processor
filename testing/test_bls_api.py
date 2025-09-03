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

if __name__ == "__main__":
    test_bls_timeseries_request_succeeds()
