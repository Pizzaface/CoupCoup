import datetime

import httpx
from dateutil.parser import parse

from stores.lib.BaseStore import CouponBaseStore


class WalgreensCoupons(CouponBaseStore):
    _store_name: str = 'walgreens-coupons'
    processing_queue: list = []

    async def scrape(self):
        json_data = {'recSize': 50, 'recStartIndex': 0, 'u': 107}
        total_coupons = 1
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            while json_data['recStartIndex'] < total_coupons:
                response = await client.post(
                    'https://www.walgreens.com/offers/v1/svc/coupons/recommended',
                    timeout=90,
                    json=json_data,
                )

                try:
                    coupons = response.json().get('coupons', [])
                except Exception as e:
                    self.logger.error('Error parsing Walgreens coupons')
                    return

                if not coupons:
                    self.logger.error('No coupons found')
                    return

                await self._clean_coupons(coupons)

                total_coupons = (
                    response.json().get('summary', {}).get('totalRecords', 1)
                )
                json_data['recStartIndex'] += 50

        self.logger.info(f'Found {len(self.processing_queue)} coupons')
        await self.process_queue()

    async def _clean_coupons(self, coupons):
        for coupon in coupons:
            try:
                coupon['expiryDate'] = parse(
                    coupon['expiryDate']
                    if len(coupon['expiryDate'].split('/')) == 3
                    else coupon['expiryDate']
                         + datetime.datetime.today().strftime('/%Y')
                ).isoformat()
            except Exception as e:
                pass

            parsed_coupon = {
                'raw_text': coupon.get('summary', '')
                            + ' '
                            + coupon['description']
                            + ' '
                            + coupon.get('offerDisclaimer', ''),
                'product_name': coupon['summary'],
                'brand_name': coupon['brandName'],
                'valid_from': coupon.get(
                    'activeDate', coupon.get('offerActiveDate', 'N/A')
                ),
                'valid_to': coupon['expiryDate'],
                'required_purchase_quantity': int(
                    coupon.get('minQty', 1)
                ),
                'deal_type': 'COUPON'
                if coupon['source'] == 'Walgreens IVC'
                else 'MANUFACTURER_COUPON',
            }

            self.processing_queue.append(parsed_coupon)
