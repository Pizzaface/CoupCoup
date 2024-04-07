import asyncio
import dateutil
import httpx

import re
from datetime import datetime
from bs4 import BeautifulSoup
from more_itertools import chunked

from stores.lib.BaseStore import CouponBaseStore
from utils.call_ai_model_gemini import extract_products_using_gemini, GeminiCallInput


class NewspaperCoupons(CouponBaseStore):
    url: str = 'https://grocery-coupons-guid.com/couponing-resources/sunday-coupon-inserts-schedule/'
    _store_name: str = 'newspaper-coupons'

    async def fetch(self, url):
        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            response = await client.get(
                url,
                headers={
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
                },
            )
            return response.content

    def __str__(self):
        return self._store_name

    async def scrape(self):
        all_cells = []
        # Make a request to the website and get the HTML content
        page_content = await self.fetch(self.url)

        # Parse the HTML using Beautiful Soup
        soup = BeautifulSoup(page_content, 'html.parser')

        # Find all the links in the table and loop through them
        table = soup.find('div', {'class': 'entry-content'})
        hrefs = [
            link.attrs['href']
            for link in table.find_all('a')
            if re.match('.*/[a-z]*-\d+-\d+-\d+/', link.attrs['href'])
        ]

        async with httpx.AsyncClient(timeout=90, transport=self.httpx_transport) as client:
            responses = await asyncio.gather(
                *[
                    client.get(
                        href,
                        headers={
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
                        },
                        timeout=60,
                    )
                    for href in hrefs
                ]
            )

        # Loop through each response and extract the data
        await self._clean_coupons(all_cells, responses)

        for cell_chunk in chunked(all_cells, 2):
            tasks = [
                extract_products_using_gemini(
                    GeminiCallInput(
                        user_input=cell_chunk,
                        logger=self.logger,
                        prompt_jinja_template_path='get_individual_products.jinja'
                    )
                )
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, results in enumerate(results):
                if isinstance(results, Exception):
                    self.logger.error(f'Error handling product: {results}')
                    continue

                products, user_input = results

                for prd_id, product in enumerate(products):
                    if not product.get('brand_name'):
                        product['brand_name'] = cell_chunk[prd_id]['raw_text']

                    product['valid_from'] = 'N/A'
                    product['requires_store_card'] = False
                    self.add_row_to_store_worksheet(product)

    async def _clean_coupons(self, all_cells, responses):
        for response in responses:
            html_content = response.content
            soup = BeautifulSoup(
                html_content, 'html.parser', from_encoding='latin1'
            )
            table = soup.find('table', class_='DescTable')

            rows = table.find_all('tr')
            cols = [head.text for head in table.find_all('th')]

            for row in rows:
                cells = row.find_all('td')

                if len(cells) < len(cols):
                    continue

                exp = (
                    cells[cols.index('Exp')]
                    .text.removeprefix('(')
                    .removesuffix(')')
                )
                current_year = datetime.today().year
                exp = f'{exp}/{current_year}'
                if exp:
                    exp = dateutil.parser.parse(exp)
                    if exp <= datetime.today():
                        continue
                else:
                    continue

                all_cells.append(
                    {
                        'raw_text': cells[0].text,
                        'sale_amount_off': cells[1].text.split('/')[0],
                        'required_purchase_quantity': cells[1].text.split('/')[
                            1
                        ],
                        'deal_type': 'COUPON',
                        'valid_from': datetime.today().strftime('%Y-%m-%d'),
                        'valid_to': exp.strftime('%Y-%m-%d'),
                    }
                )
