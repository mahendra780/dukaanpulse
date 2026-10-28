"""Safely seed an isolated DukaanPulse demo environment through its HTTP API.

Run from ``backend/``:

    python -m app.scripts.seed_demo --base-url http://127.0.0.1:8001 --months 12 --seed 42

The planner in this module has no I/O, database, or clock dependency.  It is
also intentionally separate from the executor so tests can validate the demo
business story without connecting to any database.
"""

from __future__ import annotations

import argparse
import getpass
import random
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

import httpx

from app.scripts.demo_personas import PERSONAS, DemoPersona


JSONValue = str | int | float | bool | None | date | list["JSONValue"] | dict[str, "JSONValue"]


@dataclass(frozen=True)
class PlannedEvent:
    event_date: date
    sequence: int
    entity: str
    operation: str
    payload: dict[str, JSONValue]
    result_ref: str | None = None
    persona_key: str | None = None


@dataclass(frozen=True)
class DemoPlan:
    seed: int
    months: int
    today: date
    events: tuple[PlannedEvent, ...]


class DemoSafetyError(RuntimeError):
    """The requested target cannot safely be seeded."""


def _ref(name: str) -> dict[str, str]:
    return {"$ref": name}


def _packaging_ref(product_key: str, unit_name: str) -> str:
    return f"packaging:{product_key}:{unit_name}"


