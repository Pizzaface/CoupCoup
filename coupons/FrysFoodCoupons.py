import httpx
from dateutil.parser import parse

from stores.lib.BaseStore import CouponBaseStore


class FrysFoodCoupons(CouponBaseStore):
    _store_name: str = 'frysfood-coupons'
    processing_queue: list = []

    async def scrape(self):
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:

            params = {
                'couponsCountPerLoad': '500',
                'sortType': 'relevance',
                'newCoupons': 'false',
            }

            json_data = {
                'displayedCoupons': [],
                'recentlyClippedCoupons': [],
            }

            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://www.frysfood.com',
                'referer': 'https://www.frysfood.com/savings/cl/coupons/',
                'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            }

            response = await client.post(
                'https://www.frysfood.com/cl/api/coupons',
                params=params,
                json=json_data,
                timeout=90,
                headers=headers,
            )

            coupons = response.json()['data'].get('coupons', [])

            if not coupons:
                self.logger.error('No coupons found')
                return

            self.logger.info(f'Found {len(coupons)} coupons')

            for coupon in coupons.values():
                try:
                    coupon['expirationDate'] = parse(
                        coupon['expirationDate']
                    ).isoformat()
                except Exception as e:
                    pass

                parsed_coupon = {
                    'raw_text': coupon.get('title', '')
                    + ' '
                    + coupon['shortDescription']
                    + ' '
                    + coupon.get('requirementDescription', ''),
                    'brand_name': coupon['brandName'],
                    'expiration_date': coupon['expirationDate'],
                    'required_purchase_quantity': int(
                        coupon.get('requiredQuantity', {}).get('quantity', 0)
                    ),
                    'deal_type': 'COUPON'
                    if coupon['longDescription'] != ''
                    else 'MANUFACTURER_COUPON',
                }

                self.processing_queue.append(parsed_coupon)

        await self.process_queue()


async def main():
    async with FrysFoodCoupons() as store:
        await store.scrape()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
