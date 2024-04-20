import asyncio
import undetected_chromedriver as uc
import csv
import os

from selenium.common import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
import asyncio

from stores.lib.BaseStore import Store


class Walmart(Store):
    _store_name: str = 'Walmart'
    processing_queue: list[dict] = []

    async def __aenter__(self):
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--window-size=1920,1080')
        options.headless = False
        self.driver = uc.Chrome(options=options)
        return self

    def setup(self):
        self.driver.get("https://www.walmart.com/")
        self.driver.implicitly_wait(30)
        self.driver.find_element(By.CSS_SELECTOR, 'a[link-identifier="Deals"]').click()
        self.driver.implicitly_wait(30)

    async def handle_flyers(self):
        url = f"https://www.walmart.com/shop/deals/food?page=1"
        self.driver.get(url)


        while True:

            current_height = self.driver.execute_script("return document.body.scrollHeight")
            # scroll to bottom of page
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.driver.implicitly_wait(30)

            if current_height == self.driver.execute_script("return document.body.scrollHeight"):
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, "#\\30  > section > div > div > div > div > div > div:nth-child(2)")

                    if not items:
                        break  # Break if no items are found (possibly last page)

                    for item in items:
                        title_element = item.find_element(By.CSS_SELECTOR, 'span[data-automation-id="product-title"]')
                        price_element = item.find_element(By.CSS_SELECTOR, 'div[data-automation-id="product-price"]')

                        if title_element and price_element:
                            title = title_element.text
                            price = price_element.text

                            self.processing_queue.append({
                                "raw_text": title,
                                "price": price,
                                "sale type": "sale price"
                            })

                    try:
                        next_page = self.driver.find_element(By.CSS_SELECTOR, 'a[data-testid="NextPage"]')
                        # scroll into view
                        actions = ActionChains(self.driver)
                        actions.move_to_element(next_page).perform()

                        self.driver.implicitly_wait(30)
                        next_page.click()
                        self.driver.implicitly_wait(30)
                        continue
                    except NoSuchElementException:
                        break
                    except ElementClickInterceptedException:
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        self.driver.implicitly_wait(30)
                        self.driver.find_element(By.CSS_SELECTOR, 'a[data-testid="NextPage"]').click()
                        self.driver.implicitly_wait(30)
                        continue
                except Exception as e:
                    print(f"Error: {e}")

                break

        await self.process_queue()


async def main():
    store = Walmart()
    store.setup()
    await store.handle_flyers()


if __name__ == '__main__':
    asyncio.run(main())