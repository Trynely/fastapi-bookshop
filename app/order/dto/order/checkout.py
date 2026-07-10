from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CheckoutResultDTO:
    order_id: int
    payment_id: int
    stripe_checkout_url: str
