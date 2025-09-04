import os
import requests
# import pytest # Removed pytest
from google.api_core.client_options import ClientOptions
from google.maps import places_v1 as places
from google.maps.places_v1 import types as place_types
from google.type import latlng_pb2
from dotenv import load_dotenv
import json
import math

load_dotenv()

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # distance in meters

GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
TEST_ADDRESS = os.getenv("TEST_ADDRESS", "1600 Amphitheatre Parkway, Mountain View, CA")
TEST_LATITUDE = os.getenv("TEST_LATITUDE", "37.4220656")
TEST_LONGITUDE = os.getenv("TEST_LONGITUDE", "-122.0840897")

# Removed pytest decorators
def test_google_geocoding_minimal():
    print(f"--- Google Geocoding Test ---")
    if not GOOGLE_KEY:
        print("GOOGLE_MAPS_API_KEY not set, skipping test_google_geocoding_minimal")
        return
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
        return loc["lat"], loc["lng"]
    return None, None


# Removed pytest decorators
def test_google_places_nearby_lenient(lat: float = None, lng: float = None):
    print(f"\n--- Google Places Nearby Search Test ---")
    if not GOOGLE_KEY:
        print("GOOGLE_MAPS_API_KEY not set, skipping test_google_places_nearby_lenient")
        return

    # Try to get coordinates from environment variables first
    env_lat = os.getenv("TEST_LATITUDE")
    env_lng = os.getenv("TEST_LONGITUDE")

    if env_lat and env_lng:
        lat = float(env_lat)
        lng = float(env_lng)
        print(f"Using coordinates from environment variables: Latitude: {lat}, Longitude: {lng}")
    else:
        print("TEST_LATITUDE or TEST_LONGITUDE not set in environment variables, attempting dynamic geocoding.")
        # Fallback to dynamic geocoding if env variables are empty
        geo_lat, geo_lng = test_google_geocoding_minimal()
        if geo_lat is not None and geo_lng is not None:
            lat = geo_lat
            lng = geo_lng
            print(f"Geocoding successful. Latitude: {lat}, Longitude: {lng}")
        else:
            print("Dynamic geocoding failed. Latitude or Longitude not available, skipping test_google_places_nearby_lenient.")
            return

    if lat is None or lng is None:
        print("Latitude or Longitude not provided, skipping test_google_places_nearby_lenient")
        return

    print(f"Using TEST_LATITUDE: {lat} and TEST_LONGITUDE: {lng}")

    # Use Google Maps Places SDK (Places API New) for Nearby Search
    client = places.PlacesClient(client_options=ClientOptions(api_key=GOOGLE_KEY))

    # Build request using dicts for nested messages to avoid missing symbol issues
    radius = float(os.getenv("GOOGLE_TEST_RADIUS", "10500.0"))
    included_types_str = os.getenv("GOOGLE_TEST_INCLUDED_TYPES", "corporate_office")
    included_types = included_types_str.split(",")
    max_result_count = int(os.getenv("GOOGLE_TEST_MAX_RESULT_COUNT", "20"))
    language_code = os.getenv("GOOGLE_TEST_LANGUAGE_CODE", "en")

    print(f"Searching with Radius: {radius} meters")
    print(f"Included Types: {included_types}")
    print(f"Max Result Count: {max_result_count}")
    print(f"Language Code: {language_code}")

    request = place_types.SearchNearbyRequest(
        location_restriction={
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius,
            }
        },
        included_types=included_types,  # Use a broad, valid place type
        max_result_count=max_result_count,
        language_code=language_code,
        rank_preference=place_types.SearchNearbyRequest.RankPreference.DISTANCE # Add this line
    )

    # Places API (New) requires a response field mask; request a minimal set
    field_mask = "places.name,places.display_name,places.location,places.addressDescriptor" # Modify this line

    response = client.search_nearby(request=request, metadata=[("x-goog-fieldmask", field_mask)])
    # Response should contain places or be empty; both are acceptable for a lenient test
    assert response is not None
    places_container = getattr(response, "places", [])
    places_list = list(places_container) if places_container is not None else []
    print(f"Google Places API Response: ")
    if places_list:
        for place in places_list:
            place_info = {
                "name": place.name,
                "display_name": place.display_name.text if hasattr(place.display_name, 'text') else 'N/A',
            }
            
            if hasattr(place, 'location') and place.location:
                place_lat = place.location.latitude
                place_lon = place.location.longitude
                place_info["location"] = {"latitude": place_lat, "longitude": place_lon}
                
                # Calculate distance if origin lat/lng are available
                if lat is not None and lng is not None:
                    calculated_distance = haversine_distance(lat, lng, place_lat, place_lon)
                    place_info["calculated_distance_meters"] = calculated_distance

            if hasattr(place, 'addressDescriptor') and place.addressDescriptor:
                landmarks_info = []
                for landmark in place.addressDescriptor.landmarks:
                    landmarks_info.append({
                        "landmark_display_name": landmark.display_name.text if hasattr(landmark.display_name, 'text') else 'N/A',
                        "straight_line_distance_meters": landmark.straight_line_distance_meters,
                        "travel_distance_meters": landmark.travel_distance_meters
                    })
                place_info["address_descriptor_landmarks"] = landmarks_info
            
            print(json.dumps(place_info, indent=4))
    else:
        print("No places found.")

    # If results exist, validate a couple of basic fields commonly available
    if places_list:
        first = places_list[0]
        # name is the resource name (e.g., "places/PLACE_ID"); display_name is LocalizedText
        assert hasattr(first, "name") or hasattr(first, "display_name")

if __name__ == "__main__":
    test_google_places_nearby_lenient()
