import os
import requests
import pytest
from google.api_core.client_options import ClientOptions
from google.maps import places_v1 as places
from google.maps.places_v1 import types as place_types
from google.type import latlng_pb2


GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
TEST_ADDRESS = os.getenv("TEST_ADDRESS", "1600 Amphitheatre Parkway, Mountain View, CA")


@pytest.mark.timeout(20)
@pytest.mark.skipif(not GOOGLE_KEY, reason="GOOGLE_MAPS_API_KEY not set")
def test_google_geocoding_minimal():
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={requests.utils.quote(TEST_ADDRESS)}&key={GOOGLE_KEY}"
    )
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data.get("status") in {"OK", "ZERO_RESULTS"}
    if data.get("status") == "OK":
        results = data.get("results", [])
        assert len(results) > 0
        loc = results[0]["geometry"]["location"]
        assert "lat" in loc and "lng" in loc


@pytest.mark.timeout(20)
@pytest.mark.skipif(not GOOGLE_KEY, reason="GOOGLE_MAPS_API_KEY not set")
def test_google_places_nearby_lenient():
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

    # Use Google Maps Places SDK (Places API New) for Nearby Search
    client = places.PlacesClient(client_options=ClientOptions(api_key=GOOGLE_KEY))

    # Build request using dicts for nested messages to avoid missing symbol issues
    request = place_types.SearchNearbyRequest(
        location_restriction={
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lng)},
                "radius": float(1500.0),
            }
        },
        included_types=["restaurant"],  # Use a broad, valid place type
        max_result_count=10,
        language_code="en",
    )

    # Places API (New) requires a response field mask; request a minimal set
    field_mask = "places.name,places.display_name"

    response = client.search_nearby(request=request, metadata=[("x-goog-fieldmask", field_mask)])
    # Response should contain places or be empty; both are acceptable for a lenient test
    assert response is not None
    places_container = getattr(response, "places", [])
    places_list = list(places_container) if places_container is not None else []
    # If results exist, validate a couple of basic fields commonly available
    if places_list:
        first = places_list[0]
        # name is the resource name (e.g., "places/PLACE_ID"); display_name is LocalizedText
        assert hasattr(first, "name") or hasattr(first, "display_name")
