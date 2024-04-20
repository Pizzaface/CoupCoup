import shutil
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
import jinja2
import openrouteservice
import orjson
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openrouteservice import directions

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
from offline_folium import offline   # noqa
import folium

from datetime import datetime
from stores.lib.constants import HEADERS, POSSIBLE_STORE_COLORS
from utils.config import get_config
from utils.geocoding import geocode_zip, get_store_locations
from utils.matching import match_multiple_columns

from bs4 import BeautifulSoup

logger.remove()

# Log all errors, warnings, and info to the console
logger.add(tqdm.write, level='DEBUG')

Worksheet.to_list = lambda ws: list(ws.iter_rows(values_only=True))

modal_html = """<div class="modal" tabindex="-1"
             id="sheetModal" aria-labelledby="sheetModalLabel" aria-hidden="true">  <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="row my-1">
                        <div class="col-6 text-left">
                            <h5 id="sheetModalLabel"></h5>
                        </div>
                        <div class="col-6 text-right">
                            <button type="button" class="close" data-bs-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true"><i class="fa fa-times"></i></span>
                            </button>
                        </div>
                    </div>
                    <div class="row my-1">
                        <input type="text" id="search" placeholder="Search for a product..." class="form-control">
                        <div class="row mt-1 mx-auto">
                            <div class="col-6 text-center">
                                <button id="searchButton" class="btn btn-primary">Search</button>
                            </div>
                            <div class="col-6 text-center">
                                <button id="clearSearch" class="btn btn-secondary">Clear</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-body">

                    <div id="contents"></div>
                </div>
            </div>
        </div>
        </div>"""


