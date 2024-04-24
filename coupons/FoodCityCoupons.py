import re
import time
import uuid

import httpx
from bs4 import BeautifulSoup

from stores.lib.BaseStore import CouponBaseStore
from utils.config import get_config


class FoodCityCoupons(CouponBaseStore):
    _store_name: str = 'foodcity-coupons'
    processing_queue: list = []
    store_code: str = None
    device_id: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        store_name = self._store_name.split('-')[0]
        config = get_config()

        if not config.has_section(store_name):
            raise Exception(
                f'No section found for {store_name} in config.ini - please add one.'
            )

        self.store_code = config[store_name]['store_code']
        self.device_id = uuid.uuid4().hex

    async def scrape(self):
        page_num = 1

        max_pages = -1
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            while page_num <= max_pages or max_pages == -1:
                url = f'https://www.foodcity.com/index.php?vica=ctl_coupons&vicb=loadMainContainerAndFilters&vicc=a&fromDash=0&page={page_num}&group=available&sorttype[]=bm&_={int(time.time() * 1000)}'

                response = await client.get(
                    url,
                )

                data = response.json()

                main_html = data['main']

                bs = BeautifulSoup(main_html, 'html.parser')

                coupon_containers = bs.find_all(
                    'div', {'id': 'sysModalDialogCouponsContentInfoAnchor'}
                )

                for coupon_container in coupon_containers:
                    raw_text = coupon_container.text
                    raw_text = re.sub(r'UPCs:\s+(.*?)\n*', '', raw_text)
                    raw_text = raw_text.strip()
                    coupon = {'raw_text': raw_text}

                    if coupon_container.find('.exp-date'):
                        coupon['valid_to'] = coupon_container.find(
                            '.exp-date'
                        ).text

                    self.processing_queue.append(coupon)

                if max_pages == -1:
                    max_pages = bs.find('input', {'id': 'hdnPageCount'})
                    if max_pages:
                        max_pages = int(max_pages.attrs['value'])
                    else:
                        max_pages = 1

                page_num += 1

        await self.process_queue()
