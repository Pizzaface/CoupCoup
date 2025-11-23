"""
Factory Boy factories for generating test data.
"""
import factory
from datetime import datetime, timedelta
from factory import Factory, Faker, LazyAttribute, SubFactory
from faker import Faker as FakerInstance

fake = FakerInstance()


class ProductFactory(Factory):
    """Factory for generating product data."""

    class Meta:
        model = dict

    brand_name = Faker('company')
    product_name = Faker('word')
    product_variety = LazyAttribute(
        lambda o: f"{fake.random_int(min=1, max=64)} {fake.random_element(elements=('oz', 'lb', 'pk', 'ct'))}"
    )
    description = Faker('sentence')
    required_purchase_quantity = Faker('random_int', min=1, max=5)
    required_purchase_amount = Faker('random_int', min=0, max=20)
    price = Faker('pyfloat', left_digits=2, right_digits=2, positive=True, min_value=0.5, max_value=50.0)
    sale_percent_off = 0
    sale_amount_off = 0
    sale_price = LazyAttribute(lambda o: round(o.price * 0.8, 2))
    quantity_at_sale_price = 1
    quantity_get_free = 0
    quantity_percent_off = 0
    quantity_at_amount_off = 0
    deal_type = Faker('random_element', elements=(
        'SALE_PRICE', 'PERCENT_OFF', 'AMOUNT_OFF', 'BUY_X_GET_Y_FREE'
    ))
    requires_store_card = Faker('boolean')
    valid_from = LazyAttribute(lambda o: datetime.now().strftime('%Y-%m-%d'))
    valid_to = LazyAttribute(
        lambda o: (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    )


class CouponFactory(ProductFactory):
    """Factory for generating coupon data."""

    product_variety = 'Any variety'
    sale_amount_off = Faker('pyfloat', left_digits=1, right_digits=2, positive=True, min_value=0.25, max_value=5.0)
    deal_type = 'AMOUNT_OFF'
    valid_to = LazyAttribute(
        lambda o: (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
    )


class FlippFlyerFactory(Factory):
    """Factory for generating Flipp flyer data."""

    class Meta:
        model = dict

    id = Faker('random_int', min=100000, max=999999)
    name = Faker('random_element', elements=('Weekly Ad', 'Monthly Specials', 'Sale Flyer'))
    valid_from = LazyAttribute(lambda o: datetime.now().isoformat())
    valid_to = LazyAttribute(
        lambda o: (datetime.now() + timedelta(days=7)).isoformat()
    )
    storefront_ids = LazyAttribute(lambda o: [fake.random_int(min=1, max=100) for _ in range(3)])


class FlippProductFactory(Factory):
    """Factory for generating Flipp product data."""

    class Meta:
        model = dict

    name = Faker('word')
    brand = Faker('company')
    description = Faker('sentence')
    price_text = LazyAttribute(lambda o: f"${fake.pyfloat(left_digits=2, right_digits=2, positive=True, min_value=0.5, max_value=50.0)}")
    pre_price_text = LazyAttribute(lambda o: f"${fake.pyfloat(left_digits=2, right_digits=2, positive=True, min_value=5.0, max_value=60.0)}")
    sale_story = Faker('sentence')
    valid_from = LazyAttribute(lambda o: datetime.now().isoformat())
    valid_to = LazyAttribute(
        lambda o: (datetime.now() + timedelta(days=7)).isoformat()
    )
    current_price = Faker('pyfloat', left_digits=2, right_digits=2, positive=True, min_value=0.5, max_value=50.0)
    sku = Faker('bothify', text='SKU-????-####')
    item_type = Faker('random_element', elements=('item', 'category', 'bundle'))


class StoreConfigFactory(Factory):
    """Factory for generating store configuration."""

    class Meta:
        model = dict

    store_code = Faker('bothify', text='????###')
    access_token = Faker('sha256')


class GeminiResponseFactory(Factory):
    """Factory for generating Gemini API response."""

    class Meta:
        model = dict

    products = LazyAttribute(lambda o: [ProductFactory() for _ in range(fake.random_int(min=1, max=5))])


class HTTPResponseFactory(Factory):
    """Factory for generating HTTP response data."""

    class Meta:
        model = dict

    status_code = 200
    data = LazyAttribute(lambda o: {'message': fake.sentence()})
    headers = LazyAttribute(lambda o: {'Content-Type': 'application/json'})
