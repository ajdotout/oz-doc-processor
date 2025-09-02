import os
import json
import requests
import pytest


@pytest.mark.timeout(20)
def test_bls_timeseries_request_succeeds():
    api_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    api_key = os.getenv("BLS_API_KEY")

    # Unemployment rate (National) as a safe public series; replace/add MSA series later
    series_ids = ["LNS14000000"]

    payload = {"seriesid": series_ids}
    if api_key:
        payload["registrationkey"] = api_key

    r = requests.post(api_url, json=payload, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"

    data = r.json()
    assert data.get("status") == "REQUEST_SUCCEEDED", data
    assert "Results" in data and "series" in data["Results"], data
    series = data["Results"]["series"]
    assert isinstance(series, list) and len(series) >= 1
    first = series[0]
    assert first.get("seriesID") in series_ids
    assert isinstance(first.get("data"), list) and len(first["data"]) > 0
