import asyncio

import httpx
from loguru import logger

from stores.lib.BaseStore import Store


class HEB(Store):
    _store_name: str = 'HEB'
    pages: list[str] = []
    processing_queue: list[dict] = []
    _wait_time: int = 15

    async def process_page(self, url: str, headers: dict):
        page_data = None
        response = None
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            try:
                response = await client.post(url, headers=headers, timeout=90)
                page_data = response.json()
            except Exception as e:
                if isinstance(e, (httpx.ConnectTimeout, httpx.ReadTimeout)):
                    logger.error(f'Error accessing H-E-B flyer page: {e}')
                    return await self.process_page(url, headers)
                elif response and response.text.startswith('<!DOCTYPE html>'):
                    logger.error(
                        f'Could not access H-E-B flyer page. This is likely due to a CAPTCHA.'
                    )

                return

            if not response or not page_data:
                return

            if not self.pages:
                self.pages = [
                    page['to']
                    for page in page_data['props']['pageProps']['pages'][1:]
                ]

            self.processing_queue.extend(
                page_data['props']['pageProps']['products']
            )

        self.logger.info(f'Grabbed {len(self.processing_queue)} items so far - waiting {self._wait_time} seconds...')
        await asyncio.sleep(self._wait_time)

    async def handle_flyers(self):
        url = 'https://www.heb.com/_exo/data/collections/weekly-ad'
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://www.heb.com/',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }

        await self.process_page(url, headers)

        prev_page = url
        for page in self.pages:
            headers['referer'] = prev_page
            await self.process_page(f'{url}{page}', headers)
            prev_page = f'{url}{page}'

        await self.process_queue()
