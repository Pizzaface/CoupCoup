from __future__ import annotations

from datetime import datetime

import dateutil.parser
import httpx

from utils.config import get_config
from .lib.BaseStore import Store


class Walgreens(Store):
    _store_name: str = 'walgreens'
    url: str = 'https://www.walgreens.com/storelistings/storesbystore.jsp'
    processing_queue: list[dict] = []
    store_code: str | None = None
    collection_ids: list[str] = []
    page_ids: list[str] = []

    start_date: datetime | None = None
    end_date: datetime | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.store_code = self.store_config.get('store_code')

    async def handle_flyers(self):
        await self.grab_collection_ids()
        await self.grab_sub_collections()
        await self.grab_products()

        await self.process_queue()

    async def grab_collection_ids(self):
        url = 'https://wag-dwa-api-prod.przone.net//api/wag/dwa/circular'
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
        json_data = {
            'containerId': 'dwa_container',
            'clippedCoupons': None,
            'search': None,
            'seachOfferCodes': [],
            'selectedOffer': '',
            'store': {
                'storeNumber': self.store_code,
            },
            'user': {
                'brid': None,
                'firstName': None,
                'affinityOffers': [],
                'clippedCoupons': None,
            },
            'circularId': None,
            'isMobileView': False,
            'customerid': 'N',
            'personalizedOffers': 'N',
            'selectedCategory': '',
            'viewMode': '',
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url, headers=headers, json=json_data
            )

            if response.status_code != 200:
                raise Exception(
                    f'Failed to grab collections: {response.status_code}'
                )

            data = response.json()

        if not data.get('pages'):
            raise Exception('No pages found in response')

        self.start_date = dateutil.parser.parse(data['startDate'])
        self.end_date = dateutil.parser.parse(data['endDate'])

        for page in data['pages']:
            if page['isActive'] and not page['isHidden']:
                self.collection_ids.append(page['collectionId'])
                self.page_ids.append(page['circularPageId'])

    async def grab_sub_collections(self):

        for collection_id in self.page_ids:
            url = f'https://wag-dwa-api-prod.przone.net//api/wag/dwa/circular/page?pageid={collection_id}'

            # Define the headers
            headers = {
                'accept': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            }

            json_body = {
                'containerId': 'dwa_container',
                'clippedCoupons': None,
                'search': None,
                'seachOfferCodes': [],
                'selectedOffer': '',
                'store': {'storeNumber': self.store_code},
                'user': {
                    'brid': None,
                    'firstName': None,
                    'affinityOffers': [],
                    'clippedCoupons': [],
                },
                'circularId': None,
                'isMobileView': False,
                'customerid': 'N',
                'personalizedOffers': 'N',
                'selectedCategory': '',
                'viewMode': '',
            }

            async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
                response = await client.post(
                    url, headers=headers, json=json_body
                )

                if response.status_code != 200:
                    raise Exception(
                        f'Failed to grab subcollections: {response.status_code}'
                    )

                data = response.json()

                subcollections = data.get('config', {}).get(
                    'subcollections', []
                )

                for subcollection in subcollections:
                    self.collection_ids.append(
                        subcollection['collectionId']
                    )

    async def grab_products(self):
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            headers = {
                'accept': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            }

            json_body = {
                'containerId': 'dwa_container',
                'clippedCoupons': None,
                'search': None,
                'seachOfferCodes': [],
                'selectedOffer': '',
                'store': {'storeNumber': self.store_code},
                'user': {
                    'brid': None,
                    'firstName': None,
                    'affinityOffers': [],
                    'clippedCoupons': [],
                },
                'circularId': None,
                'isMobileView': False,
                'customerid': 'N',
                'personalizedOffers': 'N',
                'selectedCategory': '',
                'viewMode': '',
            }
            for collection_id in self.collection_ids:
                url = f'https://wag-dwa-api-prod.przone.net//api/wag/dwa/collection?collectionid={collection_id}&store={self.store_code}'

                response = await client.post(
                    url, headers=headers, json=json_body
                )

                if response.status_code != 200:
                    continue

                data = response.json()

                offers = data.get('offers', [])

                await self.clean_coupons(offers)

    async def clean_coupons(self, offers):
        for offer in offers:
            if offer['offerType'] not in ['offer']:
                continue

            cleaned_offer = {}
            dataColumns = offer.get('dataColumns', {})
            if dataColumns:
                cleaned_offer['info'] = offer.get('pricing_header')
                if 'BOGOPercentOff' in dataColumns:
                    cleaned_offer[
                        'deal_type'
                    ] = 'BUY_X_GET_Y_AT_Z_PER_OFF'
                elif 'BOGOAmountOff' in dataColumns:
                    cleaned_offer[
                        'deal_type'
                    ] = 'BUY_X_GET_Y_AT_Z_OFF'

                if 'Quantity' in dataColumns:
                    cleaned_offer[
                        'required_purchase_quantity'
                    ] = dataColumns['Quantity']

                cleaned_offer['description'] = (
                        offer.get('pricingTemplateName', '')
                        + ' '
                        + offer.get('pricingBody', '')
                        + '\n'
                        + offer.get('disclaimerText', '')
                )
                cleaned_offer.update(
                    {k: v for k, v in dataColumns.items() if v}
                )
                self.processing_queue.append(cleaned_offer)
