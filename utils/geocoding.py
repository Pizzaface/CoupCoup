import random
import shutil
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path

import folium
import jinja2
import openrouteservice
import orjson
from bs4 import BeautifulSoup
from loguru import logger
from openrouteservice import geocode, directions
from rapidfuzz import fuzz

from utils.constants import modal_html, extra_script
from stores.lib.constants import POSSIBLE_STORE_COLORS
from utils.config import get_config


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


async def determine_store_paths():
    config = get_config()
    section = config['config']
    included_stores = orjson.loads(section.get('INCLUDED_STORES', '[]'))
    if 'directions' not in config:
        logger.error(
            'No directions section found in config.ini - please create one.'
        )
        return

    directions_config = config['directions']

    logger.info('Determining paths between stores...')
    if not included_stores:
        logger.error(
            "No stores included in config.ini - please add some to the 'INCLUDED_STORES' list"
        )
        return

    if 'openrouteservice_api_key' not in directions_config:
        logger.error(
            "No OpenRouteService API key found in config.ini - please add one under 'openrouteservice_api_key' in the [directions] section."
        )
        return

    if len(directions_config) - 1 == 0:
        logger.error(
            'Enter some geocoding information in the [directions] section for your starting location.'
        )
        return

    begin_long, begin_lat = geocode_zip(**directions_config)
    api_key = directions_config['openrouteservice_api_key']

    locations_by_store = get_locations_by_store(
        api_key=api_key,
        begin_lat=begin_lat,
        begin_long=begin_long,
        included_stores=included_stores,
    )

    # flatten the list of locations
    locations = [loc for locs in locations_by_store.values() for loc in locs]
    all_locations = [
        [begin_long, begin_lat],
        *locations,
        [begin_long, begin_lat],
    ]

    # plot the route
    route = directions.directions(
        client=openrouteservice.Client(key=api_key),
        coordinates=all_locations,
        profile='driving-car',
        format='geojson',
        instructions_format='html',
        units='mi',
        optimize_waypoints=True,
    )

    await create_map_bundle(begin_lat, begin_long, locations_by_store, route)


async def create_map_bundle(
    begin_lat: float,
    begin_long: float,
    locations_by_store: dict[str, list[list[float, float]]],
    route: dict,
):
    m = _prepare_map(begin_lat, begin_long, locations_by_store, route)

    logger.debug(f'Writing map...')

    temp = BytesIO()
    m.save(temp, close_file=False)
    temp.seek(0)

    pretty_html = _add_directions_components(route, temp)

    output_path = Path(
        f'{Path.cwd()}/output/{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}'
    )
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / 'directions.html', 'w+') as f:
        f.write(pretty_html)

    # Copy `resources` folder to output
    shutil.copytree(
        'resources',
        output_path / 'resources',
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '*.ttf', '*.woff2'),
    )
    # copy the webfont to webfonts/{fontname}.ttf
    Path(output_path / 'webfonts').mkdir(exist_ok=True)
    shutil.copy(
        'resources/fa-solid-900.ttf', output_path / 'webfonts/fa-solid-900.ttf'
    )
    shutil.copy(
        'resources/fa-solid-900.woff2', output_path / 'webfonts/fa-solid-900.woff2'
    )

    shutil.copy('output/stores.xlsx', output_path / 'stores.xlsx')
    shutil.copytree(
        'output/stores',
        output_path / 'stores',
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('*.pyc', '__pycache__'),
    )

    logger.info('Map and directions saved to directions.html')


def _add_directions_components(route, temp):
    bs = BeautifulSoup(temp, 'html.parser')
    # add title
    bs.head.append(bs.new_tag('title'))
    bs.title.string = 'CoupCoup'
    bs.head.append(bs.new_tag('meta', charset='utf-8'))
    bs.head.append(
        bs.new_tag(
            'meta', 'viewport', content='width=device-width, initial-scale=1.0'
        )
    )
    bs.head.append(
        bs.new_tag('link', rel='icon', href='resources/favicon.ico')
    )
    resources_to_add = ['map.css', 'csvutils.js', 'papaparse.min.js']
    for resource in resources_to_add:
        if resource.endswith('.js'):
            bs.body.append(bs.new_tag('script', src=f'resources/{resource}'))
        elif resource.endswith('.css'):
            bs.head.append(
                bs.new_tag(
                    'link', href=f'resources/{resource}', rel='stylesheet'
                )
            )
    direction_container = bs.new_tag(
        'div', attrs={'class': 'direction-overlay'}
    )
    direction_container.append(bs.new_tag('div', id='directionsContainer'))
    directions_navigation = bs.new_tag('div', class_='direction-navigation')

    prev_button = bs.new_tag(
        'button', attrs={'class': 'btn btn-primary prev-step'}
    )
    prev_button.string = 'Previous'
    directions_navigation.append(prev_button)

    next_button = bs.new_tag(
        'button', attrs={'class': 'btn btn-primary next-step'}
    )
    next_button.string = 'Next'
    directions_navigation.append(next_button)
    direction_container.append(directions_navigation)
    bs.body.insert(0, direction_container)

    bs.body.insert(0, BeautifulSoup(modal_html, 'html.parser'))

    bottom_script = bs.new_tag('script')
    bottom_script.string = jinja2.Template(extra_script).render(
        geometry=route['features'][0]['geometry']['coordinates'],
        directions=route['features'][0]['properties']['segments'],
    )

    bs.append(bottom_script)
    pretty_html = bs.prettify()
    return pretty_html


def _prepare_map(begin_lat, begin_long, locations_by_store, route):
    m = folium.Map(
        location=[begin_lat, begin_long],
        zoom_start=13,
        prefer_canvas=True,
        id='map',
    )
    folium.GeoJson(route).add_to(m)
    m = add_markers_to_map(locations_by_store, m)
    return m


def add_markers_to_map(
    locations_by_store: dict[str, list[list[float, float]]], m: folium.Map
) -> folium.Map:
    store_colors = {}
    for store_name, locs in locations_by_store.items():
        if store_name not in store_colors:
            store_colors[store_name] = random.choice(POSSIBLE_STORE_COLORS)

        for i, loc in enumerate(locs):
            html_text = f"""<a href='#' onclick="loadStoreSheetAndMatchupSheet('{store_name}')" data-bs-toggle="modal" data-bs-target="#sheetModal">{store_name}</a>"""

            tooltip = folium.map.Popup(html=html_text, max_width=2650)

            marker = folium.Marker(
                location=[loc[1], loc[0]],
                popup=store_name,
                icon=folium.Icon(
                    icon='shopping-cart',
                    prefix='fa',
                    color=store_colors[store_name],
                ),
            )
            marker.add_child(tooltip)
            m.add_child(marker)

    return m


def get_locations_by_store(
    api_key: str,
    begin_lat: float,
    begin_long: float,
    included_stores: list[str],
):
    locations_by_store = defaultdict(list)
    for store_name in included_stores:
        # search for local locations of store
        locations = get_store_locations(
            api_key, store_name, begin_lat, begin_long
        )

        if not locations:
            logger.error(f'No locations found for store: {store_name}')
            continue

        for location in locations:
            location_name = location['properties']['name']
            if fuzz.ratio(location_name, store_name) < 80:
                continue

            coords = location['geometry']['coordinates']
            locations_by_store[store_name].append([coords[0], coords[1]])

    return locations_by_store
