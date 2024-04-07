import uuid

import httpx

from stores.lib.BaseStore import CouponBaseStore


class FoodLionCoupons(CouponBaseStore):
    _store_name: str = 'foodlion-coupons'
    processing_queue: list = []
    store_code: str = None
    device_id: str = None
    base_url: str = None

    def __init__(self):
        super().__init__()
        self.base_url = f'https://foodlion.com/apis/circular-coupons/v1/FDLN/offers/anonymous'

    async def scrape(self):
        cookies = {
            'optimizelyEndUserId': 'oeu1711679203155r0.7757359292261279',
            'cf_clearance': 'Ya2l5tovAfDLBShAocrY9x6GTO6LUDQfoGCxs.AILhQ-1712007576-1.0.1.1-lnQYtFUwfsjmGhlvPzWPd4wh7sSI08cuOcK55JIhprf3iYLsTstTF5D_nGuKR76tEVmyH1N.YKRifS5rP649mA',
            'OptanonConsent': 'isGpcEnabled=0&datestamp=Mon+Apr+01+2024+17%3A39%3A45+GMT-0400+(Eastern+Daylight+Time)&version=202209.2.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=SPD_BG%3A0%2CC0004%3A0%2CC0005%3A0&AwaitingReconsent=false',
            'datadome': 'aTkMdtE6GZVeJPSK1ZtlOA8SxdM4dU0S~EVKeimNkbfSjVEsc4fm1Bz5C8X2qed8PmzxepHeH8mNk4aj2UY~zTCz09asAQ3Q7hazCIRqdyleWBoOJH6QE2485FlbJ5gC',
            '_dd_s': 'rum=1&id=2e9cc7bb-5eff-4d1b-b32a-a9bab5215a16&created=1712007577561&expire=1712008844653',
        }

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'dnt': '1',
            'if-modified-since': 'Mon, 01 Apr 2024 21:33:51 GMT',
            'sec-ch-device-memory': '8',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-arch': '"x86"',
            'sec-ch-ua-full-version-list': '"Google Chrome";v="123.0.6312.86", "Not:A-Brand";v="8.0.0.0", "Chromium";v="123.0.6312.86"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'Referer': 'https://foodlion.com/coupons/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                cookies=cookies,
                timeout=90,
            )

            response_json = response.json()

            for coupon in response_json.get('offers', []):
                to_process = {
                    'raw_text': coupon.get('name', '')
                    + ' '
                    + coupon.get('title', '')
                    + coupon.get('description', '')
                    + coupon.get('legalText', ''),
                    'brand_name': coupon.get('name', ''),
                    'description': coupon.get('description', '')
                    + ' '
                    + coupon.get('legalText', ''),
                    'required_purchase_quantity': coupon.get(
                        'maxDiscount', 'N/A'
                    ),
                    'deal_type': 'COUPON',
                    'valid_from': coupon.get('startDate', 'N/A'),
                    'valid_to': coupon.get('expirationDate', 'N/A'),
                }

                if to_process not in self.processing_queue:
                    self.processing_queue.append(to_process)

        await self.process_queue()


async def main():
    async with FoodLionCoupons() as store:
        await store.scrape()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