extra_script = """window.addEventListener('DOMContentLoaded', (event) => {
                $('#searchButton').click(function() {
                    var search = $('#search').val();
                    var cards = $('.coupon-card');
                    cards.each(function(index, card) {
                        var header = $(card).find('.coupon-header').text();
                        if (header.toLowerCase().includes(search.toLowerCase())) {
                            $(card).show();
                        } else {
                            $(card).hide();
                        }
                    });
                });

                $('#clearSearch').click(function() {
                    $('#search').val('');
                    var cards = $('.coupon-card');
                    cards.each(function(index, card) {
                        $(card).show();
                    });
                });
            });

            function findLeafletMap() {
                for (var key in window) {
                    if (key.startsWith('map_') && window[key] instanceof L.Map) {
                        return window[key];
                    }
                }
                return null;
            }

            const icons = {
                'turn-left': `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23000000' viewBox='0 0 24 24' id='turn-left-top-direction-circle' data-name='Flat Color' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'/%3E%3Cpath id='secondary' d='M13,9H10.41l.3-.29A1,1,0,1,0,9.29,7.29l-2,2a1,1,0,0,0,0,1.42l2,2a1,1,0,0,0,1.42,0,1,1,0,0,0,0-1.42l-.3-.29H13v5a1,1,0,0,0,2,0V11A2,2,0,0,0,13,9Z' style='fill: rgb(44, 169, 188);'/%3E%3Cscript xmlns='' id='bw-fido2-page-script'/%3E%3C/svg%3E"`,
                'turn-right': `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23000000' viewBox='0 0 24 24' id='turn-right-direction-circle' data-name='Flat Color' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'/%3E%3Cpath id='secondary' d='M16.71,9.29l-2-2a1,1,0,1,0-1.42,1.42l.3.29H11a2,2,0,0,0-2,2v5a1,1,0,0,0,2,0V11h2.59l-.3.29a1,1,0,0,0,0,1.42,1,1,0,0,0,1.42,0l2-2A1,1,0,0,0,16.71,9.29Z' style='fill: rgb(44, 169, 188);'/%3E%3C/svg%3E"`,
                'uturn': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M17.0005 18.1716L14.4649 15.636L13.0507 17.0503L18.0005 22L22.9502 17.0503L21.536 15.636L19.0005 18.1716V11C19.0005 6.58172 15.4187 3 11.0005 3C6.58218 3 3.00046 6.58172 3.00046 11V20H5.00046V11C5.00046 7.68629 7.68675 5 11.0005 5C14.3142 5 17.0005 7.68629 17.0005 11V18.1716Z'%3E%3C/path%3E%3C/svg%3E",
                'exit-left': "data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='up-left-arrow-circle' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'%3E%3C/circle%3E%3Cpath id='secondary' d='M7.24,8.21l.7,3.73a1,1,0,0,0,1.55.57l.8-.8,4.54,4.53a1,1,0,0,0,1.41,0,1,1,0,0,0,0-1.41l-4.53-4.54.8-.8a1,1,0,0,0-.57-1.55l-3.73-.7A.82.82,0,0,0,7.24,8.21Z' style='fill: rgb(44, 169, 188);'%3E%3C/path%3E%3C/svg%3E",
                'exit-right': "data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='up-right-arrow-circle' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'%3E%3C/circle%3E%3Cpath id='secondary' d='M15.79,7.24l-3.73.7a1,1,0,0,0-.57,1.55l.8.8L7.76,14.83a1,1,0,0,0,0,1.41,1,1,0,0,0,1.41,0l4.54-4.53.8.8a1,1,0,0,0,1.55-.57l.7-3.73A.82.82,0,0,0,15.79,7.24Z' style='fill: rgb(44, 169, 188);'%3E%3C/path%3E%3C/svg%3E",
                'store': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M21 11.6458V21C21 21.5523 20.5523 22 20 22H4C3.44772 22 3 21.5523 3 21V11.6458C2.37764 10.9407 2 10.0144 2 9V3C2 2.44772 2.44772 2 3 2H21C21.5523 2 22 2.44772 22 3V9C22 10.0144 21.6224 10.9407 21 11.6458ZM14 9C14 8.44772 14.4477 8 15 8C15.5523 8 16 8.44772 16 9C16 10.1046 16.8954 11 18 11C19.1046 11 20 10.1046 20 9V4H4V9C4 10.1046 4.89543 11 6 11C7.10457 11 8 10.1046 8 9C8 8.44772 8.44772 8 9 8C9.55228 8 10 8.44772 10 9C10 10.1046 10.8954 11 12 11C13.1046 11 14 10.1046 14 9Z'%3E%3C/path%3E%3C/svg%3E",
                'compass': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12C22 17.5228 17.5228 22 12 22ZM12 20C16.4183 20 20 16.4183 20 12C20 7.58172 16.4183 4 12 4C7.58172 4 4 7.58172 4 12C4 16.4183 7.58172 20 12 20ZM15.5 8.5L13.5 13.5L8.5 15.5L10.5 10.5L15.5 8.5Z'%3E%3C/path%3E%3C/svg%3E",
                'straight': `data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='up-direction-square' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Crect id='primary' x='2' y='2' width='20' height='20' rx='2' style='fill: rgb(0, 0, 0);'%3E%3C/rect%3E%3Cpath id='secondary' d='M14,12v4a1,1,0,0,1-1,1H11a1,1,0,0,1-1-1V12H9.18a1,1,0,0,1-.76-1.65l2.82-3.27a1,1,0,0,1,1.52,0l2.82,3.27A1,1,0,0,1,14.82,12Z' style='fill: rgb(44, 169, 188);'%3E%3C/path%3E%3C/svg%3E`,
                'roundabout': `data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='update' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Cpath id='primary' d='M19,2a1,1,0,0,0-1,1V5.33A9,9,0,0,0,3,12a1,1,0,0,0,2,0A7,7,0,0,1,16.86,7H14a1,1,0,0,0,0,2h5a1,1,0,0,0,1-1V3A1,1,0,0,0,19,2Z' style='fill: rgb(0, 0, 0);'%3E%3C/path%3E%3Cpath id='secondary' d='M20,11a1,1,0,0,0-1,1A7,7,0,0,1,7.11,17H10a1,1,0,0,0,0-2H5a1,1,0,0,0-1,1v5a1,1,0,0,0,2,0V18.67A9,9,0,0,0,21,12,1,1,0,0,0,20,11Z' style='fill: #000000;'%3E%3C/path%3E%3C/svg%3E`
            }

            function mapDirectionToFontAwesome(direction) {
                direction = direction.toLowerCase();
                if (direction.includes('exit left') || direction.includes('keep left')) {
                    return 'exit-left';
                } else if (direction.includes('exit right') || direction.includes('keep right')) {
                    return 'exit-right';
                } else if (direction.includes('roundabout')) {
                    return 'roundabout';
                } else if (direction.includes('straight')) {
                    return 'straight';
                } else if (direction.includes('uturn')) {
                    return 'uturn';
                } else if (direction.includes('destination') || direction.includes('arrive')) {
                    return 'store';
                } else if (direction.includes('head')) {
                    return 'compass';
                } else if (direction.includes('turn left') || direction.includes('sharp left') || direction.includes('left')) {
                    return 'turn-left'
                } else if (direction.includes('turn right') || direction.includes('sharp right') || direction.includes('right')) {
                    return 'turn-right';
                } else {
                    return 'compass'
                }
            }

            function secondsToHms(d) {
                d = Number(d);
                var h = Math.floor(d / 3600);
                var m = Math.floor(d % 3600 / 60);
                var s = Math.floor(d % 3600 % 60);

                var hDisplay = h > 0 ? h + (h === 1 ? " hour, " : " hours, ") : "";
                var mDisplay = m > 0 ? m + (m === 1 ? " minute, " : " minutes, ") : "";
                var sDisplay = s > 0 ? s + (s === 1 ? " second" : " seconds") : "";

                const out = hDisplay + mDisplay + sDisplay;
                return out.length > 0 ? out : 'N/A';
            }


            $(document).ready(function() {
                // fetch the file
                var geometry = {{ geometry | tojson }};
                var directions = {{ directions | tojson }};

                var marker;
                var currentDirectionIndex = 0;
                var currentStepIndex = 0;
                const map = findLeafletMap();


                function showStep() {

                    var direction = directions[currentDirectionIndex];
                    var step = direction.steps[currentStepIndex];
                    const icon = mapDirectionToFontAwesome(step.instruction);

                    var markerIcon = L.divIcon({
                        html: `<img src="${icons[icon]}">`,
                        iconSize: [40, 40],
                        iconAnchor: [20, 20],
                        className: 'direction-marker',
                    });

                    if (step.way_points && step.way_points.length > 0) {
                        if (marker) {
                            map.removeLayer(marker);
                        }

                        var firstPoint = step.way_points[0]; // Get the first point
                        var lastPoint = step.way_points[step.way_points.length - 1]; // Get the last point
                        var lat_lng = geometry[firstPoint]; // Get the lat/lng of the first point
                        map.flyTo([lat_lng[1], lat_lng[0]], 19); // Pan the map to the first point

                        marker = L.marker([lat_lng[1], lat_lng[0]], {
                            icon: markerIcon,
                            className: 'direction-marker-icon',
                        }).addTo(map);
                    }





                    $('#directionsContainer').html(`
    <div class="align-center route-info">
        <div class='instruction' style="">
            <img src="${icons[icon]}" style="width: 50px; height: 50px; margin-right: 10px; margin-top: auto; margin-bottom: auto;">
            ${step.instruction}
        </div>
        <p style='font-size: 1rem'>Store ${currentDirectionIndex + 1}: ${direction.distance} mi (total)</p>
        <p>Distance: ${step.distance} mi</p>
        <p>Duration: ${secondsToHms(step.duration)}</p>
    </div>
`);

                }


                function nextStep() {
                    var direction = directions[currentDirectionIndex];
                    if (currentStepIndex < direction.steps.length - 1) {
                        currentStepIndex++;
                        showStep();
                    } else if (currentDirectionIndex < directions.length - 1) {
                        currentDirectionIndex++;
                        currentStepIndex = 0;
                        showStep();
                    }
                }

                function prevStep() {
                    if (currentStepIndex > 0) {
                        currentStepIndex--;
                        showStep();
                    } else if (currentDirectionIndex > 0) {
                        currentDirectionIndex--;
                        currentStepIndex = directions[currentDirectionIndex].steps.length - 1;
                        showStep();
                    }
                }

                $('.next-step').click(nextStep);
                $('.prev-step').click(prevStep);

                // Initially show the first step of the first direction
                showStep();
            });"""


