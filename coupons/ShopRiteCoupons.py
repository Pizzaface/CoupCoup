import re

import httpx
from dateutil.parser import parse

from stores.lib.BaseStore import CouponBaseStore


class ShopRiteCoupons(CouponBaseStore):
    _store_name: str = 'shoprite-coupons'
    processing_queue: list = []
    access_token: str = None
    store_code: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.store_code = self.store_config.get('store_code')
        if not self.store_code:
            raise Exception(
                f'No store code found for ShopRite in config.ini - please add one.'
            )

    async def scrape(self):
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            await self.get_access_token(client)

            params = {'storeId': self.store_code}

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Authorization': f'Bearer {self.access_token}',
                'Origin': 'https://shop-rite-web-prod.azurewebsites.net',
                'Referer': 'https://shop-rite-web-prod.azurewebsites.net/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }

            response = await client.get(
                'https://digitalcoupons-api-v3-prod.azurewebsites.net/api/v3/shoprite/coupons/available',
                params=params,
                timeout=90,
                headers=headers,
            )

            coupons = response.json()

        if not coupons:
            self.logger.error('No coupons found')
            return

        self.logger.info(f'Found {len(coupons)} coupons')

        for coupon in coupons:
            try:
                coupon['expiration_date'] = parse(
                    coupon['expiration_date']
                ).isoformat()
            except Exception as e:
                pass

            parsed_coupon = {
                'raw_text': coupon.get('title', '')
                + ' '
                + coupon['short_description']
                + ' '
                + coupon.get('requirement_description', ''),
                'brand_name': coupon['brand_name'],
                'expiration_date': coupon['expiration_date'],
                'deal_type': 'COUPON',
            }

            self.processing_queue.append(parsed_coupon)

        await self.process_queue()

    async def get_access_token(self, client):
        response = await client.get(
            url='https://shop-rite-web-prod.azurewebsites.net/main.217c7d548fbdc45488b3.js',
        )

        content = response.text
        token_start = re.match('.*apiToken:"(.*?)".*', content).group(1)

        headers = {
            'Authorization': token_start,
            'Content-Type': 'application/json',
        }

        response = await client.post(
            url='https://digitalcoupons-api-v3-prod.azurewebsites.net/api/v3/auth/login',
            headers=headers,
        )
        self.access_token = response.json()['access_token']