def build_plan(seed: int, months: int, today: date) -> DemoPlan:
    """Build a complete, deterministic, chronologically ordered demo plan.

    ``today`` is explicit so the result remains a pure function.  Six months
    is the minimum that can honestly demonstrate the two D25 trend windows.
    """
    if months < 6:
        raise ValueError("months must be at least 6 to build the analytics scenarios.")

    rng = random.Random(seed)
    events: list[PlannedEvent] = []

    def add(
        event_date: date,
        entity: str,
        operation: str,
        payload: dict[str, JSONValue],
        *,
        result_ref: str | None = None,
        persona_key: str | None = None,
    ) -> None:
        events.append(
            PlannedEvent(
                event_date=event_date,
                sequence=len(events),
                entity=entity,
                operation=operation,
                payload=payload,
                result_ref=result_ref,
                persona_key=persona_key,
            )
        )

    # Start before the oldest invoice date, even for the minimum allowed
    # history, so received stock always precedes a delivered sale.
    start_date = today - timedelta(days=max(months * 30, 240))

    for category_key, category_name in (
        ("beverages", "Demo Beverages"),
        ("snacks", "Demo Snacks"),
    ):
        add(
            start_date,
            "category",
            "create",
            {"category_name": category_name, "status": "ACTIVE"},
            result_ref=f"category:{category_key}",
        )

    products = (
        (
            "fast_tea",
            "Demo Fast Tea",
            "Pulse Tea",
            "DEMO-FAST-TEA",
            "beverages",
            (
                ("PIECE", 1, True, False, False),
                ("CARTON", 12, False, True, True),
            ),
        ),
        (
            "fast_snacks",
            "Demo Fast Snacks",
            "Pulse Snacks",
            "DEMO-FAST-SNACKS",
            "snacks",
            (
                ("PIECE", 1, True, False, False),
                ("BOX", 24, False, True, True),
            ),
        ),
        (
            "slow_stock",
            "Demo Slow Stock",
            "Pulse Pantry",
            "DEMO-SLOW-STOCK",
            "snacks",
            (
                ("PIECE", 1, True, False, False),
                ("CARTON", 6, False, True, True),
            ),
        ),
    )
    for product_key, name, brand, sku, category_key, packaging in products:
        add(
            start_date,
            "product",
            "create",
            {
                "product_name": name,
                "brand_name": brand,
                "sku": sku,
                "category_id": _ref(f"category:{category_key}"),
                "status": "ACTIVE",
                "packaging": [
                    {
                        "unit_name": unit_name,
                        "conversion_to_base": conversion,
                        "is_base_unit": is_base_unit,
                        "is_purchase_unit": is_purchase_unit,
                        "is_sale_unit": is_sale_unit,
                    }
                    for unit_name, conversion, is_base_unit, is_purchase_unit, is_sale_unit in packaging
                ],
            },
            result_ref=f"product:{product_key}",
        )
        add(
            start_date,
            "product",
            "lookup_packaging",
            {"product_key": product_key},
            result_ref=f"product:{product_key}",
        )

    suppliers = (
        ("north", "North Foods Supply", 7),
        ("metro", "Metro Wholesale Supply", 30),
        ("old", "Old Stock Supply", 14),
    )
    for supplier_key, supplier_name, terms in suppliers:
        add(
            start_date,
            "supplier",
            "create",
            {
                "supplier_name": supplier_name,
                "phone": None,
                "address": "Demo supplier address",
                "gst_number": None,
                "payment_terms_days": terms,
                "status": "ACTIVE",
            },
            result_ref=f"supplier:{supplier_key}",
        )

    for persona in PERSONAS:
        add(
            start_date,
            "customer",
            "create",
            {
                "customer_name": persona.customer_name,
                "phone": None,
                "address": "Demo customer address",
                "area": "Demo Market",
                "credit_limit": persona.credit_limit,
                "payment_terms_days": persona.payment_terms_days,
                "status": "ACTIVE",
            },
            result_ref=f"customer:{persona.key}",
            persona_key=persona.key,
        )

    def purchase_item(product_key: str, unit_name: str, quantity: float, unit_price: float) -> dict[str, JSONValue]:
        line_total = round(quantity * unit_price, 2)
        return {
            "product_id": _ref(f"product:{product_key}"),
            "packaging_id": _ref(_packaging_ref(product_key, unit_name)),
            "quantity": quantity,
            "received_quantity": 0,
            "unit_price": unit_price,
            "discount": 0,
            "tax": 0,
            "line_total": line_total,
        }

    def add_purchase(
        purchase_key: str,
        supplier_key: str,
        purchase_date: date,
        items: list[dict[str, JSONValue]],
    ) -> None:
        subtotal = round(sum(float(item["line_total"]) for item in items), 2)
        add(
            purchase_date,
            "purchase",
            "create",
            {
                "supplier_id": _ref(f"supplier:{supplier_key}"),
                "purchase_date": purchase_date,
                "supplier_invoice_no": f"DEMO-PUR-{purchase_key.upper()}",
                "subtotal": subtotal,
                "discount": 0,
                "tax": 0,
                "total_amount": subtotal,
                "status": "PENDING",
                "items": items,
            },
            result_ref=f"purchase:{purchase_key}",
        )
        add(
            purchase_date,
            "purchase",
            "receive_all",
            {"purchase_id": _ref(f"purchase:{purchase_key}"), "status": "RECEIVED"},
        )

    # The opening receipt gives the two fast-moving products enough stock for
    # every historic delivery and leaves slow stock untouched for 120+ days.
    add_purchase(
        "opening",
        "north",
        start_date + timedelta(days=1),
        [
            purchase_item("fast_tea", "CARTON", 500, 450),
            purchase_item("fast_snacks", "BOX", 500, 300),
            purchase_item("slow_stock", "CARTON", 80, 200),
        ],
    )
    add_purchase(
        "due_soon",
        "metro",
        today - timedelta(days=25),
        [purchase_item("fast_snacks", "BOX", 40, 300)],
    )
    add_purchase(
        "overdue",
        "old",
        today - timedelta(days=60),
        [purchase_item("fast_tea", "CARTON", 40, 450)],
    )

    add(
        start_date + timedelta(days=8),
        "purchase_payment",
        "create",
        {
            "purchase_id": _ref("purchase:opening"),
            "payment_date": start_date + timedelta(days=8),
            "amount": 391_000,
            "payment_method": "BANK_TRANSFER",
            "reference_number": "DEMO-OPENING-PAID",
            "notes": "Synthetic demo purchase payment",
        },
    )
    add(
        today - timedelta(days=10),
        "purchase_payment",
        "create",
        {
            "purchase_id": _ref("purchase:due_soon"),
            "payment_date": today - timedelta(days=10),
            "amount": 4_000,
            "payment_method": "BANK_TRANSFER",
            "reference_number": "DEMO-DUE-SOON-PARTIAL",
            "notes": "Synthetic demo purchase payment",
        },
    )
    add(
        today - timedelta(days=30),
        "purchase_payment",
        "create",
        {
            "purchase_id": _ref("purchase:overdue"),
            "payment_date": today - timedelta(days=30),
            "amount": 5_000,
            "payment_method": "BANK_TRANSFER",
            "reference_number": "DEMO-OVERDUE-PARTIAL",
            "notes": "Synthetic demo purchase payment",
        },
    )

    credit_holder_sale: dict[str, Any] | None = None

    def add_sale(
        persona: DemoPersona,
        sale_number: int,
        invoice_date: date,
        amount: float,
        payment_date: date | None,
    ) -> dict[str, Any]:
        product_key, unit_name = rng.choice(
            (("fast_tea", "CARTON"), ("fast_snacks", "BOX"))
        )
        order_ref = f"order:{persona.key}:{sale_number}"
        invoice_ref = f"invoice:{persona.key}:{sale_number}"
        delivery_ref = f"delivery:{persona.key}:{sale_number}"
        line = {
            "product_id": _ref(f"product:{product_key}"),
            "packaging_id": _ref(_packaging_ref(product_key, unit_name)),
            "quantity": 1,
            "unit_price": amount,
            "discount": 0,
            "tax": 0,
            "line_total": amount,
        }
        add(
            invoice_date,
            "order",
            "create",
            {
                "customer_id": _ref(f"customer:{persona.key}"),
                "order_date": invoice_date,
                "status": "PENDING",
                "notes": f"Synthetic {persona.key} order {sale_number}",
                "items": [
                    {
                        "product_id": line["product_id"],
                        "packaging_id": line["packaging_id"],
                        "quantity": line["quantity"],
                    }
                ],
            },
            result_ref=order_ref,
            persona_key=persona.key,
        )
        add(
            invoice_date,
            "order",
            "confirm",
            {"order_id": _ref(order_ref), "status": "CONFIRMED"},
            persona_key=persona.key,
        )
        add(
            invoice_date,
            "invoice",
            "create",
            {
                "order_id": _ref(order_ref),
                "invoice_number": f"DEMO-{persona.key}-{sale_number:03d}",
                "invoice_date": invoice_date,
                "subtotal": amount,
                "discount": 0,
                "tax": 0,
                "total_amount": amount,
                "status": "UNPAID",
                "items": [line],
            },
            result_ref=invoice_ref,
            persona_key=persona.key,
        )
        add(
            invoice_date,
            "delivery",
            "create",
            {
                "invoice_id": _ref(invoice_ref),
                "delivery_date": invoice_date,
                "status": "PENDING",
                "delivery_address": "Demo customer address",
                "vehicle_number": "DEMO-01",
                "driver_name": "Demo Driver",
                "notes": "Synthetic demo delivery",
            },
            result_ref=delivery_ref,
            persona_key=persona.key,
        )
        for status in ("DISPATCHED", "OUT_FOR_DELIVERY", "DELIVERED"):
            add(
                invoice_date,
                "delivery",
                "update_status",
                {"delivery_id": _ref(delivery_ref), "status": status},
                persona_key=persona.key,
            )
        if payment_date is not None:
            add(
                payment_date,
                "payment",
                "create",
                {
                    "invoice_id": _ref(invoice_ref),
                    "payment_date": payment_date,
                    "amount": amount,
                    "payment_method": "BANK_TRANSFER",
                    "reference_number": f"DEMO-PAY-{persona.key}-{sale_number:03d}",
                    "notes": "Synthetic demo customer payment",
                },
                persona_key=persona.key,
            )
        return {
            "invoice_ref": invoice_ref,
            "product_ref": f"product:{product_key}",
            "packaging_ref": _packaging_ref(product_key, unit_name),
            "payment_date": payment_date,
        }

    for persona in PERSONAS:
        for sale_number, (settlement_offset, lateness_days) in enumerate(
            zip(persona.settlement_offsets, persona.settled_payment_lateness_days),
            start=1,
        ):
            payment_date = today + timedelta(days=settlement_offset)
            invoice_date = payment_date - timedelta(
                days=persona.payment_terms_days + lateness_days
            )
            sale = add_sale(
                persona,
                sale_number,
                invoice_date,
                persona.settled_invoice_amount,
                payment_date,
            )
            if persona.creates_credit_balance:
                credit_holder_sale = sale

        if persona.open_invoice_overdue_days is not None:
            open_sale_number = len(persona.settlement_offsets) + 1
            open_invoice_date = today - timedelta(
                days=persona.payment_terms_days + persona.open_invoice_overdue_days
            )
            add_sale(
                persona,
                open_sale_number,
                open_invoice_date,
                float(persona.open_invoice_amount or persona.settled_invoice_amount),
                None,
            )

    if credit_holder_sale is None or credit_holder_sale["payment_date"] is None:
        raise AssertionError("The CREDIT_HOLDER persona needs a fully paid invoice.")

    # The returned goods were fully paid first.  Receiving this resellable
    # return therefore puts its value into customers.credit_balance.
    return_date = credit_holder_sale["payment_date"] + timedelta(days=7)
    return_ref = "return:CREDIT_HOLDER:1"
    add(
        return_date,
        "return",
        "create",
        {
            "invoice_id": _ref(credit_holder_sale["invoice_ref"]),
            "return_date": return_date,
            "reason": "QUALITY_ISSUE",
            "status": "REQUESTED",
            "notes": "Synthetic return after a fully paid invoice",
            "items": [
                {
                    "product_id": _ref(credit_holder_sale["product_ref"]),
                    "packaging_id": _ref(credit_holder_sale["packaging_ref"]),
                    "quantity": 1,
                    "condition": "RESELLABLE",
                }
            ],
        },
        result_ref=return_ref,
        persona_key="CREDIT_HOLDER",
    )
    add(
        return_date,
        "return",
        "approve",
        {"return_id": _ref(return_ref)},
        persona_key="CREDIT_HOLDER",
    )
    add(
        return_date,
        "return",
        "receive",
        {"return_id": _ref(return_ref)},
        persona_key="CREDIT_HOLDER",
    )

    ordered_events = tuple(sorted(events, key=lambda event: (event.event_date, event.sequence)))
    return DemoPlan(seed=seed, months=months, today=today, events=ordered_events)


