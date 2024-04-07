import openrouteservice
from openrouteservice import geocode
from rapidfuzz import fuzz

def geocode_zip(openrouteservice_api_key: str, **kwargs):
    client = openrouteservice.Client(key=openrouteservice_api_key)
    geocoded_zip = geocode.pelias_structured(client, **kwargs)

    coords = geocoded_zip['features'][0]['geometry']['coordinates']
    return coords[0], coords[1]


def get_store_locations(
    api_key: str, store_name: str, lat: float, long: float
):
    client = openrouteservice.Client(key=api_key)
    locations = geocode.pelias_search(
        client,
        text=store_name,
        focus_point=[long, lat],
        size=10,
        circle_point=[long, lat],
        circle_radius=40,
        country='USA',
        layers=['venue', 'address']
    )

    checked_locations = []
    for location in locations['features']:
        if fuzz.ratio(location['properties']['name'], store_name) > 80:
            checked_locations.append(location)

    return checked_locations
