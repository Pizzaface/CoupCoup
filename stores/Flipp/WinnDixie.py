from __future__ import annotations
from stores.Flipp.Flipp import Flipp


class WinnDixie(Flipp):
    @property
    def _store_name(self) -> str:
        return 'winndixie'