def summarize_plan(plan: DemoPlan) -> str:
    entity_counts = Counter(event.entity for event in plan.events)
    invoice_counts = Counter(
        event.persona_key
        for event in plan.events
        if event.entity == "invoice" and event.operation == "create" and event.persona_key
    )
    lines = [
        f"Dry run: {len(plan.events)} planned API events for {plan.today.isoformat()}.",
        "Per persona (invoices):",
    ]
    lines.extend(f"  {persona.key}: {invoice_counts[persona.key]}" for persona in PERSONAS)
    lines.append("Per entity (events):")
    lines.extend(f"  {entity}: {entity_counts[entity]}" for entity in sorted(entity_counts))
    return "\n".join(lines)


def validate_demo_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DemoSafetyError("--base-url must be an absolute HTTP(S) URL.")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise DemoSafetyError(
            "For safety, the demo seeder only accepts a loopback backend URL."
        )
    return normalized


def require_seed_confirmation(input_func: Callable[[str], str] = input) -> None:
    try:
        confirmation = input_func("Type SEED DEMO to seed this target: ").strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise DemoSafetyError("Demo seeding cancelled.") from exc
    if confirmation != "SEED DEMO":
        raise DemoSafetyError("Demo seeding cancelled: confirmation did not match.")


def ensure_demo_seed_allowed(client: httpx.Client) -> None:
    health = _request(client, "GET", "/health", headers={})
    if not isinstance(health, dict) or health.get("demo_seed_allowed") is not True:
        raise DemoSafetyError(
            "Refusing to seed: target must return demo_seed_allowed=true from /health. "
            "Set DEMO_SEED_ALLOWED=true only in that target's .env.demo."
        )


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    form_data: dict[str, str] | None = None,
) -> Any:
    response = client.request(
        method,
        path,
        headers=headers,
        json=json_body,
        data=form_data,
    )
    if response.is_error:
        raise DemoSafetyError(
            f"API request failed: {method} {path} returned HTTP {response.status_code}."
        )
    try:
        return response.json()
    except ValueError as exc:
        raise DemoSafetyError(f"API request failed: {method} {path} returned invalid JSON.") from exc


