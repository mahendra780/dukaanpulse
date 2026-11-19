
# DukaanPulse — manual test flow

Run this top to bottom once, in order — each step's data feeds the next.
It exercises every status transition the backend enforces, so it's the
fastest way to catch a mismatch between frontend and backend.

## 0. Prerequisites

- Backend running on :8000, frontend on :5173 (see setup steps).
- At least one row in `categories` (seeded via SQL — no create endpoint
  exists yet). Everything below assumes one exists.

## 1. Products

1. Go to **Products → Add product**.
2. Create a product with two packaging units, e.g. `PIECE` (base unit,
   sale unit) and `CARTON` (purchase unit, conversion_to_base = 12).
3. Confirm it appears in the list with **0 stock**.

## 2. Suppliers & Customers

1. **Suppliers → Add supplier** — create one.
2. **Customers → Add customer** — create one.

## 3. Purchase → receive → stock goes up

1. **Purchases → New purchase** — pick the supplier, add a line for
   your product using the `CARTON` unit, quantity 5, received qty 5,
   any price.
2. Status starts `PENDING`. Click **Mark received**.
3. Go to **Stock lookup**, select the product — stock should now read
   `60 PIECE` (5 cartons × 12 conversion).
   - This is the `create_purchase_movement` path — if stock doesn't
     move, the purchase→inventory link is broken.

## 4. Order → Confirm → Invoice → stock unaffected yet

1. **Orders → New order** — pick the customer, add a line using the
   `PIECE` unit, quantity 10.
2. Click **Confirm** (`PENDING → CONFIRMED`).
3. **Invoices → New invoice** — the confirmed order should appear in
   the picker. Selecting it pre-fills quantity (10 PIECE) from the
   order; enter a unit price and create it.
4. Check **Stock lookup** again — stock should **still be 60**.
   Invoicing does not deduct stock; delivery does. If it already
   dropped here, something's wrong.

## 5. Delivery → Dispatch → Deliver → stock goes down

1. **Deliveries → New delivery** — the invoice should appear (only
   invoices without an existing delivery are offered). Fill address,
   create it (starts `PENDING`).
2. Click **Dispatch** (`PENDING → DISPATCHED`).
3. Click **Mark delivered** (`DISPATCHED → DELIVERED`).
4. Check **Stock lookup** — should now read `50 PIECE` (60 − 10).
   This confirms `create_sale_movement` fired only on delivery.

## 6. Payment → invoice status flips

1. **Invoice detail** (click the invoice number from the Invoices
   list) — should show "remaining" equal to the full invoice total.
2. **Payments → Record payment** — pick the invoice, pay the full
   remaining amount.
3. Revisit **Invoice detail** — status should now be `PAID`, remaining
   `₹0`. Try a partial amount on a different invoice to confirm it
   instead flips to `PARTIALLY_PAID`.

## 7. Return → Approve → Receive → stock goes back up, invoice gets credited

1. **Returns → New return** — pick the delivered invoice, reason
   `WRONG_PRODUCT`, one item (product/unit as sold), condition
   **`RESELLABLE`**. Status starts `REQUESTED`.
   - Condition matters for stock: only `RESELLABLE` returns add stock
     back (`create_return_movement` skips `DAMAGED`/`EXPIRED`/
     `SUPPLIER_RETURN` on purpose — damaged goods shouldn't become
     sellable stock again). Use `RESELLABLE` here specifically so you
     can observe the stock change in the next step; the money credit
     in step 5 below applies regardless of condition.
2. Click **Approve** (`REQUESTED → APPROVED`).
3. Click **Receive** (`APPROVED → RECEIVED`).
4. Check **Stock lookup** — stock should increase again by the
   returned quantity. This confirms `create_return_movement`.
5. Open that invoice's **Invoice detail** page — the Payments list
   should now show an extra row tagged **Return credit**, equal to
   (returned quantity × the price it was sold at on that invoice).
   "Remaining" should have dropped by that same amount, and if it
   fully covers what was left, the invoice status should flip to
   `PAID` on its own — no manual payment needed for that part.

## 8. Cancellation paths (the bug fixed earlier)

1. Create a throwaway purchase, leave it `PENDING`, click **Cancel**.
   It should update cleanly with no 500 error — this is exactly the
   indentation bug that was fixed in `purchases.py`. If this throws a
   generic server error, that fix regressed.
2. Same check for an order left `PENDING` → **Cancel**.

## 9. Dashboard sanity check

Go back to **Dashboard** — sales/purchases totals, the trend chart,
top products, and low stock should all reflect the activity above.

---

### If something breaks

- Open the browser devtools Network tab — every page surfaces the
  backend's actual `detail` message via `extractErrorMessage`, so the
  red banner text is almost always the real FastAPI error, not a
  generic frontend one.
- Check the `uvicorn --reload` terminal for the Python traceback if
  the frontend just shows "Something went wrong".
