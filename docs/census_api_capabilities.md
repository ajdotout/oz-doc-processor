# Census API Capabilities

Based on the `test_census_api.py` script and successful test runs, the following data can be reliably fetched from the US Census Bureau API:

1.  **Population Data:** Total population for a given county (variable: `B01003_001E`).
2.  **Income Data:** Median household income for a given county (variable: `B19013_001E`).
3.  **Age Distribution Data:** Population counts for specific age groups (25-34, 35-44, 45-54, 55-64) for a given county. These are derived from variables like `B01001_010E` through `B01001_017E` (Male) and `B01001_034E` through `B01001_041E` (Female).
4.  **Education Data:** Population counts for various educational attainment levels (Bachelor's, Master's, Professional, Doctorate degrees) and the total college-educated population for a given county. These are derived from variables like `B15003_022E` through `B15003_025E`.
5.  **Housing Data:** Total Housing Units for a given county (variable: `B25002_001E`).
6.  **Poverty Data:** Population below the poverty level for a given county (variable: `B17001_002E`).

**Note:** Employment-related variables (specifically the `B24050` series) consistently caused a 400 Client Error during testing and are therefore not reliably fetchable with the current setup. 

## Current Data Fetching and Parsing Schema

The current implementation in `test_census_api.py` fetches data from the US Census Bureau's American Community Survey (ACS) 5-Year Data. Specifically, it targets the 2022 ACS 5-Year estimates.

### API Endpoint

All requests are made to the following base URL, with the year and survey specified:
`https://api.census.gov/data/2022/acs/acs5`

### Request Parameters

Each API request is constructed with the following parameters:

-   `get`: A comma-separated string of Census variable codes (e.g., `NAME,B01003_001E`). `NAME` is always requested to get the geographic area name.
-   `for`: Specifies the geographic level, typically `county:{COUNTY_FIPS}` (e.g., `county:037` for Los Angeles County).
-   `in`: Specifies the state for the county, typically `state:{STATE_FIPS}` (e.g., `state:06` for California).
-   `key`: The user's Census API key, loaded from environment variables.

Example `params` structure:
```python
params = {
    'get': 'NAME,B01003_001E',  # Total population
    'for': 'county:037',
    'in': 'state:06',
    'key': 'YOUR_API_KEY'
}
```

### Response Structure and Parsing

The API returns a JSON array. The first element of this array (`data[0]`) contains the headers (variable names), and subsequent elements (`data[1]` in our case for a single county) contain the corresponding data values.

Parsing involves:
1.  Making an HTTP GET request to the constructed URL.
2.  Checking for a 204 (No Content) status code, which indicates no data was returned for the query.
3.  Parsing the JSON response into a Python list of lists.
4.  Extracting headers from `data[0]` and the relevant county data from `data[1]`.
5.  Data values are typically strings and are converted to integers when performing calculations (e.g., summing age groups or college-educated populations) or for display formatting.

For example, to get the total population (`B01003_001E`):
```python
headers = data[0] # e.g., ['NAME', 'B01003_001E', 'state', 'county']
county_data = data[1] # e.g., ['Los Angeles County, California', '9936690', '06', '037']

# Find the index of 'B01003_001E' in headers and retrieve the corresponding value from county_data
population_index = headers.index('B01003_001E')
total_population = int(county_data[population_index])
```

For aggregated data like age distribution or education levels, individual variable values are summed up after converting them to integers.

**Error Handling:** The script includes basic error handling for `requests.exceptions.RequestException` (network issues, bad responses) and checks if `len(data) > 1` to ensure actual data is returned. 

### Census Variable Codes (B\*) Dictionary

The Census variable codes (e.g., `B01003_001E`) are specific identifiers for different data points within the Census Bureau's datasets. While not common knowledge, their meanings can be looked up on the official Census Bureau website. Here are the variables currently used in the `test_census_api.py` script and their descriptions:

*   `B01003_001E`: Total population
*   `B19013_001E`: Median household income
*   `B01001_010E`: Male 25-29
*   `B01001_011E`: Male 30-34
*   `B01001_012E`: Male 35-39
*   `B01001_013E`: Male 40-44
*   `B01001_014E`: Male 45-49
*   `B01001_015E`: Male 50-54
*   `B01001_016E`: Male 55-59
*   `B01001_017E`: Male 60-64
*   `B01001_034E`: Female 25-29
*   `B01001_035E`: Female 30-34
*   `B01001_036E`: Female 35-39
*   `B01001_037E`: Female 40-44
*   `B01001_038E`: Female 45-49
*   `B01001_039E`: Female 50-54
*   `B01001_040E`: Female 55-59
*   `B01001_041E`: Female 60-64
*   `B15003_022E`: Bachelor's degree
*   `B15003_023E`: Master's degree
*   `B15003_024E`: Professional degree
*   `B15003_025E`: Doctorate degree
*   `B25002_001E`: Total Housing Units
*   `B17001_002E`: Poverty Status in the Past 12 Months: Below poverty level 