async def main():
    Path('output/stores').mkdir(exist_ok=True, parents=True)
    section = _setup_config()

    # await _handle_stores(section)
    # await _handle_coupons(section)

    await _compare_products()
    await determine_store_paths()


async def _compare_products():
    wb = load_workbook('output/stores.xlsx')
    sheet_names = wb.sheetnames

    newspaper_coupons = get_global_coupons(sheet_names, wb)

    tasks = []
    # get the sales
    for sheet_name in sheet_names:
        if sheet_name.endswith(
            (*GLOBAL_COUPON_PROVIDERS, '-coupons', '-matchups')
        ):
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
    if Path('output/stores').exists():
        shutil.rmtree('output/stores')

    Path('output/stores').mkdir(exist_ok=True, parents=True)

    # split the stores into separate files
    sheet_names = wb.sheetnames
    for sheet_name in sheet_names:
        if sheet_name.endswith(('coupons', 'com')):
            continue

        # convert the sheet to a dataframe
        sales = wb[sheet_name]
        values = list(sales.values)[1:]
        sales = DataFrame(values, columns=HEADERS if not sheet_name.endswith('matchups') else [*HEADERS, "Matched Field", "Matched Value", 'Match Percentage', 'Matched Rows'])

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
            html_text = f"""<a href='#' onclick="loadSheet('stores/{store_name.lower()}.csv')" data-bs-toggle="modal" data-bs-target="#sheetModal">{store_name}</a>"""

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
            if coupon_name in included_coupons
            or coupon_name in GLOBAL_COUPON_PROVIDERS
            or coupon_name.removesuffix('Coupons') in included_coupons
        ]

        await aiometer.run_on_each(
            async_fn=_handle_coupon_site, args=coupon_objs, max_at_once=2
        )

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

    if 'GOOGLE_PROJECT_ID' in section:
        import vertexai as genai

        genai.init(project=section['GOOGLE_PROJECT_ID'])
    elif 'GOOGLE_API_KEY' in section:
        import google.generativeai as genai

        genai.configure(api_key=section['GOOGLE_API_KEY'])
    else:
        raise Exception(
            "No Google API key found in config.ini - please add one under 'OPENAI_KEY' or 'GOOGLE_API_KEY' in the [config] section."
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

    await aiometer.run_on_each(
        async_fn=_run_store, args=store_objs, max_at_once=2
    )

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
