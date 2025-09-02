import requests
import pytest


@pytest.mark.timeout(20)
def test_education_data_directory_query():
    # Query directory for University of Nevada to validate endpoint shape
    url = (
        "https://educationdata.urban.org/api/v1/colleges/ipeds/directory/2022/institution"
        "?name=nevada"
        "&page=1"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    # Expected keys: results, count, next, previous
    assert isinstance(data, dict)
    assert "results" in data and isinstance(data["results"], list)
