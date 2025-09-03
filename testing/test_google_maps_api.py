import os
import requests
import pytest
from google.api_core.client_options import ClientOptions
from google.maps import places_v1 as places
from google.maps.places_v1 import types as place_types
from google.type import latlng_pb2
from dotenv import load_dotenv
import json

load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
TEST_ADDRESS = os.getenv("TEST_ADDRESS", "1600 Amphitheatre Parkway, Mountain View, CA")


@pytest.mark.timeout(20)
@pytest.mark.skipif(not GOOGLE_KEY, reason="GOOGLE_MAPS_API_KEY not set")
def test_google_geocoding_minimal():
    print(f"--- Google Geocoding Test ---")
    print(f"Using TEST_ADDRESS: {TEST_ADDRESS}")
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={requests.utils.quote(TEST_ADDRESS)}&key={GOOGLE_KEY}"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    print(json.dumps(data, indent=4))
    assert data.get("status") in {"OK", "ZERO_RESULTS"}
    if data.get("status") == "OK":
        results = data.get("results", [])
        assert len(results) > 0
        loc = results[0]["geometry"]["location"]
        assert "lat" in loc and "lng" in loc


@pytest.mark.timeout(20)
@pytest.mark.skipif(not GOOGLE_KEY, reason="GOOGLE_MAPS_API_KEY not set")
def test_google_places_nearby_lenient():
    print(f"\n--- Google Places Nearby Search Test ---")
    print(f"Using TEST_ADDRESS for geocoding: {TEST_ADDRESS}")
    # Use geocoded coords to seed a modest nearby search (kept lenient re: ZERO_RESULTS)
    geocode_url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={requests.utils.quote(TEST_ADDRESS)}&key={GOOGLE_KEY}"
    )
    g = requests.get(geocode_url, timeout=15).json()
    if g.get("status") != "OK":
        pytest.skip("Geocode did not return OK; skipping nearby search")
    loc = g["results"][0]["geometry"]["location"]
    lat, lng = loc["lat"], loc["lng"]
    print(f"Geocoded location - Latitude: {lat}, Longitude: {lng}")

    # Use Google Maps Places SDK (Places API New) for Nearby Search
    client = places.PlacesClient(client_options=ClientOptions(api_key=GOOGLE_KEY))

    # Build request using dicts for nested messages to avoid missing symbol issues
    radius = float(os.getenv("GOOGLE_TEST_RADIUS", "1500.0"))
    included_types_str = os.getenv("GOOGLE_TEST_INCLUDED_TYPES", "restaurant")
    included_types = included_types_str.split(",")
    max_result_count = int(os.getenv("GOOGLE_TEST_MAX_RESULT_COUNT", "10"))
    language_code = os.getenv("GOOGLE_TEST_LANGUAGE_CODE", "en")

    print(f"Searching with Radius: {radius} meters")
    print(f"Included Types: {included_types}")
    print(f"Max Result Count: {max_result_count}")
    print(f"Language Code: {language_code}")

    request = place_types.SearchNearbyRequest(
        location_restriction={
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lng)},
                "radius": radius,
            }
        },
        included_types=included_types,  # Use a broad, valid place type
        max_result_count=max_result_count,
        language_code=language_code,
    )

    # Places API (New) requires a response field mask; request a minimal set
    field_mask = "places.name,places.display_name"

    response = client.search_nearby(request=request, metadata=[("x-goog-fieldmask", field_mask)])
    # Response should contain places or be empty; both are acceptable for a lenient test
    assert response is not None
    places_container = getattr(response, "places", [])
    places_list = list(places_container) if places_container is not None else []
    print(f"Google Places API Response: {json.dumps([p.display_name for p in places_list], indent=4) if places_list else 'No places found.'}")

    # If results exist, validate a couple of basic fields commonly available
    if places_list:
        first = places_list[0]
        # name is the resource name (e.g., "places/PLACE_ID"); display_name is LocalizedText
        assert hasattr(first, "name") or hasattr(first, "display_name")