def login(client: httpx.Client, username: str, password: str) -> dict[str, str]:
    response = _request(
        client,
        "POST",
        "/auth/login",
        headers={},
        form_data={"username": username, "password": password},
    )
    token = response.get("access_token") if isinstance(response, dict) else None
    if not isinstance(token, str) or not token:
        raise DemoSafetyError("Login did not return an access token.")
    return {"Authorization": f"Bearer {token}"}


def ensure_target_is_empty(client: httpx.Client, headers: dict[str, str]) -> None:
    for entity, path in (
        ("products", "/products/"),
        ("customers", "/customers/"),
        ("suppliers", "/suppliers/"),
        ("purchases", "/purchases/"),
        ("orders", "/orders/"),
    ):
        records = _request(client, "GET", path, headers=headers)
        if not isinstance(records, list):
            raise DemoSafetyError(f"Unable to confirm that {entity} are empty.")
        if records:
            raise DemoSafetyError(
                f"Refusing to seed: target already contains {entity}."
            )


def _resolve(value: JSONValue, references: dict[str, Any]) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_resolve(item, references) for item in value]
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            reference = value["$ref"]
            if reference not in references:
                raise DemoSafetyError(f"Plan reference is not available: {reference}.")
            return references[reference]
        return {key: _resolve(item, references) for key, item in value.items()}
    return value


