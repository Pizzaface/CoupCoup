from __future__ import annotations

import asyncio

from pyppeteer.browser import Browser
from pyppeteer.page import Page

from stores.lib.BrowserStore import BrowserStore

PUBLIX_AD_URL = 'https://accessibleweeklyad.publix.com/'


class Publix(BrowserStore):
    _browser: None | Browser = None
    _page: None | Page = None
    store_code: str | None = None

    categories: list[str] = []
    weekly_ad: list[dict] = []

    processing_queue: list[dict] = []

    _store_name: str = 'publix'

    @property
    def url(self) -> str:
        return f'{PUBLIX_AD_URL}PublixAccessibility/Entry/LandingContent?storeid={self.store_code}&sneakpeek=N&listingid=0'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_code = self.store_config.get('store_code')

        if not self.store_code:
            raise Exception('Publix store code not found in config')

    async def handle_flyers(self):
        await self.load_page()

        # The left column of the page is the departments
        left_col = await self._page.querySelector('.leftcolumn')

        departments = await left_col.querySelectorAll('.listing')

        self.categories = await self._get_categories(departments)

        # Loop through each department
        for category in self.categories:
            try:
                await self.page.goto(category, waitUntil='networkidle2')
            except Exception as e:
                print(e)
                continue

            await self.page.waitForSelector('.gridpage')

            items = await self.page.querySelectorAll('.unitB')

            # Gather all handle_item tasks
            tasks = [self.handle_item(item) for item in items]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Process the queue
        await self.process_queue()

    @staticmethod
    async def _get_categories(departments):
        return [
            await (await department.getProperty('href')).jsonValue()
            for department in departments
        ]

    async def handle_item(self, item):
        item_info = [
            (
                await (await info_point.getProperty('textContent')).jsonValue()
            ).strip()
            for info_point in await item.querySelectorAll('div')
        ]

        self.processing_queue.append(
            {
                'raw_text': item_info,
            }
        )
