# HUD Opportunity Zones API Integration Guide

This document provides essential information for integrating with the HUD Opportunity Zones API, based on the testing and exploration conducted in this chat. It covers the API endpoint, data freshness, key fields, response structure, and an example of the parsed output.

## 1. API Endpoint

The primary API endpoint for accessing comprehensive HUD Opportunity Zones data is:

`https://services.arcgis.com/AgwDJMQH12AGieWa/ArcGIS/rest/services/Opportunity_Zone_Index_FS/FeatureServer/0/query`

### Query Parameters:

*   `f=json`: Specifies the response format as JSON.
*   `geometryType=esriGeometryPoint`: Defines the geometry type for the query (point).
*   `geometry={'x':<longitude>,'y':<latitude>}`: Specifies the latitude and longitude for the query.
*   `inSR=4326`: Sets the input spatial reference to WGS84.
*   `spatialRel=esriSpatialRelIntersects`: Specifies the spatial relationship for the query (intersects).
*   `returnGeometry=false`: Excludes geometry from the response.
*   `outFields`: A comma-separated list of fields to be returned. The selected fields and their aliases are detailed below.

## 2. Data Freshness

The data available through this API endpoint is more recent than 2018. While many field names retain a "2018_Values" prefix, the actual data points, such as "2023 Median Household Income" and "2023 Median Home Value," are updated.

Metadata Update Date: **March 1, 2024** (as per `catalog.data.gov`)
Data Last Modified Date: **August 9, 2023** (as per `catalog.data.gov`)

## 3. Key Fields and Aliases

Below are the important fields retrieved from the API, along with their aliases for easier understanding and usage in an automated system:

| Field Name                           | Alias                                     | Description                                          |
| :----------------------------------- | :---------------------------------------- | :--------------------------------------------------- |
| `OZ_2018_Values_Census_Tract_Qua`    | GEOID                                     | Census Tract GEOID for OZ identification             |
| `OZ_2018_Values_Census_Tract_Q_1`    | State                                     | State Name                                           |
| `OZ_2018_Values_Census_Tract_Q_2`    | County                                    | County Name                                          |
| `OZ_2018_Values_populationtotals`    | 2018-2023 Growth/Yr: Population           | Population growth rate between 2018 and 2023         |
| `OZ_2018_Values_keyusfacts_tothh`    | 2018 Total Households                     | Total number of households in 2018                   |
| `OZ_2018_Values_retailmarketplac`    | Total Retail:Sales                        | Total retail sales                                   |
| `OZ_2018_Values_industrybynaicsc`    | Retail Trade Sales ($000) (NAICS)         | Retail trade sales in thousands (NAICS)              |
| `OZ_2018_Values_gender_medage_cy`    | 2018 Median Age                           | Median age in 2018                                   |
| `OZ_2018_Values_householdincome_`    | 2018 Median Household Income              | Median household income in 2018                      |
| `OZ_2018_Values_wealth_medval_cy`    | 2018 Median Home Value                    | Median home value in 2018                            |
| `OZ_2018_Values_householdincome1`    | 2023 Median Household Income              | Median household income in 2023                      |
| `OZ_2018_Values_wealth_medval_fy`    | 2023 Median Home Value                    | Median home value in 2023                            |
| `OZ_2018_Values_educationalattai`    | 2018 Education: Bachelor's Degree: Percent| Percentage of population with Bachelor's Degree in 2018 |
| `OZ_2018_Values_industry_unemprt`    | 2018 Unemployment Rate                    | Unemployment rate in 2018                            |
| `OZ_2018_Values_populationtota_1`    | 2018 Total Population                     | Total population in 2018                             |
| `OZ_2018_Values_businesses_n01_b`    | Total Businesses (NAICS)                  | Total number of businesses (NAICS)                   |
| `OZ_2018_Values_employees_n01_em`    | Total Employees (NAICS)                   | Total number of employees (NAICS)                    |
| `OZ_2018_Values_raceandhispanico`    | 2018 Minority Population: Percent         | Percentage of minority population in 2018            |
| `Location`                           | County and State                          | Combined County and State information                |
| `OZRanks_ExcelToTableUpdated_N_3`    | Rank                                      | Opportunity Zone Rank                                |

## 4. Response Structure

