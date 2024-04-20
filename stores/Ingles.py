from __future__ import annotations

from loguru import logger
import asyncio

from stores.lib.BrowserStore import BrowserStore


class Ingles(BrowserStore):
    _store_name: str = 'ingles'
    categories: list[str] = []
    processing_queue: list[dict] = []
    store_code: str | None = None
    ingles_session_id: str | None = None

    @property
    def url(self) -> str:
        return 'https://flyer.inglesads.com/noncard/ThisWeek/ReviewAllSpecials.jsp'

    async def __aenter__(self):
        try:
            await super().__aenter__()
        except Exception as e:
            logger.error(f'Error initializing browser: {e} - retrying')
            await asyncio.sleep(5)
            return await self.__aenter__()

        self.store_code = self.store_config.get('store_code')
        self.ingles_session_id = self.store_config.get('session_id')

        if not self.store_code or not self.ingles_session_id:
            raise Exception(
                'Ingles store code or session id not found in config'
            )

        await self.page.setCookie(
            {
                'name': 'StoreNumberCK',
                'value': self.store_code,
                'domain': 'flyer.inglesads.com',
            }
        )
        await self.page.setCookie(
            {
                'name': 'JSESSIONID',
                'value': self.ingles_session_id,
                'domain': 'flyer.inglesads.com',
            }
        )

        await self.load_page(wait_until='domcontentloaded')
        await asyncio.sleep(5)
        return self

    async def handle_flyers(self):
        try:
            # We reload the URL here because Ingles doesn't allow us to navigate to the URL directly, it will always take us to the home page first
            await self.load_page(wait_until='domcontentloaded')

            await self.page.waitForSelector(
                '#specialsNoBG > tbody > tr > td > div > div > div.container_depts'
            )
        except Exception as e:
            logger.error(f'Error loading page: {e} - retrying')
            await asyncio.sleep(5)
            await self.reset_browser()
            return await self.handle_flyers()

        await self._extract_categories()

        # Loop through each department
        for category in self.categories:
            logger.info(
                f'Processing category: {category} for {self._store_name}'
            )
            await self.page.goto(
                category, waitUntil='domcontentloaded', timeout=90000
            )

            # Get the products
            products = await self.page.querySelectorAll('.offerblock')

            for product in products:
                desc_text, price_text, title_text = await self.handle_item(product)

                self.processing_queue.append(
                    {
                        'product_name': title_text,
                        'description': desc_text,
                        'price': price_text,
                    }
                )

        await self.browser.close()
        await self.process_queue()

    async def _extract_categories(self):
        left_col = (
            await self.page.frames[0].querySelector('.container_depts')
        ).asElement()
        departments = await left_col.querySelectorAll('.dept_name > a')
        self.categories = [
            await self._get_department_link(department)
            for department in departments
        ]

    @staticmethod
    async def _get_department_link(department):
        return str(await (await department.getProperty('href')).jsonValue())

    @classmethod
    async def handle_item(cls, product):
        title = await product.J('.title')
        price = await product.J('.priceblock')
        desc = await product.J('.desc')
        title_text = await cls.get_inner_text(title)
        price_text = await cls.get_inner_text(price)
        desc_text = await cls.get_inner_text(desc)
        return desc_text, price_text, title_text


async def main():
    async with Ingles() as p:
        await p.get_sales()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
