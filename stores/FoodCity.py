from __future__ import annotations

from pyppeteer import launch
import asyncio

from pyppeteer.browser import Browser
from pyppeteer.page import Page

from stores.lib.BaseStore import Store
import unicodedata

from stores.lib.BrowserStore import BrowserStore
from utils.config import get_config

PUBLIX_AD_URL = 'https://accessibleweeklyad.publix.com/'


class FoodCity(BrowserStore):
    categories: list[str] = []
    weekly_ad: list[dict] = []
    processing_queue: list[dict] = []
    store_code: str | None = None

    _store_name: str = 'foodcity'

    @property
    def url(self) -> str:
        return f'https://www.foodcity.com/circulars/weekly/{self.store_code}/?searchDisplay=grid&Clear=1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_code = self.store_config.get('store_code')

        if not self.store_code:
            raise Exception('FoodCity store code not found in config')

    async def handle_flyers(self):
        await self.load_page()
        await self.page.waitForSelector('#hdnPageCount')
        total_page_input = await self.page.J('#hdnPageCount')

        current_page = 1

        while current_page <= await self._get_total_pages(total_page_input):
            show_more_button = await self.page.J('#showMore')
            if not show_more_button:
                break

            try:
                await show_more_button.click()
            except Exception:
                break

            await asyncio.sleep(5)
            current_page += 1

        items = await self.page.JJ('.tile-item__product')

        tasks = [self.handle_item(item) for item in items]
        await asyncio.gather(*tasks, return_exceptions=True)

        await self.browser.close()

        await self.process_queue()

    @classmethod
    async def _get_total_pages(cls, total_page_input):
        return int(await cls.get_value(total_page_input))

    async def handle_item(self, item):
        if not item or ((await item.J('.dead-end-content')) is not None):
            return

        title = await item.J('.tile-item__product__title')
        price = await item.J('.tile-item__product__price')
        size = await item.J('.tile-item__product__size')
        brand = await item.J('.tile-item__product__brand')

        if not title or not price or not size:
            return

        item_info = {
            'product_name': await self.get_title(title),
            'price': await self.get_inner_text(price),
            'size': await self.get_inner_text(size),
            'brand': await self.get_inner_text(brand),
        }
        if not title or not price or not size:
            return

        item_info['size'] = (
            unicodedata.normalize('NFKD', item_info['size'])
            .encode('latin1')
            .decode('latin1')
        )
        item_info['brand'] = (
            unicodedata.normalize('NFKD', item_info['brand'])
            .encode('latin1')
            .decode('latin1')
        )

        self.processing_queue.append(item_info)
