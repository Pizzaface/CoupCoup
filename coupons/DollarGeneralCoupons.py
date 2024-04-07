import uuid

import httpx

from stores.lib.BaseStore import CouponBaseStore
from utils.config import get_config


class DollarGeneralCoupons(CouponBaseStore):
    _store_name: str = 'dollargeneral-coupons'
    base_url: str = 'https://www.dollargeneral.com/bin/omni/coupons/search'
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
        cookies = {
            'uniqueDeviceId': self.device_id,
            'authType': '0',
            's_gpv_pageName': 'Deals>coupons',
        }

        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
        }
        start_record = 0
        total_records = 1
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            while start_record < total_records and start_record % 15 == 0:
                params = {
                    'searchText': '',
                    'sortOrder': '2',
                    'sortBy': '0',
                    'numPageRecords': '15',
                    'pageIndex': str(start_record // 15),
                    'categories': '',
                    'brands': '',
                    'offerSourceType': '0',
                    'mixMode': '0',
                    'deviceId': self.device_id,
                    'isMobileDevice': 'false',
                    'clientOriginStoreNumber': self.store_code or '',
                }

                response = await client.get(
                    self.base_url,
                    cookies=cookies,
                    headers=headers,
                    params=params,
                    timeout=90,
                )

                response_json = response.json()

                pagination_info = response_json.get('PaginationInfo', {})
                total_records = pagination_info.get('TotalRecords', 0)

                for coupon in response_json.get('Coupons', []):
                    to_process = {
                        'raw_text': coupon.get('OfferSummary', '')
                        + coupon.get('OfferDescription', '')
                        + coupon.get('OfferDisclaimer', ''),
                        'brand_name': coupon.get('BrandName', '')
                        + coupon.get('Companyname', 'N/A'),
                        'product_name': coupon.get('BrandName', 'N/A'),
                        'sale_amount_off': coupon.get('SaleAmountOff', 'N/A'),
                        'required_purchase_quantity': coupon.get(
                            'MinQuantity', 'N/A'
                        ),
                        'deal_type': 'COUPON'
                        if coupon.get('IsManufacturerCoupon', -1) == 0
                        else 'MANUFACTURER_COUPON',
                        'description': coupon.get('OfferDescription', '')
                        + ' '
                        + coupon.get('OfferDisclaimer', ''),
                        'valid_from': coupon.get('OfferActivationDate', 'N/A'),
                        'valid_to': coupon.get('OfferExpirationDate', 'N/A'),
                    }

                    if to_process not in self.processing_queue:
                        self.processing_queue.append(to_process)

                start_record += len(response_json.get('Coupons', []))

        await self.process_queue()
