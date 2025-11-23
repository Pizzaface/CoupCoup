# Import Flipp stores (these should always work)
from stores.Flipp import *

# Import standalone stores with optional dependency handling
__all__ = []

try:
    from stores.Publix import Publix
    __all__.append('Publix')
except ImportError:
    # Publix requires pyppeteer which may not be installed
    pass

try:
    from stores.FoodCity import FoodCity
    __all__.append('FoodCity')
except ImportError:
    pass

try:
    from stores.Ingles import Ingles
    __all__.append('Ingles')
except ImportError:
    pass

try:
    from stores.Walgreens import Walgreens
    __all__.append('Walgreens')
except ImportError:
    pass
