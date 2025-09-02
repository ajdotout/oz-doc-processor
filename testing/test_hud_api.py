import os
import requests
import pytest


@pytest.mark.timeout(20)
def test_hud_opportunity_zones_geometry_query():
    # Use a known coordinate in the US; override via env if desired
    lat = float(os.getenv("TEST_LAT", "36.1699"))
    lng = float(os.getenv("TEST_LNG", "-115.1398"))

    url = (
        "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Opportunity_Zones/FeatureServer/0/query"
        "?f=json"
        "&geometryType=esriGeometryPoint"
        f"&geometry={{'x':{lng},'y':{lat}}}"
        "&inSR=4326"
        "&spatialRel=esriSpatialRelIntersects"
        "&returnGeometry=false"
        "&outFields=GEOID,NAME,STATE,TRACTCE10"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "features" in data and isinstance(data["features"], list)
    # Can be zero if point not in an OZ; still a valid response
