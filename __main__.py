import asyncio
import configparser
import inspect
import json
import random
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Type

import aiometer
import openrouteservice
import orjson
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openrouteservice import directions
import sys

from loguru import logger
from pandas import DataFrame
from rapidfuzz import fuzz
from tqdm.asyncio import tqdm

from lib.constants import GLOBAL_COUPON_PROVIDERS
from stores.lib import BaseStore
from utils.jinja import get_template_with_args
from utils.spreadsheets import write_grouped_rows_with_colors, clean_workbook
import coupons
import stores
import openai
import folium

from stores.lib.constants import HEADERS, POSSIBLE_STORE_COLORS
from utils.config import get_config
from utils.geocoding import geocode_zip, get_store_locations
from utils.matching import match_multiple_columns

from bs4 import BeautifulSoup

logger.remove()

# Log all errors, warnings, and info to the console
logger.add(tqdm.write, level='DEBUG')

Worksheet.to_list = lambda ws: list(ws.iter_rows(values_only=True))


async def main():
    Path('output/stores').mkdir(exist_ok=True, parents=True)
    section = _setup_config()

    # await _handle_stores(section)
    # await _handle_coupons(section)

    # await _compare_products()
    await determine_store_paths()


async def _compare_products():
    wb = load_workbook('output/stores.xlsx')
    sheet_names = wb.sheetnames

    newspaper_coupons = get_global_coupons(sheet_names, wb)

    tasks = []
    # get the sales
    for sheet_name in sheet_names:
        if sheet_name.endswith((*GLOBAL_COUPON_PROVIDERS, '-coupons', '-matchups')):
            continue

        tasks.append(
            run_matchups_for_store(
                newspaper_coupons, sheet_name, sheet_names, wb
            )
        )

    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f'Error comparing products: {result}')
            continue

    clean_workbook(wb)

    wb.save('output/stores.xlsx')

    _split_sheets_by_store(wb)

    wb.close()


def _split_sheets_by_store(wb: Workbook):
    # split the stores into separate files
    sheet_names = wb.sheetnames
    for sheet_name in sheet_names:
        if sheet_name.endswith(('matchups', 'coupons', 'com')):
            continue

        # convert the sheet to a dataframe
        sales = wb[sheet_name]
        values = list(sales.values)[1:]
        sales = DataFrame(values, columns=HEADERS)

        # save it as a csv
        sales.to_csv(f'output/stores/{sheet_name}.csv', index=False)


def get_global_coupons(sheet_names: list[str], wb: Workbook):
    newspaper_coupons = []
    if 'newspaper-coupons' in sheet_names:
        newspaper_coupons.extend(
            wb['newspaper-coupons'].to_list()[1:],
        )
    if 'coupons-com' in sheet_names:
        newspaper_coupons.extend(
            wb['coupons-com'].to_list()[1:],
        )
    newspaper_coupons = DataFrame(newspaper_coupons, columns=HEADERS)

    if newspaper_coupons.empty:
        logger.error('No coupons found in the global coupon sheets')

    return newspaper_coupons


async def run_matchups_for_store(
    newspaper_coupons: DataFrame,
    sheet_name: str,
    sheet_names: list[str],
    wb: Workbook,
):
    sales, total_coupons = _get_sales_and_coupons(
        newspaper_coupons, sheet_name, sheet_names, wb
    )

    try:
        # compare the products
        matches = match_multiple_columns(
            total_coupons,
            sales,
            ['brand_name', 'product_name', 'product_variety'],
            ['brand_name', 'product_name', 'product_variety'],
            threshold=90,
            limit=None,
        )
    except Exception as e:
        logger.error(f'Error comparing products for {sheet_name}: {e}')
        return

    sheet = wb.create_sheet(f'{sheet_name}-matchups', 0)
    rows = dataframe_to_rows(matches, index=False, header=True)

    write_grouped_rows_with_colors(rows, sheet)


def _get_sales_and_coupons(
    newspaper_coupons: DataFrame,
    sheet_name: str,
    sheet_names: list[str],
    wb: Workbook,
):
    if f'{sheet_name}-matchups' in sheet_names:
        del wb[f'{sheet_name}-matchups']

    sales = wb[sheet_name]
    values = list(sales.values)[1:]
    sales = DataFrame(values, columns=HEADERS)
    total_coupons = DataFrame()

    if f'{sheet_name}-coupons' in sheet_names:
        values = wb[f'{sheet_name}-coupons'].to_list()[1:]
        total_coupons = DataFrame(values, columns=HEADERS)

    if isinstance(newspaper_coupons, DataFrame):
        total_coupons = pd.concat(
            [total_coupons, newspaper_coupons],
            ignore_index=True,
            sort=False,
        )

    return sales, total_coupons


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

    await create_shopping_route(
        begin_lat, begin_long, locations_by_store, route
    )


