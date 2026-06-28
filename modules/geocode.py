"""
Geocoding for NagarSeva AI (Delhi NCR focused).

Converts a free-text Delhi-area location into latitude/longitude using
OpenStreetMap's Nominatim (free, no API key), and validates that the result
actually falls inside the Delhi NCR region. Users can type just an area
("Batla House", "Saket") without writing "Delhi" - we append it automatically.
Locations in other cities/states are rejected.
"""

import ssl
import certifi
import geopy.geocoders
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Use certifi's certificate bundle to avoid local SSL verification failures
try:
    _ctx = ssl.create_default_context(cafile=certifi.where())
    geopy.geocoders.options.default_ssl_context = _ctx
except Exception as e:
    print("SSL context setup warning:", str(e))

_geolocator = Nominatim(user_agent="nagarseva_ai_civic_app", timeout=10)
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1,
                       max_retries=1, error_wait_seconds=2.0, swallow_exceptions=True)

_session_cache = {}

# Delhi NCR approximate bounding box (covers Delhi + Gurugram, Noida, Faridabad,
# Ghaziabad, Greater Noida - the wider NCR). lat ~ 28.0-29.0, lon ~ 76.7-77.6
_NCR_BOUNDS = {"lat_min": 28.30, "lat_max": 28.95, "lon_min": 76.80, "lon_max": 77.55}

# Other major Indian cities - if the user explicitly types these, reject early
_OTHER_CITIES = {
    "mumbai", "bombay", "bangalore", "bengaluru", "hyderabad", "chennai",
    "kolkata", "calcutta", "pune", "ahmedabad", "surat", "jaipur", "lucknow",
    "kanpur", "nagpur", "indore", "bhopal", "patna", "chandigarh", "kochi",
    "goa", "mysore", "coimbatore", "visakhapatnam", "vizag", "nashik", "rajkot",
    "vadodara", "agra", "varanasi", "amritsar", "ludhiana", "guwahati", "ranchi",
    "raipur", "dehradun", "shimla", "srinagar", "thiruvananthapuram", "madurai",
    "juhu", "andheri", "bandra", "powai", "thane", "navi mumbai",
}


def _in_ncr(lat: float, lon: float) -> bool:
    b = _NCR_BOUNDS
    return b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]


def in_ncr(lat: float, lon: float) -> bool:
    """Public helper: is this coordinate inside Delhi NCR?"""
    try:
        return _in_ncr(float(lat), float(lon))
    except Exception:
        return False


# Verified coordinates for popular Delhi NCR areas, including common misspellings.
# Checked first (instant + reliable) before hitting the online geocoder, so typos
# like "rajori garden" still map correctly.
_KNOWN_AREAS = {
    "rajouri garden": (28.6415, 77.1209), "rajori garden": (28.6415, 77.1209),
    "batla house": (28.5560, 77.2880), "jamia nagar": (28.5620, 77.2810),
    "okhla": (28.5500, 77.2700), "saket": (28.5245, 77.2066),
    "dwarka": (28.5921, 77.0460), "rohini": (28.7410, 77.0660),
    "connaught place": (28.6315, 77.2167), "cp": (28.6315, 77.2167),
    "karol bagh": (28.6512, 77.1906), "lajpat nagar": (28.5677, 77.2433),
    "nehru place": (28.5494, 77.2510), "hauz khas": (28.5494, 77.2001),
    "vasant kunj": (28.5200, 77.1591), "janakpuri": (28.6219, 77.0878),
    "pitampura": (28.6987, 77.1325), "shahdara": (28.6730, 77.2890),
    "laxmi nagar": (28.6358, 77.2772), "preet vihar": (28.6418, 77.2954),
    "mayur vihar": (28.6089, 77.2934), "vikaspuri": (28.6380, 77.0780),
    "punjabi bagh": (28.6680, 77.1310), "rajender nagar": (28.6380, 77.1810),
    "rajendra nagar": (28.6380, 77.1810), "kalkaji": (28.5400, 77.2590),
    "greater kailash": (28.5410, 77.2410), "gk": (28.5410, 77.2410),
    "chandni chowk": (28.6506, 77.2303), "paharganj": (28.6450, 77.2120),
    "tilak nagar": (28.6410, 77.0950), "uttam nagar": (28.6220, 77.0590),
    "najafgarh": (28.6090, 76.9800), "narela": (28.8530, 77.0920),
    "model town": (28.7160, 77.1890), "civil lines": (28.6790, 77.2250),
    "ashok vihar": (28.6990, 77.1760), "moti nagar": (28.6580, 77.1430),
    "rajouri": (28.6415, 77.1209), "kashmere gate": (28.6670, 77.2290),
    "noida": (28.5355, 77.3910), "gurugram": (28.4595, 77.0266),
    "gurgaon": (28.4595, 77.0266), "faridabad": (28.4089, 77.3178),
    "ghaziabad": (28.6692, 77.4538), "greater noida": (28.4744, 77.5040),
}


