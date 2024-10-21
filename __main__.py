import asyncio
import configparser
import inspect
import json
from pathlib import Path
from typing import Type

import aiometer
import orjson
from async_timeout import timeout
from loguru import logger
from openpyxl.worksheet.worksheet import Worksheet
from tqdm.asyncio import tqdm

import coupons
import stores
from lib.constants import GLOBAL_COUPON_PROVIDERS
from stores.lib import BaseStore
from utils.config import get_config

logger.remove()

# Log all errors, warnings, and info to the console
logger.add(tqdm.write, level='DEBUG')

Worksheet.to_list = lambda ws: list(ws.iter_rows(values_only=True))


async def main():
    Path('output/stores').mkdir(exist_ok=True, parents=True)
    section = _setup_config()

    await _handle_stores(section)
    await _handle_coupons(section)



async def _handle_coupon_site(coupon, is_retry: bool = False):
    logger.info(f'Grabbing Coupons for Source: {coupon.__name__}')

    try:
        async with timeout(240) as cm:
            async with coupon(cm=cm) as coupon_obj:
                try:
                    await coupon_obj.scrape()
                except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                    if is_retry:
                        logger.error(f'Timeout error scraping coupons: {e}')
                        return

                    logger.error(f'Timeout error scraping coupons: {e} - retrying...')
                    return await _handle_coupon_site(coupon, is_retry=True)

                except Exception as e:
                    logger.error(f'Error scraping coupons: {e}')
    except (asyncio.TimeoutError, asyncio.CancelledError) as e:
        if is_retry:
            logger.error(f'Timeout error scraping coupons: {e}')
            return

        logger.error(f'Timeout error scraping coupons: {e} - retrying...')
        return await _handle_coupon_site(coupon, is_retry=True)
    except Exception as e:
        logger.error(f'Error scraping coupons: {e}')


async def _handle_coupons(section: configparser.SectionProxy):
    included_coupons = orjson.loads(section.get('COUPON_SOURCES', '[]'))
    stores_at_once = section.getint('STORES_AT_ONCE', 2)

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
            async_fn=_handle_coupon_site, args=coupon_objs, max_at_once=stores_at_once
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
    stores_at_once = section.getint('STORES_AT_ONCE', 2)
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
        async_fn=_run_store, args=store_objs, max_at_once=stores_at_once
    )

    print('Finished scraping stores')


async def _run_store(store: Type['BaseStore'], is_retry: bool = False):
    try:
        async with timeout(240) as cm:
            async with store(cm=cm) as store_obj:
                logger.info(f'Grabbing Sales for Store: {store_obj._store_name}')

                try:
                    await store_obj.handle_flyers()
                except Exception as e:
                    logger.error(f'Error scraping store: {e}')
                    pass
    except (asyncio.TimeoutError, asyncio.CancelledError) as e:
        if is_retry:
            logger.error(f'Timeout error scraping store: {e}')
            return

        logger.error(f'Timeout error scraping store: {e} - retrying...')
        return await _run_store(store, is_retry=True)

    except Exception as e:
        logger.error(f'Error scraping store: {e}')

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