def _result_id(payload: Any, key: str) -> int:
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, int):
        raise DemoSafetyError(f"API response did not contain {key}.")
    return value


def execute_plan(client: httpx.Client, headers: dict[str, str], plan: DemoPlan) -> None:
    """Execute a valid plan through the normal authenticated HTTP endpoints."""
    references: dict[str, Any] = {}
    response_id_keys = {
        "category": "category_id",
        "product": "product_id",
        "supplier": "supplier_id",
        "customer": "customer_id",
        "purchase": "purchase_id",
        "order": "order_id",
        "invoice": "invoice_id",
        "delivery": "delivery_id",
        "return": "return_id",
    }

    for event in plan.events:
        payload = _resolve(event.payload, references)
        response: Any
        if event.entity == "category" and event.operation == "create":
            response = _request(client, "POST", "/categories/", headers=headers, json_body=payload)
        elif event.entity == "product" and event.operation == "create":
            response = _request(client, "POST", "/products/", headers=headers, json_body=payload)
        elif event.entity == "product" and event.operation == "lookup_packaging":
            product_id = references.get(event.result_ref or "")
            if not isinstance(product_id, int):
                raise DemoSafetyError("Product ID is unavailable while resolving packaging.")
            response = _request(client, "GET", f"/products/{product_id}", headers=headers)
            packaging = response.get("packaging") if isinstance(response, dict) else None
            if not isinstance(packaging, list):
                raise DemoSafetyError("Product lookup did not return packaging.")
            product_key = payload["product_key"]
            for item in packaging:
                if not isinstance(item, dict):
                    continue
                unit_name = item.get("unit_name")
                packaging_id = item.get("packaging_id")
                if isinstance(unit_name, str) and isinstance(packaging_id, int):
                    references[_packaging_ref(str(product_key), unit_name)] = packaging_id
            continue
        elif event.entity == "supplier" and event.operation == "create":
            response = _request(client, "POST", "/suppliers/", headers=headers, json_body=payload)
        elif event.entity == "customer" and event.operation == "create":
            response = _request(client, "POST", "/customers/", headers=headers, json_body=payload)
        elif event.entity == "purchase" and event.operation == "create":
            response = _request(client, "POST", "/purchases/", headers=headers, json_body=payload)
        elif event.entity == "purchase" and event.operation == "receive_all":
            purchase_id = payload["purchase_id"]
            response = _request(
                client,
                "PATCH",
                f"/purchases/{purchase_id}/status",
                headers=headers,
                json_body={"status": payload["status"]},
            )
        elif event.entity == "purchase_payment" and event.operation == "create":
            response = _request(client, "POST", "/purchase-payments/", headers=headers, json_body=payload)
        elif event.entity == "order" and event.operation == "create":
            response = _request(client, "POST", "/orders/", headers=headers, json_body=payload)
        elif event.entity == "order" and event.operation == "confirm":
            order_id = payload["order_id"]
            response = _request(
                client,
                "PATCH",
                f"/orders/{order_id}/status",
                headers=headers,
                json_body={"status": payload["status"]},
            )
        elif event.entity == "invoice" and event.operation == "create":
            response = _request(client, "POST", "/invoices/", headers=headers, json_body=payload)
        elif event.entity == "delivery" and event.operation == "create":
            response = _request(client, "POST", "/deliveries/", headers=headers, json_body=payload)
        elif event.entity == "delivery" and event.operation == "update_status":
            delivery_id = payload["delivery_id"]
            response = _request(
                client,
                "PATCH",
                f"/deliveries/{delivery_id}/status",
                headers=headers,
                json_body={"status": payload["status"]},
            )
        elif event.entity == "payment" and event.operation == "create":
            response = _request(client, "POST", "/payments/", headers=headers, json_body=payload)
        elif event.entity == "return" and event.operation == "create":
            response = _request(client, "POST", "/returns/", headers=headers, json_body=payload)
        elif event.entity == "return" and event.operation in {"approve", "receive"}:
            return_id = payload["return_id"]
            response = _request(
                client,
                "PATCH",
                f"/returns/{return_id}/{event.operation}",
                headers=headers,
            )
        else:
            raise DemoSafetyError(
                f"Unsupported plan event: {event.entity} {event.operation}."
            )

        if event.result_ref:
            result_key = response_id_keys.get(event.entity)
            if result_key is None:
                raise DemoSafetyError(f"No response ID mapping exists for {event.entity}.")
            references[event.result_ref] = _result_id(response, result_key)


