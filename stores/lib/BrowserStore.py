import asyncio

from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.page import Page

from stores.lib.BaseStore import Store
from tqdm.asyncio import tqdm as tqdm_asyncio


class BrowserStore(Store):
    _browser: None | Browser = None
    _page: None | Page = None
    headless: bool = True

    @property
    def browser(self):
        return self._browser

    @property
    def page(self):
        return self._page

    @property
    def url(self):
        raise NotImplementedError

    async def __aenter__(self):
        self.reset_worksheet()
        self._browser: Browser = await launch(
            {
                'headless': self.headless,
            }
        )
        self._page = await self._browser.newPage()

        self.pbar = tqdm_asyncio([], desc=self._store_name, leave=False)
        self.pbar.disable = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._browser.close()

    async def load_page(self, is_retry: bool = False, wait_until: str = 'networkidle2'):
        try:
            await self.page.goto(self.url, waitUntil=wait_until)
        except Exception as e:
            self.logger.warning(f'Error loading page: {e}')

            await asyncio.sleep(5)

            if not is_retry:
                return await self.load_page(is_retry=True)

            self.logger.error('Error loading page on retry')
            return

    async def query_selector(self, selector: str):
        return await self.page.querySelector(selector)

    async def query_selector_all(self, selector: str):
        return await self.page.querySelectorAll(selector)

    @staticmethod
    async def get_attribute(element, attribute: str):
        return await element.getProperty(attribute)

    @staticmethod
    async def get_title(element):
        if not element:
            return None

        title = await element.getProperty('title')
        return await title.jsonValue()

    @staticmethod
    async def get_inner_text(element):
        if not element:
            return None

        inner_text = await element.getProperty('innerText')
        return await inner_text.jsonValue()

    @staticmethod
    async def get_outer_html(element):
        return await element.getProperty('outerHTML')

    @staticmethod
    async def get_class_name(element):
        return await element.getProperty('className')

    @staticmethod
    async def get_tag_name(element):
        return await element.getProperty('tagName')

    @staticmethod
    async def get_value(element):
        if not element:
            return None

        value_property = await element.getProperty('value')
        return await value_property.jsonValue()

    @staticmethod
    async def get_style(element):
        return await element.getProperty('style')

    async def reset_browser(self):
        if self.browser:
            await self.browser.close()
            self._browser = None

        self._browser: Browser = await launch(
            {
                'headless': self.headless,
            }
        )
