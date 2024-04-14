import openrouteservice
from openrouteservice import geocode
from rapidfuzz import fuzz

def geocode_zip(openrouteservice_api_key: str, **kwargs):
    client = openrouteservice.Client(key=openrouteservice_api_key)
    geocoded_zip = geocode.pelias_structured(client, **kwargs)

    coords = geocoded_zip['features'][0]['geometry']['coordinates']
    return coords[0], coords[1]

STORE_TO_STORE_NAME = {
    'heb': 'H-E-B',
    'cvs': 'CVS Pharmacy',
    'krogermidatlantic': 'Kroger',
    'smithsfoodanddrug': "Smith's Food & Drug",
    'kingsoopers': "King Soopers",
    'safeway': 'Safeway',
    'frysfoodstores': "Fry's Food Stores",
    'rousessupermarkets': "Rouses Supermarkets",
    'acmemarkets': "Acme Markets",
    'stopandshop': "Stop & Shop",
    'giantfood': "Giant",
    'foodlion': "Food Lion",
    'jewelosco': "Jewel-Osco",
    'sprouts': "Sprouts Farmers Market",
    'harristeeter': "Harris Teeter",
    'winndixie': "Winn-Dixie",
    'dollargeneral': "Dollar General",
    'familydollar': "Family Dollar",
    'foodcity': "Food City",
    'fredmeyer': "Fred Meyer",
}



def get_store_locations(
    api_key: str, store_name: str, lat: float, long: float
):
    if store_name.lower() in STORE_TO_STORE_NAME:
        store_name = STORE_TO_STORE_NAME[store_name.lower()]

    client = openrouteservice.Client(key=api_key)
    locations = geocode.pelias_search(
        client,
        text=store_name.title(),
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
