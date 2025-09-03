import os
import requests
# import pytest # Removed pytest

# Removed pytest decorators
def test_hud_opportunity_zones_comprehensive_data():
    """Test fetching comprehensive HUD Opportunity Zones data for market analysis"""
    # Use Las Vegas coordinates (known OZ area)
    lat = float(os.getenv("TEST_LATITUDE", "36.1699"))
    lng = float(os.getenv("TEST_LONGITUDE", "-115.1398"))
    
    # Test comprehensive OZ data including economic metrics
    url = (
        "https://services.arcgis.com/AgwDJMQH12AGieWa/ArcGIS/rest/services/"
        "Opportunity_Zone_Index_FS/FeatureServer/0/query"
        "?f=json"
        "&geometryType=esriGeometryPoint"
        f"&geometry={{'x':{lng},'y':{lat}}}"
        "&inSR=4326"
        "&spatialRel=esriSpatialRelIntersects"
        "&returnGeometry=false"
        "&outFields="
        "OZ_2018_Values_Census_Tract_Qua,OZ_2018_Values_Census_Tract_Q_1,OZ_2018_Values_Census_Tract_Q_2,OZ_2018_Values_Census_Tract_Q_3,"
        "OZ_2018_Values_populationtotals,OZ_2018_Values_keyusfacts_tothh,OZ_2018_Values_retailmarketplac,"
        "OZ_2018_Values_industrybynaicsc,OZ_2018_Values_gender_medage_cy,OZ_2018_Values_householdincome_,"
        "OZ_2018_Values_wealth_medval_cy,OZ_2018_Values_householdincome1,OZ_2018_Values_wealth_medval_fy,"
        "OZ_2018_Values_educationalattai,OZ_2018_Values_industry_unemprt,OZ_2018_Values_populationtota_1,"
        "OZ_2018_Values_businesses_n01_b,OZ_2018_Values_employees_n01_em,OZ_2018_Values_raceandhispanico"
    )
    
    r = requests.get(url, timeout=20)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    
    # Check response structure
    assert "features" in data and isinstance(data["features"], list)
    
    if data["features"]:
        feature = data["features"][0]
        attributes = feature.get("attributes", {})
        
        # Print only essential identification data and a summary of fetched attributes
        print(f"OZ Data Retrieved for GEOID: {attributes.get('OZ_2018_Values_Census_Tract_Qua')}")
        print(f"  State: {attributes.get('OZ_2018_Values_Census_Tract_Q_1')}, County: {attributes.get('OZ_2018_Values_Census_Tract_Q_2')}")
        print(f"  Fetched {len(attributes)} attributes.")

        # Verify we have the key data fields for OZ identification and some economic metrics
        assert attributes.get('OZ_2018_Values_Census_Tract_Qua') is not None, "Missing GEOID for OZ identification"
        assert attributes.get('OZ_2018_Values_Census_Tract_Q_1') is not None, "Missing State for OZ identification"
        assert attributes.get('OZ_2018_Values_Census_Tract_Q_2') is not None, "Missing County for OZ identification"
        assert attributes.get('OZ_2018_Values_populationtotals') is not None, "Missing population totals data"
        assert attributes.get('OZ_2018_Values_householdincome1') is not None, "Missing 2023 median household income"
        
        return data
    else:
        print("No Opportunity Zone found at this location")
        return data

if __name__ == "__main__":
    test_hud_opportunity_zones_comprehensive_data()
