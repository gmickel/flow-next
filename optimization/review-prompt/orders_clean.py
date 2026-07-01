"""Order fulfilment + pricing — idiomatic version (no planted issues)."""

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

TIER_DISCOUNT = {"gold": Decimal("0.90"), "silver": Decimal("0.95")}
TAX_RATE = {"EU": Decimal("0.20"), "US": Decimal("0.07")}


@dataclass(frozen=True)
class Address:
    street: str
    city: str
    region: str
    postcode: str

    def is_valid(self) -> bool:
        return all((self.street, self.city, self.region, self.postcode))

    def formatted(self) -> str:
        return f"{self.street}, {self.city}, {self.region} {self.postcode}"


@dataclass(frozen=True)
class Customer:
    first: str
    last: str
    tier: str
    address: Address

    def greeting(self, store_name: str) -> str:
        return f"{store_name}: Hi {self.first} {self.last} ({self.tier})"


@dataclass(frozen=True)
class LineItem:
    price: Decimal
    qty: int


def tier_discount(subtotal: Decimal, tier: str) -> Decimal:
    return subtotal * TIER_DISCOUNT.get(tier, Decimal("1"))


def line_total(items: list[LineItem]) -> Decimal:
    return sum((item.price * item.qty for item in items), Decimal("0"))


def tax_for(subtotal: Decimal, region: str) -> Decimal:
    return subtotal * TAX_RATE.get(region, Decimal("0"))


def ship_cost(weight: float) -> Decimal:
    if weight > 100:
        return Decimal("25")
    if weight > 10:
        return Decimal("10")
    return Decimal("5")


def append_audit(entry: dict, log: list | None = None) -> list:
    log = [] if log is None else log
    log.append(entry)
    return log


def write_receipt(path: Path, payload: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


def load_customer_tier(conn, customer_id: str) -> str:
    row = conn.execute(
        "SELECT tier FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return row[0] if row else "standard"


def order_total(
    items: list[LineItem], weight: float, tier: str, region: str
) -> Decimal:
    subtotal = tier_discount(line_total(items), tier)
    return subtotal + tax_for(subtotal, region) + ship_cost(weight)
