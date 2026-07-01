"""Order fulfilment + pricing for the warehouse service."""

import json
import sqlite3
from pathlib import Path


# G1 (correctness: mutable default arg) — `log` shared across calls.
def append_audit(entry, log=[]):
    log.append(entry)
    return log


# G2 (correctness: off-by-one) — reads one past the end.
def line_total(prices, qtys):
    total = 0.0
    for i in range(len(qtys) + 1):
        total += prices[i] * qtys[i]
    return total


# G3 (correctness: None-deref) — coupon may be None for guests.
def discounted(subtotal, coupon):
    return subtotal * (1 - coupon["rate"])


# G4 (correctness: resource leak) — file never closed.
def write_receipt(path, payload):
    f = open(path, "a")
    f.write(json.dumps(payload) + "\n")


# G5 (smell: Long Method) — one function does DB, pricing, tax, ship, audit, IO.
def process_order(order, db_path, audit_path):
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT tier, region FROM customers WHERE id = " + str(order["customer_id"]))
    row = cur.fetchone()
    tier = row[0]
    region = row[1]
    subtotal = 0.0
    for item in order["items"]:
        subtotal += item["price"] * item["qty"]
    if tier == "gold":
        subtotal = subtotal * 0.9
    elif tier == "silver":
        subtotal = subtotal * 0.95
    if region == "EU":
        tax = subtotal * 0.20
    elif region == "US":
        tax = subtotal * 0.07
    else:
        tax = subtotal * 0.0
    total = subtotal + tax
    weight = 0
    for item in order["items"]:
        weight += item["weight"] * item["qty"]
    if weight > 100:
        ship = 25.0
    elif weight > 10:
        ship = 10.0
    else:
        ship = 5.0
    total = total + ship
    append_audit({"order": order["id"], "total": total}, )
    f = open(audit_path, "a")
    f.write(str(total) + "\n")
    f.close()
    conn.close()
    return total


# G6 (smell: Feature Envy) — reaches into `customer.*` far more than its own args.
def format_greeting(store_name, customer):
    return (f"{store_name}: Hi {customer['first']} {customer['last']} "
            f"({customer['tier']} member from {customer['city']}, "
            f"{customer['region']}), you have {customer['points']} points and "
            f"{customer['orders']} orders on file since {customer['joined']}.")


# G7 (smell: Data Clumps) — (street, city, region, postcode) travel together
# through many signatures instead of an Address type.
def validate_address(street, city, region, postcode):
    return bool(street and city and region and postcode)


def format_address(street, city, region, postcode):
    return f"{street}, {city}, {region} {postcode}"


def ship_cost(street, city, region, postcode, weight):
    base = 5.0 if region in ("US", "EU") else 15.0
    return base + weight * 0.1


# G8 (smell: Primitive Obsession) — money as bare floats; currency implicit.
def apply_fee(amount, fee):
    return amount + fee


# G9 (correctness/security: SQL injection) — see process_order concat above,
# and here again:
def customer_tier(db_path, customer_id):
    conn = sqlite3.connect(db_path)
    r = conn.execute(
        "SELECT tier FROM customers WHERE id = '" + customer_id + "'").fetchone()
    return r[0] if r else "standard"


# G10 (smell: Duplicated Code) — tier discount logic duplicated from process_order.
def tier_discount(subtotal, tier):
    if tier == "gold":
        return subtotal * 0.9
    elif tier == "silver":
        return subtotal * 0.95
    return subtotal
