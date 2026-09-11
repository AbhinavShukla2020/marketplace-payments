import pytest

from app.domain import sale_postings, stable_hash


def test_stable_hash_is_repeatable():
    assert stable_hash({"a": 1}) == stable_hash({"a": 1})


def test_stable_hash_ignores_key_order():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})


def test_stable_hash_changes_with_payload():
    assert stable_hash({"a": 1}) != stable_hash({"a": 2})


@pytest.mark.parametrize("amount", [1, 2, 3, 10, 11, 25, 99, 100, 101, 250, 499, 500, 999, 1000, 1001, 2500, 9999, 10000, 10001, 99999])
def test_sale_postings_balance(amount):
    postings = sale_postings("order", "seller", amount, 500)
    assert sum(posting.amount_cents for posting in postings) == 0


@pytest.mark.parametrize(("amount", "bps", "fee"), [(100, 100, 1), (100, 500, 5), (999, 500, 49), (1000, 0, 0), (1000, 1000, 100), (1234, 250, 30), (9999, 333, 332), (10000, 10000, 10000), (50, 500, 2), (1, 500, 0)])
def test_platform_fee_uses_integer_cents(amount, bps, fee):
    postings = sale_postings("order", "seller", amount, bps)
    platform = next(posting for posting in postings if posting.account == "platform_revenue")
    assert platform.amount_cents == -fee


@pytest.mark.parametrize("amount", [-1, -10, 0, -999, -100000])
def test_nonpositive_sale_amount_is_rejected(amount):
    with pytest.raises(ValueError):
        sale_postings("order", "seller", amount, 500)


@pytest.mark.parametrize("bps", [-1, -10, 10001, 20000, 99999, -10000])
def test_invalid_fee_rate_is_rejected(bps):
    with pytest.raises(ValueError):
        sale_postings("order", "seller", 100, bps)


def test_zero_fee_credits_entire_sale_to_seller():
    postings = sale_postings("order", "seller", 275, 0)
    seller = next(posting for posting in postings if posting.account.startswith("seller_payable"))
    assert seller.amount_cents == -275