async def create_shopping_route(
    begin_lat: float,
    begin_long: float,
    locations_by_store: dict[str, list[list[float, float]]],
    route: dict,
):
    m = folium.Map(location=[begin_lat, begin_long], zoom_start=13, prefer_canvas=True, id='map')
    folium.GeoJson(route).add_to(m)
    store_colors = {}
    logger.debug(f'Locations by store: {locations_by_store}')
    for store_name, locs in locations_by_store.items():
        if store_name not in store_colors:
            store_colors[store_name] = random.choice(POSSIBLE_STORE_COLORS)

        for i, loc in enumerate(locs):
            html_text = f"""<a href='#' onclick="loadSheet('output/stores/{store_name}.csv')" data-toggle="modal" data-target="#sheetModal">{store_name}</span>"""

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

    logger.debug(f'Writing map...')

    temp = BytesIO()
    m.save(temp, close_file=False)
    temp.seek(0)

    jinja_directions = await get_template_with_args(
        'direction_output.jinja',
        map=temp.read().decode('utf-8'),
        directions=route.get('features', [])[0]['properties']['segments'],
        geometry=route.get('features', [])[0]['geometry']['coordinates']
    )

    html = jinja_directions.encode('utf-8')
    bs = BeautifulSoup(html, 'html.parser')
    pretty_html = bs.prettify()

    with open('directions.html', 'w') as f:
        f.write(pretty_html)

    logger.info('Map and directions saved to directions.html')


def get_locations_by_store(
    api_key: str,
    begin_lat: float,
    begin_long: float,
    included_stores: list[str],
):
    locations_by_store = defaultdict(list)
    for store_name in included_stores:
        if store_name.lower() == 'heb':
            store_name = 'H-E-B'

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


async def _handle_coupon_site(coupon):
    logger.info(f'Grabbing Coupons for Source: {coupon.__name__}')

    async with coupon() as coupon_obj:
        try:
            await coupon_obj.scrape()
        except Exception as e:
            logger.error(f'Error scraping coupons: {e}')


async def _handle_coupons(section: configparser.SectionProxy):
    included_coupons = orjson.loads(section.get('COUPON_SOURCES', '[]'))

    if included_coupons:
        coupon_objs = inspect.getmembers(coupons, inspect.isclass)
        coupon_objs = [
            coupon
            for coupon_name, coupon in coupon_objs
            if coupon_name in included_coupons or coupon_name in GLOBAL_COUPON_PROVIDERS or coupon_name.removesuffix('Coupons') in included_coupons
        ]

        await aiometer.run_on_each(async_fn=_handle_coupon_site, args=coupon_objs, max_at_once=2)

    else:
        logger.info(
            'No coupon sources included in config.ini - skipping coupon scraping.'
        )


def _setup_config():
    config = get_config()

    try:
        section = config['config']
    except KeyError:
        raise Exception(
            'No [config] section found in config.ini - please create one.'
        )

    if 'OPENAI_KEY' in section:
        openai.api_key = section['OPENAI_KEY']
    elif 'GOOGLE_PROJECT_ID' in section:
        import vertexai as genai

        genai.init(project=section['GOOGLE_PROJECT_ID'])
    elif 'GOOGLE_API_KEY' in section:
        import google.generativeai as genai

        genai.configure(api_key=section['GOOGLE_API_KEY'])
    else:
        raise Exception(
            "No OpenAI or Google API key found in config.ini - please add one under 'OPENAI_KEY' or 'GOOGLE_API_KEY' in the [config] section."
        )

    return section


async def _handle_stores(section):
    included_stores = json.loads(section.get('INCLUDED_STORES', '[]'))

    if not included_stores:
        print('No stores included in config.ini - skipping store scraping.')
        return

    store_objs = [
        store
        for store_name, store in inspect.getmembers(stores, inspect.isclass)
        if store_name in included_stores
    ]

    await aiometer.run_on_each(async_fn=_run_store, args=store_objs, max_at_once=2)

    print('Finished scraping stores')


async def _run_store(store: Type[BaseStore]):
    async with store() as store_obj:
        logger.info(f'Grabbing Sales for Store: {store_obj._store_name}')
        try:
            await store_obj.handle_flyers()
        except Exception as e:
            logger.error(f'Error scraping store: {e}')
            pass


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
