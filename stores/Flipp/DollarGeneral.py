from __future__ import annotations
from stores.Flipp.Flipp import Flipp
from typing import Any


class DollarGeneral(Flipp):
    _store_name: str = 'dollargeneral'
    current_flyer_id: int | None = None
    processing_queue: list[dict] = []

    async def handle_flyers(self) -> None:
        flyers = await self.grab_flyers()
        for flyer in flyers:
            if flyer['name'] != 'Dollar General Weekly Ad':
                continue

            self.flyer_ids_to_process.append(flyer['id'])

        if not self.flyer_ids_to_process:
            raise Exception('Could not locate Weekly Ad flyer')

        for flyer_id in self.flyer_ids_to_process:
            self.current_flyer_id = flyer_id
            async for product in self.grab_sales():
                try:
                    await self.handle_product(product)
                except Exception as e:
                    print(f'Error handling product: {e}')

        await self.process_queue()

    async def handle_product(self, product: dict[str, Any]) -> None:
        if product['name'] is None:
            return None

        if (
            product.get('sale_story')
            and 'switch to save' in product['sale_story'].lower()
        ):
            return None

        self.processing_queue.append(product)
