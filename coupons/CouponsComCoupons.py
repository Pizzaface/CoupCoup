import httpx

from stores.lib.BaseStore import CouponBaseStore


class CouponsComCoupons(CouponBaseStore):
    _store_name: str = 'coupons-com'
    processing_queue: list = []

    async def scrape(self):
        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'dnt': '1',
            'origin': 'https://www.coupons.com',
            'referer': 'https://www.coupons.com/printable/beverage-coupons',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }

        json_data = {
            'guid': 'G',
            'pageType': 'Pah',
        }

        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            response = await client.post(
                'https://www.coupons.com/api/getCoupons',
                headers=headers,
                json=json_data,
            )

            data = response.json()

        for offer in data['offers']:
            item = offer['offer']
            parsed_coupon = {
                'valid_from': item['activation_date'],
                'valid_to': item['expiration_date'],
                'brand_name': item['brand'],
                'raw_text': item['offer_print_detail']
                + item['offer_disclaimer'],
                'deal_type': 'MANUFACTURER_COUPON',
                'description': item.get('short_description', '')
                + ' '
                + item.get('offer_disclaimer', ''),
                'minimum_purchase_quantity': item['reward_category'].get(
                    'required_quantity', 1
                ),
                'amount_get_free': item['reward_category'].get(
                    'reward_quantity', 0
                ),
            }

            if parsed_coupon not in self.processing_queue:
                self.processing_queue.append(parsed_coupon)

        await self.process_queue()
