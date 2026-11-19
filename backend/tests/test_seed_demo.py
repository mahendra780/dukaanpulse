import json
import unittest
from collections import defaultdict
from datetime import date

import httpx

from app.scripts.demo_personas import PERSONAS
from app.scripts.seed_demo import (
    DemoSafetyError,
    build_plan,
    ensure_demo_seed_allowed,
    ensure_target_is_empty,
    execute_plan,
    require_seed_confirmation,
    validate_demo_base_url,
)


TODAY = date(2026, 10, 22)


def reference_name(value):
    return value["$ref"]


class SeedDemoPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan(seed=42, months=12, today=TODAY)

    def test_same_seed_and_inputs_build_the_same_plan(self):
        self.assertEqual(
            self.plan,
            build_plan(seed=42, months=12, today=TODAY),
        )

    def test_persona_invoice_counts_and_expected_scenarios_hold(self):
        invoice_counts = defaultdict(int)
        for event in self.plan.events:
            if event.entity == "invoice" and event.operation == "create":
                invoice_counts[event.persona_key] += 1

        self.assertEqual(invoice_counts["NEW"], 2)
        for persona in PERSONAS:
            expected = len(persona.settlement_offsets) + int(
                persona.open_invoice_overdue_days is not None
            )
            self.assertEqual(invoice_counts[persona.key], expected)

        credit_return = next(
            event
            for event in self.plan.events
            if event.entity == "return" and event.operation == "create"
        )
        invoice_ref = reference_name(credit_return.payload["invoice_id"])
        payment_dates = [
            event.payload["payment_date"]
            for event in self.plan.events
            if event.entity == "payment"
            and event.operation == "create"
            and reference_name(event.payload["invoice_id"]) == invoice_ref
        ]
        self.assertEqual(len(payment_dates), 1)
        self.assertLess(payment_dates[0], credit_return.payload["return_date"])
        self.assertEqual(credit_return.payload["items"][0]["condition"], "RESELLABLE")

    def test_persona_parameters_match_the_d25_bands_and_trends(self):
        invoices = {
            event.result_ref: event
            for event in self.plan.events
            if event.entity == "invoice" and event.operation == "create"
        }
        payments_by_invoice = defaultdict(list)
        for event in self.plan.events:
            if event.entity == "payment" and event.operation == "create":
                payments_by_invoice[reference_name(event.payload["invoice_id"])].append(event)

        for persona in PERSONAS:
            settled = []
            open_invoices = []
            for invoice_ref, invoice in invoices.items():
                if invoice.persona_key != persona.key:
                    continue
                payments = payments_by_invoice[invoice_ref]
                if payments:
                    settlement_date = max(payment.payload["payment_date"] for payment in payments)
                    due_date = invoice.payload["invoice_date"].fromordinal(
                        invoice.payload["invoice_date"].toordinal() + persona.payment_terms_days
                    )
                    settled.append((settlement_date, max(0, (settlement_date - due_date).days)))
                else:
                    open_invoices.append(invoice)

            window = [entry for entry in settled if entry[0] >= TODAY.fromordinal(TODAY.toordinal() - 180)]
            if len(window) < 3:
                band = "INSUFFICIENT_HISTORY"
            else:
                average_days_late = sum(entry[1] for entry in window) / len(window)
                late_share = sum(entry[1] > 0 for entry in window) / len(window)
                overdue_days = [
                    max(
                        0,
                        (
                            TODAY
                            - invoice.payload["invoice_date"].fromordinal(
                                invoice.payload["invoice_date"].toordinal()
                                + persona.payment_terms_days
                            )
                        ).days,
                    )
                    for invoice in open_invoices
                ]
                oldest_overdue = max(overdue_days, default=0)
                outstanding = sum(invoice.payload["total_amount"] for invoice in open_invoices)
                utilisation = 0 if persona.credit_limit == 0 else max(
                    0,
                    min(1, (outstanding / persona.credit_limit - 0.7) / 0.3),
                )
                score = (
                    40 * min(average_days_late, 45) / 45
                    + 20 * late_share
                    + 25 * min(oldest_overdue, 60) / 60
                    + 15 * utilisation
                )
                band = "RELIABLE" if score < 25 else "WATCH" if score < 50 else "RISKY"

            recent = [entry[1] for entry in settled if entry[0] >= TODAY.fromordinal(TODAY.toordinal() - 90)]
            previous = [
                entry[1]
                for entry in settled
                if TODAY.fromordinal(TODAY.toordinal() - 180)
                <= entry[0]
                < TODAY.fromordinal(TODAY.toordinal() - 90)
            ]
            if len(recent) < 2 or len(previous) < 2:
                trend = None
            elif sum(recent) / len(recent) > sum(previous) / len(previous):
                trend = "WORSENING"
            elif sum(recent) / len(recent) < sum(previous) / len(previous):
                trend = "IMPROVING"
            else:
                trend = "STABLE"

            self.assertEqual(band, persona.expected_band, persona.key)
            self.assertEqual(trend, persona.expected_trend, persona.key)

    def test_payments_are_not_future_dated_and_invoice_totals_match_lines(self):
        for event in self.plan.events:
            if event.entity in {"payment", "purchase_payment"}:
                self.assertLessEqual(event.payload["payment_date"], TODAY)
            if event.entity == "return" and event.operation == "create":
                # Receiving a return creates an automatic RETURN_CREDIT payment
                # dated with this business event.
                self.assertLessEqual(event.payload["return_date"], TODAY)
            if event.entity == "invoice" and event.operation == "create":
                lines = event.payload["items"]
                self.assertAlmostEqual(
                    event.payload["subtotal"],
                    sum(line["quantity"] * line["unit_price"] for line in lines),
                )
                self.assertAlmostEqual(
                    event.payload["total_amount"],
                    sum(line["line_total"] for line in lines),
                )
                for line in lines:
                    self.assertAlmostEqual(
                        line["line_total"],
                        line["quantity"] * line["unit_price"] - line["discount"] + line["tax"],
                    )

    def test_planned_stock_never_goes_negative(self):
        conversions = {}
        purchases = {}
        invoices = {}
        deliveries = {}
        returns = {}
        stock = defaultdict(float)

        for event in self.plan.events:
            if event.entity == "product" and event.operation == "create":
                product_key = event.result_ref.removeprefix("product:")
                for packaging in event.payload["packaging"]:
                    conversions[f"packaging:{product_key}:{packaging['unit_name']}"] = packaging[
                        "conversion_to_base"
                    ]
            elif event.entity == "purchase" and event.operation == "create":
                purchases[event.result_ref] = event.payload
            elif event.entity == "purchase" and event.operation == "receive_all":
                purchase = purchases[reference_name(event.payload["purchase_id"])]
                for line in purchase["items"]:
                    product_ref = reference_name(line["product_id"])
                    packaging_ref = reference_name(line["packaging_id"])
                    stock[product_ref] += line["quantity"] * conversions[packaging_ref]
            elif event.entity == "invoice" and event.operation == "create":
                invoices[event.result_ref] = event.payload
            elif event.entity == "delivery" and event.operation == "create":
                deliveries[event.result_ref] = reference_name(event.payload["invoice_id"])
            elif (
                event.entity == "delivery"
                and event.operation == "update_status"
                and event.payload["status"] == "DELIVERED"
            ):
                invoice = invoices[deliveries[reference_name(event.payload["delivery_id"])]]
                for line in invoice["items"]:
                    product_ref = reference_name(line["product_id"])
                    packaging_ref = reference_name(line["packaging_id"])
                    stock[product_ref] -= line["quantity"] * conversions[packaging_ref]
                    self.assertGreaterEqual(stock[product_ref], 0)
            elif event.entity == "return" and event.operation == "create":
                returns[event.result_ref] = event.payload
            elif event.entity == "return" and event.operation == "receive":
                return_payload = returns[reference_name(event.payload["return_id"])]
                for line in return_payload["items"]:
                    if line["condition"] == "RESELLABLE":
                        product_ref = reference_name(line["product_id"])
                        packaging_ref = reference_name(line["packaging_id"])
                        stock[product_ref] += line["quantity"] * conversions[packaging_ref]


