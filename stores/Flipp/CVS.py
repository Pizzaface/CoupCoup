from __future__ import annotations
from typing import Any
from stores.Flipp.Flipp import Flipp


class CVS(Flipp):
    _store_name: str = 'cvspharmacy'

    async def handle_product(self, product: dict[str, Any]):
        if product.get('sku') is None or product.get('item_type') == 7:
            return None

        return await super().handle_product(product)
