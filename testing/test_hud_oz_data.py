import os
import requests
import pytest

@pytest.mark.timeout(20)
def test_hud_oz_data_query():
    # Use a known coordinate in the US; override via env if desired
    lat = float(os.getenv("TEST_LAT", "36.1699"))
    lng = float(os.getenv("TEST_LNG", "-115.1398"))

    url = (
        "https://services.arcgis.com/AgwDJMQH12AGieWa/ArcGIS/rest/services/Opportunity_Zone_Index_FS/FeatureServer/0/query"
        f"?geometry={lng},{lat}"
        "&geometryType=esriGeometryPoint"
        "&inSR=4326"
        "&spatialRel=esriSpatialRelIntersects"
        "&outFields=*"
        "&f=json"
    )

    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    assert "features" in data
    assert len(data["features"]) > 0
    
    attributes = data["features"][0]["attributes"]
    
    # Check for some of the expected data fields
    assert "OZ_2018_Values_populationtotals" in attributes
    assert "OZ_2018_Values_householdincome_" in attributes
    assert "OZ_2018_Values_wealth_medval_cy" in attributes
    assert "OZ_2018_Values_industry_unemprt" in attributes
    
    print("\n--- HUD OZ Data Fetched ---")
    for key, value in attributes.items():
        if "OZ_2018" in key:
            print(f"{key}: {value}")
    print("--------------------------")

