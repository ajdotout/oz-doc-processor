import os
import requests
import pytest


@pytest.mark.timeout(25)
@pytest.mark.skipif(not os.getenv("ATTOM_API_KEY"), reason="ATTOM_API_KEY not set")
def test_attom_property_detail():
    api_key = os.getenv("ATTOM_API_KEY")
    address1 = os.getenv("ATTOM_TEST_ADDRESS1", "4529 Winona Court")
    address2 = os.getenv("ATTOM_TEST_ADDRESS2", "Denver, CO")
    url = (
        "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/detail"
        f"?address1={requests.utils.quote(address1)}&address2={requests.utils.quote(address2)}"
    )
    headers = {"accept": "application/json", "apikey": api_key}
    r = requests.get(url, headers=headers, timeout=20)
    assert r.status_code in (200, 206), f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
