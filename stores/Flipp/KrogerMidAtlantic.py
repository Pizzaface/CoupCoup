from __future__ import annotations

from stores.Flipp.Flipp import Flipp


class KrogerMidAtlantic(Flipp):
    @property
    def _store_name(self) -> str:
        return 'krogermidatlantic'

    @property
    def flyer_url(self) -> str:
        return f'https://dam.flippenterprise.net/flyerkit/publications/{self._store_name}?locale=en&access_token={self.access_token}&show_storefronts=true&store_code={self.store_code}&locale=en&source=hosted2'

