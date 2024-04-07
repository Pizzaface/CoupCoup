import time
import uuid

import httpx
from stores.lib.BaseStore import CouponBaseStore
from utils.config import get_config


class FamilyDollarCoupons(CouponBaseStore):
    _store_name: str = 'familydollar-coupons'
    processing_queue: list = []
    store_code: str = None
    device_id: str = None

    def __init__(self):
        super().__init__()

        store_name = self._store_name.split('-')[0]
        config = get_config()

        if not config.has_section(store_name):
            raise Exception(
                f'No section found for {store_name} in config.ini - please add one.'
            )

        self.store_code = config[store_name]['store_code']
        self.device_id = uuid.uuid4().hex

    async def scrape(self):
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            url = f'https://ice-familydollar.dpn.inmar.com/v2/offers?limit=1501&&_={int(time.time() * 1000)}'

            response = await client.get(
                url,
            )

            data = response.json()

        for item in data:
            parsed_coupon = {
                'raw_text': item['description']
                + ' '
                + item.get('terms', ''),
                'brand': item['brand'],
                'expiration_date': item['expirationDate']['iso'],
                'minimum_purchase_quantity': int(item['minPurchase']),
                'deal_type': 'COUPON'
                if item['type'] != 'mfg'
                else 'MANUFACTURER_COUPON',
            }

            if parsed_coupon not in self.processing_queue:
                self.processing_queue.append(parsed_coupon)

        await self.process_queue()
