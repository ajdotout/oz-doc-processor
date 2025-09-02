# OZ Doc Processor - API Testing Guide

This guide explains how to set up API credentials and run the smoke tests for external data sources used to auto-populate the Market Analysis page.

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`
- Network access to public APIs

## Environment Variables

Create a `.env` file at the repo root (`oz-doc-processor/.env`) and set keys as needed. Tests skip automatically if a required key is not present.

```
# Google Maps
GOOGLE_MAPS_API_KEY=
TEST_ADDRESS=1600 Amphitheatre Parkway, Mountain View, CA
TEST_LAT=36.1699
TEST_LNG=-115.1398

# BLS
BLS_API_KEY=

# FRED
FRED_API_KEY=
FRED_TEST_SERIES_ID=GDP

# ATTOM
ATTOM_API_KEY=
ATTOM_TEST_ADDRESS1=4529 Winona Court
ATTOM_TEST_ADDRESS2=Denver, CO
```

Notes:
- HUD Opportunity Zones test uses a public ArcGIS Feature Service and does not require a key.
- Census tests may already exist and not require keys for public endpoints.

## Installing Dependencies

```
pip install -r requirements.txt
```

## Running Tests

From the `oz-doc-processor/` directory:

```
pytest -q
```

Run a single test module:

```
pytest testing/test_google_maps_api.py -q
```

Increase verbosity and show skip reasons:

```
pytest -vv -ra
```

## Test Behavior

- Tests are designed as lightweight smoke checks that validate endpoint availability and response shapes.
- Tests that require API keys are skipped automatically if keys are missing.
- Google Places Nearby Search asserts a permissive status (`OK`, `ZERO_RESULTS`, or `OVER_QUERY_LIMIT`) to avoid false negatives.

## Troubleshooting

- Ensure keys are enabled for the relevant APIs (e.g., enable Geocoding/Places/Distance Matrix in Google Cloud Console).
- For BLS, confirm you are using the v2 endpoint with a valid registration key if provided.
- For FRED, validate the series ID on the FRED website before testing.
- For ATTOM, confirm that the account has access to the called endpoint.

## Next Steps

These smoke tests validate connectivity and basic shapes. For production, add parsing utilities to extract the specific fields required by sections like `marketMetrics`, `majorEmployers`, and `keyMarketDrivers`, and persist raw JSON for LLM context. 