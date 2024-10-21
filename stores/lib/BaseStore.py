from __future__ import annotations

import asyncio
import json
from typing import Dict, List

import aiometer
import orjson
from httpx import AsyncHTTPTransport
from loguru import logger
from more_itertools import chunked
from pydantic import BaseModel
from tqdm.asyncio import tqdm as tqdm_asyncio

from lib.RetryTransport import RetryTransport
from lib.constants import GLOBAL_COUPON_PROVIDERS
from models.db import engine
from models.deal import Deal
from models.store import Store
from stores.lib.constants import HEADERS, FILTER_KEYS
from utils.call_ai_model_gemini import extract_products_using_gemini
from utils.config import get_config
from sqlmodel import Session, select


class StoreBase(BaseModel):
    weekly_ad: List[Dict] | None = []
    headers: List[str] = HEADERS
    filter_keys: List[str] | None = FILTER_KEYS
    _store_name: str | None = None
    store_config: Dict[str, str] | None = None
    processing_queue: list[dict] = []

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        extra = 'allow'

    def __init__(self, cm, *args, **kwargs):
        super().__init__(**kwargs)
        self.timer_cm = cm
        self.apply_config()

    def apply_config(self):
        config = get_config()
        store_name = self._store_name.lower()
        if store_name.endswith('-coupons'):
            store_name = store_name.removesuffix('-coupons')

        if store_name in config.sections():
            self.store_config = config[store_name]
        elif self._store_name.lower() not in GLOBAL_COUPON_PROVIDERS:
            raise Exception(f'{store_name} config not found - please check your config file')

        self.items_at_once = config['config'].getint('items_at_once', 5)

    async def __aenter__(self):
        self.pbar = tqdm_asyncio([], desc=self._store_name)
        self.pbar.disable = False
        self.session = Session(engine)
        self.store = self.get_or_create_store()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.session.commit()
        self.session.close()

    def get_or_create_store(self):
        query = select(Store).where(Store.name == self._store_name)
        store = self.session.exec(query).first()
        if not store:
            store = Store(name=self._store_name)
            self.session.add(store)
            self.session.commit()
        return store

    @property
    def httpx_transport(self):
        return RetryTransport(
            AsyncHTTPTransport(retries=3),
            max_attempts=10,
            retry_status_codes=[429, 500, 502, 503, 504],
        )

    @property
    def logger(self):
        logger.remove()
        logger.add(tqdm_asyncio.write, colorize=True)
        return logger.patch(lambda record: record.update(name=self._store_name))

    def add_rows(self, rows: List[Dict]):
        if not rows:
            return

        for row in rows:
            row['brand_name'] = row.pop('brand_names', row.pop('brand', None))

        rows = [{k: v for k, v in row.items() if v} for row in rows]
        self.session.add_all([Deal.model_validate({**row, 'store_id': self.store.id}) for row in rows])
        self.session.commit()

    async def process_queue(self, is_reprocess: bool = False):
        if not self.processing_queue:
            self.logger.info('No items to process')
            return

        self.logger.info(f'Processing {len(self.processing_queue)} items')
        reprocess_queue = []
        chunked_queue = list(chunked(self.processing_queue, 4))
        tasks = [
            {
                'prompt_jinja_template_path': 'get_individual_products.jinja',
                'user_input': batch,
                'logger': self.logger,
            }
            for batch in chunked_queue
        ]

        self.pbar.reset(total=len(tasks))
        self.pbar.set_description(f'Processing {self._store_name}')
        self.pbar.refresh()

        rows_to_add = []
        self.timer_cm.shift(20 * len(tasks))

        async with aiometer.amap(
            async_fn=extract_products_using_gemini,
            args=tasks,
            max_at_once=self.items_at_once,
        ) as results:
            async for result_obj in results:
                if not self.is_valid_result(result_obj):
                    continue

                self.pbar.update(1)
                self.timer_cm.shift(10)

                products, user_input = result_obj
                user_input = self.parse_user_input(user_input)

                if not products:
                    self.logger.warning(f'No products found for user input: {user_input} - adding to reprocess queue')
                    reprocess_queue.extend(user_input)
                    continue

                for product in products:
                    if self.is_invalid_product(product):
                        self.logger.debug(f'No valid data found for product: {product} - adding to reprocess queue')
                        reprocess_queue.extend(user_input)
                        continue

                    rows_to_add.extend(self.process_product(product))

                    if len(rows_to_add) >= 100:
                        self.logger.info(f'Adding {len(rows_to_add)} rows to {self._store_name}')
                        try:
                            self.add_rows(rows_to_add)
                            rows_to_add = []
                        except Exception as e:
                            self.logger.error(f'Error adding to database: {e}')
                            self.logger.error(f'Adding product to reprocess queue: {product}')
                            reprocess_queue.extend(user_input)

        if rows_to_add:
            self.logger.info(f'Adding {len(rows_to_add)} rows to {self._store_name} worksheet')
            self.add_rows(rows_to_add)

        if reprocess_queue and not is_reprocess:
            self.processing_queue = reprocess_queue
            self.logger.info(f'Reprocessing {len(reprocess_queue)} items')
            self.timer_cm.shift(20 * len(reprocess_queue))
            return await self.process_queue(is_reprocess=True)

        if reprocess_queue and is_reprocess:
            self.logger.error(f'Unable to process {len(reprocess_queue)} items after reprocessing. Please check logs.')
            self.timer_cm.shift(5)
            await asyncio.sleep(2)

        self.logger.info('Finished processing queue')

    def is_valid_result(self, result_obj):
        return not issubclass(result_obj.__class__, Exception) and isinstance(result_obj, tuple) and result_obj

    def parse_user_input(self, user_input):
        if isinstance(user_input, str):
            try:
                return orjson.loads(user_input)
            except json.JSONDecodeError:
                self.logger.error(f'Unable to decode user_input: {user_input}')
                return []
        return user_input

    def is_invalid_product(self, product):
        return all(product.get(key) in ['N/A', None, 'COUPON', 'MANUFACTURER_COUPON'] for key in self.headers)

    def process_product(self, product):
        if 'brand_names' in product:
            product['brand_name'] = product.pop('brand_names')

        brand_names = product.get('brand_name', '').split('|') if '|' in (product.get('brand_name') or '') else [product.get('brand_name')]
        return [{**product, 'brand_name': brand_name.strip()} for brand_name in brand_names if brand_name]


class CouponBaseStore(StoreBase):
    pass
