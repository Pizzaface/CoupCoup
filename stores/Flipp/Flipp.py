from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Any

import httpx as httpx
from abc import ABC

from aioitertools.more_itertools import chunked
from dateutil.parser import parse
from stores.lib.BaseStore import Store
from stores.lib.constants import WEEKLY_AD_NAMES
from utils.text import clean_text


class Flipp(Store, ABC):
    access_token: str | None = None
    store_code: str | None = None
    current_flyer_id: int | None = None
    _store_name: str | None = None

    flyer_ids_to_process: list[int] = []
    processing_queue: list[dict] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.store_code = self.store_config.get('store_code')
        self.access_token = self.store_config.get('access_token')

        if not self.store_code or not self.access_token:
            raise Exception(
                f'{self.__class__} store code or access token not found in config'
            )


    @property
    def store_name(self) -> str:
        return self._store_name

    @store_name.setter
    def store_name(self, value: str):
        self._store_name = value

    @property
    def flyer_url(self) -> str:
        return f'https://dam.flippenterprise.net/flyerkit/publications/{self._store_name}?locale=en&access_token={self.access_token}&show_storefronts=true&store_code={self.store_code}'

    @property
    def products_url(self):
        if not self.current_flyer_id:
            raise Exception('Flyer ID not set')

        return f'https://dam.flippenterprise.net/flyerkit/publication/{self.current_flyer_id}/products?display_type=all&valid_web_url=false&locale=en&access_token={self.access_token}'

    async def grab_flyers(self, is_retry: bool = False) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            timeout=90, transport=self.httpx_transport
        ) as client:
            try:
                response = await client.get(self.flyer_url, timeout=90)
            except (
                httpx.HTTPStatusError,
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                httpx.ConnectError,
                httpx.RequestError,
            ) as e:
                if is_retry:
                    self.logger.error(f'Error grabbing flyers on retry: {e}')
                    return []

                self.logger.info('Error grabbing flyers - retrying')
                await asyncio.sleep(20)
                return await self.grab_flyers(is_retry=True)

        response.raise_for_status()
        return response.json()

    async def grab_sales(self) -> AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(
            timeout=90, transport=self.httpx_transport
        ) as client:
            response = await client.get(self.products_url, timeout=90)

            response.raise_for_status()
            data = response.json()

        for item in data:
            try:
                item['price_text'] = float(
                    item['price_text'].replace('$', '')
                )
            except ValueError:
                pass

            try:
                item['valid_from'] = parse(item['valid_from']).strftime(
                    '%Y-%m-%d'
                )
            except ValueError:
                pass

            try:
                item['valid_to'] = parse(item['valid_to']).strftime(
                    '%Y-%m-%d'
                )
            except ValueError:
                pass

            filtered_item = {
                'sku': item.get('sku'),
                'item_type': item.get('item_type'),
                'name': clean_text(item['name']),
                'brand': clean_text(item['brand']),
                'pre_price': item['pre_price_text'],
                'price_text': item['price_text'],
                'sale_story': clean_text(item['sale_story']),
                'valid_from': item['valid_from'],
                'valid_to': item['valid_to'],
                'description': clean_text(item['description']),
            }

            yield filtered_item

    async def handle_flyers(self, is_retry: bool = False):
        try:
            flyers = await self.grab_flyers()
        except Exception as e:
            if is_retry:
                self.logger.error(f'Error grabbing flyers on retry: {e}')
                return
            self.logger.info(f'Error grabbing flyers: {e} - retrying')
            await asyncio.sleep(5)
            return await self.handle_flyers(is_retry=True)

        for flyer in flyers:

            if (
                flyer['name'] not in WEEKLY_AD_NAMES
                and flyer['external_display_name'] not in WEEKLY_AD_NAMES
            ):
                continue

            self.flyer_ids_to_process.append(flyer['id'])

        # Gather all handle_product tasks
        tasks = []
        for flyer_id in self.flyer_ids_to_process:
            self.current_flyer_id = flyer_id

            async for product in self.grab_sales():
                tasks.append(self.handle_product(product))

        # Use more_itertools.chunked to split tasks into batches (e.g., of size 10)
        async for batch in chunked(tasks, 3):
            results = await asyncio.gather(*batch)

            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f'Error handling product: {result}')

        try:
            await self.process_queue()
        except Exception as e:
            self.logger.error(f'Error processing queue: {e}')

    async def handle_product(self, product: dict[str, Any]):
        if product['item_type'] not in [1]:
            return None

        # Add the disclaimer to the product description
        if product.get('disclaimer_text'):
            product[
                'description'
            ] = f"{product['description'] if product['description'] else ''}\n{product['disclaimer_text']}".strip()

        cleaned_product = {
            'product_name': product['name'],
            'brand_names': product['brand'],
            'sale_story': product['sale_story'],
            'sale_price': product.get('current_price', None),
            'pre_price_text': product.get('pre_price_text', ''),
            'price_text': product.get('price_text', ''),
            'sale_amount_off': product.get('dollars_off', ''),
            'original_price': product.get('original_price', ''),
            'description': product.get('description', ''),
            'valid_from': product['valid_from'],
            'valid_to': product['valid_to'],
        }

        self.processing_queue.append(cleaned_product)
