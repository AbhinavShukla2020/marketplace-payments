import itertools

from locust import HttpUser, between, task


class MarketplaceBuyer(HttpUser):
    wait_time = between(0.05, 0.2)
    sequence = itertools.count()

    @task(4)
    def browse(self):
        self.client.get("/listings")

    @task(1)
    def checkout(self):
        number = next(self.sequence)
        self.client.post(
            "/checkout",
            headers={"idempotency-key": f"load-user-{id(self)}-{number}"},
            json={"listing_id": "seeded-listing", "buyer_id": f"buyer-{id(self)}"},
        )