The API returns a JSON object with the following key elements:

*   **`objectIdFieldName`**: The name of the field serving as the unique object identifier (e.g., `OBJECTID`).
*   **`uniqueIdField`**: Details about the unique ID field.
*   **`globalIdFieldName`**: The name of the global unique identifier field, if present.
*   **`geometryType`**: The geometric representation of the features (e.g., `esriGeometryPolygon`).
*   **`spatialReference`**: Information about the coordinate system used.
*   **`fields`**: A list of objects, each describing a field available in the dataset, including its `name`, `type`, `alias`, `length`, `domain`, and `defaultValue`.
*   **`features`**: A list of Opportunity Zone objects. Each object has:
    *   **`attributes`**: A key-value pair object containing the requested data for a specific Opportunity Zone. The keys are the field names (e.g., `OZ_2018_Values_Census_Tract_Qua`, `Location`), and the values are the corresponding data.

### Example of `attributes` Object (partial):

```json
{
  "OZ_2018_Values_Census_Tract_Qua": "32003000700",
  "OZ_2018_Values_Census_Tract_Q_1": "Nevada",
  "OZ_2018_Values_Census_Tract_Q_2": "Clark",
  "OZ_2018_Values_populationtotals": 1.27,
  "OZ_2018_Values_householdincome1": 17427,
  "Location": "Clark County, Nevada",
  "OZRanks_ExcelToTableUpdated_N_3": 3853
}
```

## 5. Example Usage (Python)

To retrieve and parse this data, you can use a Python script similar to the `test_hud_api.py` we developed:

```python
import os
import requests
import json

def get_hud_opportunity_zone_data(lat, lng):
    url = (
        "https://services.arcgis.com/AgwDJMQH12AGieWa/ArcGIS/rest/services/"
        "Opportunity_Zone_Index_FS/FeatureServer/0/query"
        "?f=json"
        "&geometryType=esriGeometryPoint"
        f"&geometry={{'x':{lng},'y':{lat}}}"
        "&inSR=4326"
        "&spatialRel=esriSpatialRelIntersects"
        "&returnGeometry=false"
        "&outFields=OZ_2018_Values_Census_Tract_Qua,OZ_2018_Values_Census_Tract_Q_1,OZ_2018_Values_Census_Tract_Q_2,OZ_2018_Values_Census_Tract_Q_3,OZ_2018_Values_populationtotals,OZ_2018_Values_keyusfacts_tothh,OZ_2018_Values_retailmarketplac,OZ_2018_Values_industrybynaicsc,OZ_2018_Values_gender_medage_cy,OZ_2018_Values_householdincome_,OZ_2018_Values_wealth_medval_cy,OZ_2018_Values_householdincome1,OZ_2018_Values_wealth_medval_fy,OZ_2018_Values_educationalattai,OZ_2018_Values_industry_unemprt,OZ_2018_Values_populationtota_1,OZ_2018_Values_businesses_n01_b,OZ_2018_Values_employees_n01_em,OZ_2018_Values_raceandhispanico,Location,OZRanks_ExcelToTableUpdated_N_3"
    )

    r = requests.get(url, timeout=20)
    r.raise_for_status() # Raise an exception for HTTP errors
    data = r.json()

    if data["features"]:
        attributes = data["features"][0]["attributes"]
        print(f"GEOID: {attributes.get('OZ_2018_Values_Census_Tract_Qua')}")
        print(f"State: {attributes.get('OZ_2018_Values_Census_Tract_Q_1')}")
        print(f"County: {attributes.get('OZ_2018_Values_Census_Tract_Q_2')}")
        print(f"Location (County and State): {attributes.get('Location')}")
        print(f"OZ Rank: {attributes.get('OZRanks_ExcelToTableUpdated_N_3')}")
        print(f"2023 Median Household Income: {attributes.get('OZ_2018_Values_householdincome1')}")
        # ... print other desired fields ...
        return attributes
    else:
        print("No Opportunity Zone found at this location")
        return None

if __name__ == "__main__":
    test_lat = float(os.getenv("TEST_LATITUDE", "36.1699"))
    test_lng = float(os.getenv("TEST_LONGITUDE", "-115.1398"))
    get_hud_opportunity_zone_data(test_lat, test_lng)
``` 