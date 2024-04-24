import datetime

import httpx
from dateutil.parser import parse

from stores.lib.BaseStore import CouponBaseStore


class MeijerCoupons(CouponBaseStore):
    _store_name: str = 'meijer-coupons'
    processing_queue: list = []
    store_code: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.store_code = self.store_config.get('store_code')

        if not self.store_code:
            raise Exception(
                f'No store code found for Meijer in config.ini - please add one.'
            )

    async def scrape(self):
        json_data = {
            'searchCriteria': '',
            'sortType': 0,
            'clippedFromTS': None,
            'pageSize': 48,
            'currentPage': 1,
            'ceilingCount': 0,
            'ceilingDuration': 0,
            'rewardCouponId': 0,
            'categoryId': '',
            'offerClass': 1,
            'tagId': '',
            'getOfferCountPerDepartment': False,
            'upcId': 0,
            'showClippedCoupons': False,
            'showOnlySpecialOffers': False,
            'showRedeemedOffers': False,
            'offerIds': [],
            'showBackToAllCoupons': False,
            'type': 6,
        }

        cookies = {
            'meijer-store': self.store_code,
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache, no-store, must-revalidate, max-age=-1, private',
            'content-type': 'application/json',
            'dnt': '1',
            'origin': 'https://www.meijer.com',
            'pragma': 'no-cache',
            'referer': 'https://www.meijer.com/shopping/coupons.html',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }

        total_coupons = -1
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            while (
                json_data['currentPage']
                < total_coupons // json_data['pageSize']
                or total_coupons == -1
                or json_data['currentPage'] >= 10
            ):
                response = await client.post(
                    'https://www.meijer.com/bin/meijer/offer',
                    timeout=90,
                    headers=headers,
                    json=json_data,
                    cookies=cookies,
                )

                response_json = response.json()
                coupons = response_json.get('listOfCoupons', [])

                if not coupons:
                    self.logger.error('No coupons found')
                    return

                await self._clean_coupons(coupons)

                total_coupons = response_json.get('availableCouponCount', 0)
                json_data['currentPage'] += 1

        self.logger.info(f'Found {len(self.processing_queue)} coupons')
        await self.process_queue()

    async def _clean_coupons(self, coupons):
        for coupon in coupons:
            offer = coupon.get('offer', {})
            try:
                offer['redemptionEndDate'] = parse(
                    offer['redemptionEndDate']
                    if len(offer['redemptionEndDate'].split('/')) == 3
                    else offer['redemptionEndDate']
                         + datetime.datetime.today().strftime('/%Y')
                ).isoformat()
            except Exception as e:
                pass

            parsed_coupon = {
                'raw_text': offer.get('title', '')
                            + ' '
                            + offer['description']
                            + ' '
                            + offer.get('termsAndConditions', ''),
                'product_name': offer['description'],
                'valid_from': offer.get('redemptionStartDate', 'N/A'),
                'valid_to': offer['redemptionEndDate'],
                'deal_type': 'MANUFACTURER_COUPON'
                if offer.get('manufacturerCoupon', False)
                else 'COUPON',
            }

            self.processing_queue.append(parsed_coupon)
