import os
import requests
import pytest


@pytest.mark.timeout(20)
@pytest.mark.skipif(not os.getenv("FRED_API_KEY"), reason="FRED_API_KEY not set")
def test_fred_observations_gdp():
    api_key = os.getenv("FRED_API_KEY")
    series_id = os.getenv("FRED_TEST_SERIES_ID", "GDP")
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "observations" in data and isinstance(data["observations"], list)
    assert len(data["observations"]) > 0
