import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# It's recommended to set your API keys as environment variables.
# Create a .env file in the root of the oz-doc-processor directory and add your keys like so:
# CENSUS_API_KEY=your_census_key
# FRED_API_KEY=your_fred_key
# GOOGLE_MAPS_API_KEY=your_google_maps_key

load_dotenv()

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
BLS_API_KEY = os.getenv("BLS_API_KEY")

def get_fips_code(latitude, longitude):
    """
    Gets the state and county FIPS code from latitude and longitude.
    """
    url = (
        "https://geo.fcc.gov/api/census/block/find"
        f"?latitude={latitude}&longitude={longitude}&format=json"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data and data.get('County') and data['County'].get('FIPS'):
            return data['County']['FIPS']
        return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching FIPS code: {e}")
        return None

def geocode_address(address):
    """
    Geocodes an address to get latitude, longitude, and other address components.
    """
    if not GOOGLE_MAPS_API_KEY:
        print("GOOGLE_MAPS_API_KEY not set.")
        return None

    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={requests.utils.quote(address)}&key={GOOGLE_MAPS_API_KEY}"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        data = r.json()

        if data.get("status") == "OK":
            results = data.get("results", [])
            if not results:
                return None
            
            location = results[0]["geometry"]["location"]
            address_components = results[0]["address_components"]
            lat = location["lat"]
            lng = location["lng"]
            
            fips_code = get_fips_code(lat, lng)

            county = None
            state = None
            
            for component in address_components:
                if "administrative_area_level_2" in component["types"]:
                    county = component["long_name"]
                if "administrative_area_level_1" in component["types"]:
                    state = component["short_name"]

            return {
                "latitude": lat,
                "longitude": lng,
                "county": county,
                "state": state,
                "fips": fips_code,
            }
        else:
            print(f"Geocoding API error: {data.get('status')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def get_census_data(fips_code):
    """
    Gets demographic data from the Census Bureau.
    """
    if not CENSUS_API_KEY:
        print("CENSUS_API_KEY not set.")
        return None

    state_fips = fips_code[:2]
    county_fips = fips_code[2:]

    # Variables from census_api_capabilities.md
    variables = [
        "NAME",
        "B01003_001E",  # Total population
        "B19013_001E",  # Median household income
        "B01001_010E", "B01001_011E", "B01001_012E", "B01001_013E", "B01001_014E", 
        "B01001_015E", "B01001_016E", "B01001_017E", "B01001_034E", "B01001_035E", 
        "B01001_036E", "B01001_037E", "B01001_038E", "B01001_039E", "B01001_040E", 
        "B01001_041E", # Age distribution
        "B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E", # Education
        "B25002_001E",  # Total Housing Units
        "B17001_002E",  # Poverty Status
    ]
    
    url = (
        "https://api.census.gov/data/2022/acs/acs5"
        f"?get={','.join(variables)}&for=county:{county_fips}&in=state:{state_fips}&key={CENSUS_API_KEY}"
    )

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if len(data) > 1:
            headers = data[0]
            values = data[1]
            return dict(zip(headers, values))
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching Census data: {e}")
        return None

def parse_census_data(census_data):
    """
    Parses the raw census data into a more readable format.
    """
    if not census_data:
        return None

    total_population = int(census_data.get("B01003_001E", 0))
    parsed = {
        "county_name": census_data.get("NAME"),
        "total_population": total_population,
        "median_household_income": int(census_data.get("B19013_001E", 0)),
        "total_housing_units": int(census_data.get("B25002_001E", 0)),
        "population_below_poverty_level": int(census_data.get("B17001_002E", 0)),
    }

    # Age distribution
    age_25_34 = int(census_data.get("B01001_010E", 0)) + int(census_data.get("B01001_011E", 0)) + int(census_data.get("B01001_034E", 0)) + int(census_data.get("B01001_035E", 0))
    age_35_44 = int(census_data.get("B01001_012E", 0)) + int(census_data.get("B01001_013E", 0)) + int(census_data.get("B01001_036E", 0)) + int(census_data.get("B01001_037E", 0))
    age_45_54 = int(census_data.get("B01001_014E", 0)) + int(census_data.get("B01001_015E", 0)) + int(census_data.get("B01001_038E", 0)) + int(census_data.get("B01001_039E", 0))
    age_55_64 = int(census_data.get("B01001_016E", 0)) + int(census_data.get("B01001_017E", 0)) + int(census_data.get("B01001_040E", 0)) + int(census_data.get("B01001_041E", 0))
    
    if total_population > 0:
        age_dist_percent = {
            "25-34": round((age_25_34 / total_population) * 100, 2),
            "35-44": round((age_35_44 / total_population) * 100, 2),
            "45-54": round((age_45_54 / total_population) * 100, 2),
            "55-64": round((age_55_64 / total_population) * 100, 2),
        }
    else:
        age_dist_percent = {}

    parsed["age_distribution"] = {
        "counts": {
            "25-34": age_25_34,
            "35-44": age_35_44,
            "45-54": age_45_54,
            "55-64": age_55_64,
        },
        "percentages": age_dist_percent
    }

    # Education
    bachelors = int(census_data.get("B15003_022E", 0))
    masters = int(census_data.get("B15003_023E", 0))
    professional = int(census_data.get("B15003_024E", 0))
    doctorate = int(census_data.get("B15003_025E", 0))
    parsed["education"] = {
        "bachelors": bachelors,
        "masters": masters,
        "professional": professional,
        "doctorate": doctorate,
        "total_college_educated": bachelors + masters + professional + doctorate,
    }

    return parsed

def get_bls_data(fips_code):
    """
    Gets employment data from the Bureau of Labor Statistics.
    """
    if not BLS_API_KEY:
        print("BLS_API_KEY not set. Get one from https://data.bls.gov/registrationEngine/")
        return None
    
    state_fips = fips_code[:2]
    county_fips = fips_code[2:]
    
    # Series ID for Employed Persons, which we can use to calculate job growth.
    series_id = f"LAUCN{state_fips}{county_fips}000000000006" # Use Civilian Labor Force
    
    api_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    
    payload = {
        "seriesid": [series_id],
        "startyear": str(datetime.now().year - 5),
        "endyear": str(datetime.now().year),
        "registrationkey": BLS_API_KEY
    }
    
    try:
        r = requests.post(api_url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching BLS data: {e}")
        return None

def parse_bls_data(bls_data):
    """
    Parses the raw BLS data to calculate job growth.
    """
    if not bls_data or bls_data.get("status") != "REQUEST_SUCCEEDED":
        return None

    series = bls_data.get("Results", {}).get("series", [])
    if not series:
        return None

    data_points = series[0].get("data", [])
    if len(data_points) < 13:
        return {"job_growth_percentage": 0, "message": "Not enough data for year-over-year comparison."}

    # Sort data by year and period to ensure correct order
    data_points.sort(key=lambda x: (x['year'], x['period']))
    
    latest_data = data_points[-1]
    previous_data = data_points[-13]

    if latest_data and previous_data:
        latest_value = int(latest_data['value'])
        previous_value = int(previous_data['value'])
        
        if previous_value == 0:
            growth_percentage = float('inf') # Avoid division by zero
        else:
            growth_percentage = ((latest_value - previous_value) / previous_value) * 100
        
        return {
            "latest_month_labor_force": latest_value,
            "previous_year_month_labor_force": previous_value,
            "labor_force_growth_percentage": round(growth_percentage, 2)
        }
    return None

def get_fred_data(fips_code):
    """
    Gets economic data from the Federal Reserve Economic Data.
    """
    if not FRED_API_KEY:
        print("FRED_API_KEY not set.")
        return None
        
    series_id = f"GDPALL{fips_code}"
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching FRED data: {e}")
        return None

def parse_fred_data(fred_data):
    """
    Parses the raw FRED data to get the latest GDP value and calculate year-over-year growth.
    """
    if not fred_data or not fred_data.get("observations"):
        return None
        
    observations = fred_data.get("observations", [])
    if len(observations) < 2:
        return { "message": "Not enough data for year-over-year comparison." }
        
    latest_observation = observations[-1]
    previous_observation = observations[-2]
    
    latest_gdp = float(latest_observation['value'])
    previous_gdp = float(previous_observation['value'])

    if previous_gdp == 0:
        growth_percentage = float('inf')
    else:
        growth_percentage = ((latest_gdp - previous_gdp) / previous_gdp) * 100

    return {
        "latest_gdp_thousands": latest_gdp,
        "gdp_date": latest_observation['date'],
        "previous_gdp_thousands": previous_gdp,
        "previous_gdp_date": previous_observation['date'],
        "gdp_growth_percentage": round(growth_percentage, 2)
    }


def main():
    """
    Main function to orchestrate the data fetching process.
    """
    address = "1600 Amphitheatre Parkway, Mountain View, CA"  # Example address

    # 1. Geocode the address
    geocoded_data = geocode_address(address)
    print(json.dumps(geocoded_data, indent=4))

    if geocoded_data and geocoded_data.get("fips"):
        census_data = get_census_data(geocoded_data["fips"])
        
        parsed_census_data = parse_census_data(census_data)
        print("\n--- Parsed Census Data ---")
        print(json.dumps(parsed_census_data, indent=4))

        # 2. Get data from APIs
        bls_data = get_bls_data(geocoded_data["fips"])
        parsed_bls_data = parse_bls_data(bls_data)
        print("\n--- Parsed BLS Data ---")
        print(json.dumps(parsed_bls_data, indent=4))
        
        fred_data = get_fred_data(geocoded_data["fips"])
        parsed_fred_data = parse_fred_data(fred_data)
        print("\n--- Parsed FRED Data ---")
        print(json.dumps(parsed_fred_data, indent=4))


        # 3. Combine and store the data
        all_data = {
            "address": address,
            "geocoded": {
                "latitude": geocoded_data["latitude"],
                "longitude": geocoded_data["longitude"],
                "county": geocoded_data["county"],
                "state": geocoded_data["state"],
                "fips": geocoded_data["fips"],
            },
            "census": parsed_census_data,
            "bls": parsed_bls_data,
            "fred": parsed_fred_data,
        }

        with open("address_data.json", "w") as f:
            json.dump(all_data, f, indent=4)
        
        print("\nData successfully fetched and saved to address_data.json")

if __name__ == "__main__":
    main() 