def seed_target(
    client: httpx.Client,
    plan: DemoPlan,
    *,
    username: str,
    password: str,
) -> None:
    headers = login(client, username, password)
    ensure_target_is_empty(client, headers)
    execute_plan(client, headers, plan)


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an isolated DukaanPulse demo backend.")
    parser.add_argument("--base-url", required=True, help="Loopback URL of the demo backend")
    parser.add_argument("--months", type=int, default=12, help="Months of history (minimum 6)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan summary without any network calls")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.dry_run:
            plan = build_plan(args.seed, args.months, date.today())
            print(summarize_plan(plan))
            return 0

        base_url = validate_demo_base_url(args.base_url)
        with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=False) as client:
            ensure_demo_seed_allowed(client)
        plan = build_plan(args.seed, args.months, date.today())
        print(f"Demo target: {base_url}")
        require_seed_confirmation()
        try:
            username = input("Admin username: ").strip()
            password = getpass.getpass("Admin password: ")
        except (EOFError, KeyboardInterrupt) as exc:
            raise DemoSafetyError("Demo seeding cancelled.") from exc
        if not username or not password:
            raise DemoSafetyError("Admin username and password are required.")

        with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=False) as client:
            seed_target(client, plan, username=username, password=password)
        print("Demo data seeded successfully.")
        return 0
    except (DemoSafetyError, ValueError, httpx.HTTPError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