class SeedDemoSafetyTests(unittest.TestCase):
    def test_health_check_refuses_when_demo_seeding_is_disabled_or_not_advertised(self):
        for health_payload in ({"demo_seed_allowed": False}, {"status": "healthy"}):
            with self.subTest(health_payload=health_payload):
                requested_paths = []

                def handler(request):
                    requested_paths.append(request.url.path)
                    return httpx.Response(200, json=health_payload)

                with httpx.Client(
                    base_url="http://127.0.0.1:8001",
                    transport=httpx.MockTransport(handler),
                ) as client:
                    with self.assertRaisesRegex(DemoSafetyError, "demo_seed_allowed=true"):
                        ensure_demo_seed_allowed(client)

                self.assertEqual(requested_paths, ["/health"])

    def test_health_check_proceeds_when_demo_seeding_is_explicitly_allowed(self):
        requested_paths = []

        def handler(request):
            requested_paths.append(request.url.path)
            return httpx.Response(200, json={"demo_seed_allowed": True})

        with httpx.Client(
            base_url="http://127.0.0.1:8001",
            transport=httpx.MockTransport(handler),
        ) as client:
            ensure_demo_seed_allowed(client)

        self.assertEqual(requested_paths, ["/health"])

    def test_target_url_must_be_loopback(self):
        self.assertEqual(
            validate_demo_base_url("http://127.0.0.1:8001/"),
            "http://127.0.0.1:8001",
        )
        with self.assertRaisesRegex(DemoSafetyError, "loopback"):
            validate_demo_base_url("https://api.example.com")

    def test_executor_sends_the_complete_plan_through_mock_transport(self):
        plan = build_plan(seed=42, months=12, today=TODAY)
        next_ids = defaultdict(int)
        packaging_by_product = {}
        requests = []

        def new_id(entity):
            next_ids[entity] += 1
            return next_ids[entity]

        def handler(request):
            requests.append(request)
            payload = json.loads(request.content) if request.content else {}
            if request.method == "POST" and request.url.path == "/categories/":
                return httpx.Response(201, json={"category_id": new_id("category")})
            if request.method == "POST" and request.url.path == "/products/":
                product_id = new_id("product")
                packaging_by_product[product_id] = [
                    {
                        "packaging_id": product_id * 100 + index,
                        "unit_name": item["unit_name"],
                    }
                    for index, item in enumerate(payload["packaging"], start=1)
                ]
                return httpx.Response(201, json={"product_id": product_id})
            if request.method == "GET" and request.url.path.startswith("/products/"):
                product_id = int(request.url.path.rsplit("/", 1)[-1])
                return httpx.Response(
                    200,
                    json={"product_id": product_id, "packaging": packaging_by_product[product_id]},
                )
            create_responses = {
                "/suppliers/": ("supplier", "supplier_id"),
                "/customers/": ("customer", "customer_id"),
                "/purchases/": ("purchase", "purchase_id"),
                "/orders/": ("order", "order_id"),
                "/invoices/": ("invoice", "invoice_id"),
                "/deliveries/": ("delivery", "delivery_id"),
                "/returns/": ("return", "return_id"),
            }
            if request.method == "POST" and request.url.path in create_responses:
                entity, key = create_responses[request.url.path]
                return httpx.Response(201, json={key: new_id(entity)})
            if request.method == "POST" and request.url.path in {
                "/payments/",
                "/purchase-payments/",
            }:
                return httpx.Response(201, json={})
            if request.method == "PATCH":
                return httpx.Response(200, json={})
            raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

        with httpx.Client(
            base_url="http://127.0.0.1:8001",
            transport=httpx.MockTransport(handler),
        ) as client:
            execute_plan(client, {"Authorization": "Bearer test"}, plan)

        self.assertEqual(len(requests), len(plan.events))
        self.assertTrue(all(request.headers["authorization"] == "Bearer test" for request in requests))

    def test_empty_target_check_refuses_a_nonempty_target_using_mock_transport(self):
        requested_paths = []

        def handler(request):
            requested_paths.append(request.url.path)
            payloads = {
                "/products/": [],
                "/customers/": [{"customer_id": 1}],
                "/suppliers/": [],
                "/purchases/": [],
                "/orders/": [],
            }
            return httpx.Response(200, json=payloads[request.url.path])

        with httpx.Client(
            base_url="http://127.0.0.1:8001",
            transport=httpx.MockTransport(handler),
        ) as client:
            with self.assertRaisesRegex(DemoSafetyError, "already contains customers"):
                ensure_target_is_empty(client, {"Authorization": "Bearer test"})

        self.assertEqual(requested_paths, ["/products/", "/customers/"])

    def test_confirmation_must_match_before_any_mock_transport_request(self):
        requested_paths = []

        def handler(request):
            requested_paths.append(request.url.path)
            return httpx.Response(500)

        with httpx.Client(
            base_url="http://127.0.0.1:8001",
            transport=httpx.MockTransport(handler),
        ):
            with self.assertRaisesRegex(DemoSafetyError, "confirmation did not match"):
                require_seed_confirmation(lambda _prompt: "not the confirmation")

        self.assertEqual(requested_paths, [])


if __name__ == "__main__":
    unittest.main()
