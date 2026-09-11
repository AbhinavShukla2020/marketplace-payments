import pytest
from pydantic import ValidationError

from app.api import ListingInput


@pytest.mark.parametrize("currency", ["usd", "eur", "gbp", "cad", "jpy"])
def test_common_three_letter_currencies_are_accepted(currency):
    listing = ListingInput(seller_id="seller", title="Good item", price_cents=100, currency=currency)
    assert listing.currency == currency


@pytest.mark.parametrize("price", [0, -1, -2, -10, -99, -100, -999, -1000, -10000, -999999])
def test_nonpositive_prices_are_rejected(price):
    with pytest.raises(ValidationError):
        ListingInput(seller_id="seller", title="Good item", price_cents=price)


@pytest.mark.parametrize("inventory", [0, -1, -2, -10, -100])
def test_nonpositive_inventory_is_rejected(inventory):
    with pytest.raises(ValidationError):
        ListingInput(seller_id="seller", title="Good item", price_cents=100, inventory=inventory)


@pytest.mark.parametrize("currency", ["US", "USDD", "USD", "12a", "u$d", "", "euro", "us", "zzzz", " usd"])
def test_invalid_currency_codes_are_rejected(currency):
    with pytest.raises(ValidationError):
        ListingInput(seller_id="seller", title="Good item", price_cents=100, currency=currency)


@pytest.mark.parametrize("title", ["", "a", "ab"])
def test_short_titles_are_rejected(title):
    with pytest.raises(ValidationError):
        ListingInput(seller_id="seller", title=title, price_cents=100)