def _known_area_coords(location: str):
    """Look up popular Delhi areas locally before calling the online geocoder."""
    key = location.strip().lower()
    # direct hit
    if key in _KNOWN_AREAS:
        return _KNOWN_AREAS[key]
    # try stripping trailing ", delhi" / ", new delhi" / ", india"
    core = (key.replace(", new delhi", "").replace(", delhi", "")
            .replace(", india", "").replace(",delhi", "").strip())
    if core in _KNOWN_AREAS:
        return _KNOWN_AREAS[core]
    # try matching the first significant chunk (e.g. "saket sector 5" -> "saket")
    for area, coords in _KNOWN_AREAS.items():
        if core.startswith(area):
            return coords
    return None


def reverse_geocode(lat: float, lon: float):
    """
    Turn GPS coordinates into a human-readable area name (for the GPS button).
    Returns a string like 'Batla House, New Delhi' or None.
    """
    try:
        result = _geolocator.reverse((lat, lon), exactly_one=True, language="en")
        if result:
            return result.address
    except Exception as e:
        print("REVERSE GEOCODE ERROR (non-fatal):", str(e))
    return None


def geocode_location(location: str):
    """
    Convert a Delhi-area location string to (lat, lon).
    Appends 'Delhi' if the user didn't mention a city. Returns None if not found.
    (Does NOT enforce NCR bounds - that's validate_location's job, so the map
    can still pin whatever geocoded.)
    """
    if not location or not location.strip():
        return None

    key = location.strip().lower()
    if key in _session_cache:
        return _session_cache[key]

    # 1) Fast, reliable local lookup for popular areas (handles common typos)
    known = _known_area_coords(location)
    if known:
        _session_cache[key] = known
        return known

    # 2) Fall back to the online geocoder
    query = location.strip()
    if "delhi" not in key and "ncr" not in key:
        query = f"{query}, Delhi, India"
    elif "india" not in key:
        query = f"{query}, India"

    try:
        result = _geocode(query, country_codes="in")
        if result:
            coords = (round(result.latitude, 6), round(result.longitude, 6))
            _session_cache[key] = coords
            return coords
    except Exception as e:
        print("GEOCODE ERROR (non-fatal):", str(e))

    _session_cache[key] = None
    return None


# City/region-level names that are too vague on their own - need an area/landmark.
# Includes NCR cities: typing just "Noida" or "Delhi" isn't specific enough.
_VAGUE_CITY_ONLY = {
    "mumbai", "delhi", "new delhi", "bangalore", "bengaluru", "hyderabad",
    "chennai", "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "bhopal", "patna", "india",
    "noida", "greater noida", "gurugram", "gurgaon", "faridabad", "ghaziabad",
    "ncr", "delhi ncr",
}


def validate_location(location: str) -> dict:
    """Validate a user-entered location for Delhi NCR only.

    Returns a dict with keys: ok, level, coords, message.
    Rejects empty input, other-city names, and points outside the NCR box.
    Accepts NCR points (with coords) and, leniently, unfound localities that
    do not name another city.
    """
    if not location or not location.strip():
        return {"ok": False, "level": "empty", "coords": None,
                "message": "Please enter a location."}

    cleaned = location.strip().lower()
    # Normalize for the vague check: strip trailing ", india" / ", delhi" / "ncr"
    core = (cleaned.replace(", india", "").replace(",india", "")
            .replace(", ncr", "").replace(", delhi ncr", "").strip())

    # Too vague: just a bare city/region name with no area or landmark
    if core in _VAGUE_CITY_ONLY:
        return {"ok": False, "level": "vague", "coords": None,
                "message": (f"'{location.strip()}' is too broad. Please add a specific "
                            "area, locality, or landmark in Delhi NCR "
                            "(e.g. 'Batla House', 'Saket', 'Connaught Place').")}

    # Explicitly mentions another city -> reject (this app serves Delhi NCR only)
    for city in _OTHER_CITIES:
        if city in cleaned:
            return {"ok": False, "level": "other_city", "coords": None,
                    "message": (f"NagarSeva AI currently serves Delhi NCR only. "
                                f"'{location.strip()}' looks like it's in another city. "
                                "Please enter a Delhi NCR location (e.g. 'Batla House' or 'Saket').")}

    # Geocode (auto-appends Delhi) and check it falls within NCR
    coords = geocode_location(location)
    if coords is not None:
        if _in_ncr(coords[0], coords[1]):
            return {"ok": True, "level": "valid", "coords": coords,
                    "message": "Delhi NCR location verified (ok)"}
        else:
            return {"ok": False, "level": "outside_ncr", "coords": None,
                    "message": ("NagarSeva AI currently serves Delhi NCR only. "
                                "That location appears to be outside Delhi NCR. "
                                "Please enter a Delhi-area location.")}

    # Geocoding could not resolve it -> reject so it won't break the map.
    return {"ok": False, "level": "notfound", "coords": None,
            "message": ("Couldn't find that location on the map. Please enter a valid, "
                        "correctly-spelled Delhi NCR area or landmark "
                        "(e.g. 'Batla House', 'Saket', 'Rajouri Garden').")}