from __future__ import annotations

from stores.Flipp.Flipp import Flipp


class KrogerMidAtlantic(Flipp):
    @property
    def _store_name(self) -> str:
        return 'krogermidatlantic'
