# DukaanPlus sample data

All data below is fictional and intended only for a dedicated test environment.
It is designed to work with the workflow in [testing01.md](testing01.md). Do
not use it against production or replace real contacts with it. Values prefixed
with `TEST` make the records easy to find later.

Use the same date throughout unless your tester needs a different date for the
dashboard. If changed, use the same year in the dashboard filters.

| Field | Sample value |
| --- | --- |
| Test date | `2026-10-20` |
| Test prefix | `TEST` |
| Currency display | Use the application's configured currency; calculations below are numeric |

## 1. Master data

### Category

| Field | Value |
| --- | --- |
| Category name | `TEST - Home Care` |
| Status | `ACTIVE` |

The category name is unique. Do not create it twice; use the duplicate attempt
only as a negative test.

### Product

| Field | Value |
| --- | --- |
| Product name | `TEST - Sparkle Soap Bar 100 g` |
| Brand | `TEST - Sparkle` |
| SKU | `TEST-SOAP-100` |
| Category | `TEST - Home Care` |
| Status | `ACTIVE` |

Packaging units:

| Unit | Conversion to base unit | Base unit | Purchase unit | Sale unit |
| --- | ---: | --- | --- | --- |
| `PIECE` | 1 | Yes | No | Yes |
| `CARTON` | 24 | No | Yes | No |

This means one CARTON contains 24 PIECE. Purchase with CARTON and sell or
return with PIECE.

### Supplier

| Field | Value |
| --- | --- |
| Supplier name | `TEST - Northstar Supply Co.` |
| Phone | `0000000000` |
| Address | `TEST Warehouse Road, Example Industrial Area` |
| GST | Leave blank |
| Payment terms (days) | `14` |
| Status | `ACTIVE` |

Leave GST blank for the main workflow. If you specifically need a format
validation check, use `27AAAAA0000A1Z5` only as a syntax example, not as a real
GST registration number.

### Customer

| Field | Value |
| --- | --- |
| Customer name | `TEST - Riverstone Stores` |
| Phone | `0000000000` |
| Address | `TEST Market Lane, Example District` |
| Area | `TEST - Lakeside` |
| Credit limit | `10000` |
| Payment terms (days) | `15` |
| Status | `ACTIVE` |

## 2. Purchase and stock receipts

Create this purchase before any sales transaction.

### Purchase `TEST-PO-1001`

| Field | Value |
| --- | --- |
| Supplier | `TEST - Northstar Supply Co.` |
| Purchase date | `2026-10-20` |
| Supplier invoice number | `TEST-PO-1001` |
| Initial status | `PENDING` |

Purchase line:

| Product | Unit | Quantity | Unit price | Discount | Tax | Line total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `TEST - Sparkle Soap Bar 100 g` | `CARTON` | 5 | 480 | 0 | 0 | 2400 |

Expected purchase total: `5 × 480 = 2400`.

Receipt sequence:

| Receipt | Quantity received | Stock added | Expected purchase status |
| --- | ---: | ---: | --- |
| First receipt | 3 CARTON | 72 PIECE | `PARTIALLY_RECEIVED` |
| Second receipt | 2 CARTON | 48 PIECE | `RECEIVED` |
| Total | 5 CARTON | 120 PIECE | `RECEIVED` |

Expected stock immediately after both receipts: **120 PIECE**.

### Supplier payments

| Payment | Purchase | Date | Amount | Method | Reference | Expected balance |
| --- | --- | --- | ---: | --- | --- | ---: |
| 1 | `TEST-PO-1001` | `2026-10-20` | 1000 | `UPI` | `TEST-UPI-SUP-001` | 1400 |
| 2 | `TEST-PO-1001` | `2026-10-20` | 1400 | `BANK_TRANSFER` | `TEST-BANK-SUP-002` | 0 |

The supported manual payment methods are Cash, UPI, Bank transfer, and Cheque.
Use a synthetic reference such as the values above.

## 3. First sale, delivery, payment, and return

### Order `TEST-SO-2001`

| Field | Value |
| --- | --- |
| Customer | `TEST - Riverstone Stores` |
| Order date | `2026-10-20` |
| Notes | `TEST workflow order one` |
| Initial status | `PENDING` |
| Next status | `CONFIRMED` |

Order line:

| Product | Unit | Quantity | Unit price | Discount | Tax | Expected total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `TEST - Sparkle Soap Bar 100 g` | `PIECE` | 10 | 30 | 0 | 0 | 300 |

### Invoice `TEST-INV-3001`

| Field | Value |
| --- | --- |
| Source order | `TEST-SO-2001` |
| Invoice number | `TEST-INV-3001` |
| Invoice date | `2026-10-20` |
| Initial status | `UNPAID` |

Invoice line:

| Product | Unit | Quantity | Unit price | Discount | Tax | Expected total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `TEST - Sparkle Soap Bar 100 g` | `PIECE` | 10 | 30 | 0 | 0 | 300 |

### Delivery for `TEST-INV-3001`

| Field | Value |
| --- | --- |
| Delivery date | `2026-10-20` |
| Delivery address | `TEST Market Lane, Example District` |
| Vehicle / driver / notes | Optional; use only synthetic text if entered |
| Initial status | `PENDING` |
| Status sequence | `PENDING` → `DISPATCHED` → `OUT_FOR_DELIVERY` → `DELIVERED` |

Expected stock once delivery is Delivered: `120 - 10 = 110 PIECE`.

### Customer payments for `TEST-INV-3001`

| Payment | Date | Amount | Method | Reference | Expected invoice status/balance |
| --- | --- | ---: | --- | --- | --- |
| 1 | `2026-10-20` | 120 | `UPI` | `TEST-UPI-CUS-001` | `PARTIALLY_PAID`, 180 remaining |
| 2 | `2026-10-20` | 180 | `CASH` | `TEST-CASH-CUS-002` | `PAID`, 0 remaining |

### Return against `TEST-INV-3001`

Create the return after the invoice is fully paid so its full value becomes
customer credit.

| Field | Value |
| --- | --- |
| Return date | `2026-10-20` |
| Reason | `QUALITY_ISSUE` |
| Notes | `TEST return after delivery` |
| Initial status | `REQUESTED` |
| Required status sequence | `REQUESTED` → `APPROVED` → `RECEIVED` |

Return line:

| Product | Unit | Quantity | Condition | Unit value | Expected credit |
| --- | --- | ---: | --- | ---: | ---: |
| `TEST - Sparkle Soap Bar 100 g` | `PIECE` | 2 | `RESELLABLE` | 30 | 60 |

Expected result after receipt:

- Stock: `110 + 2 = 112 PIECE` because the condition is Resellable.
- Invoice `TEST-INV-3001` remains paid.
- Customer credit balance: `60`.

## 4. Second sale: apply customer credit

This proves the credit created by the return can be used for another invoice.

### Order `TEST-SO-2002`

| Field | Value |
| --- | --- |
| Customer | `TEST - Riverstone Stores` |
| Order date | `2026-10-20` |
| Notes | `TEST credit-application order` |
| Status sequence | `PENDING` → `CONFIRMED` |

| Product | Unit | Quantity | Unit price | Discount | Tax | Expected total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `TEST - Sparkle Soap Bar 100 g` | `PIECE` | 1 | 30 | 0 | 0 | 30 |

### Invoice and delivery `TEST-INV-3002`

| Field | Value |
| --- | --- |
| Invoice number | `TEST-INV-3002` |
| Date | `2026-10-20` |
| Initial status | `UNPAID` |
| Delivery statuses | `PENDING` → `DISPATCHED` → `OUT_FOR_DELIVERY` → `DELIVERED` |

Expected stock after the second delivery: `112 - 1 = 111 PIECE`.

Open the Invoice Detail page for `TEST-INV-3002` and use **Apply credit**.

| Before applying credit | Credit applied | After applying credit |
| ---: | ---: | --- |
| Customer credit 60; invoice balance 30 | 30 | Invoice `PAID`; customer credit 30 remains |

## 5. Expected checkpoints

Use this table to quickly spot an incorrect calculation.

| Checkpoint | Expected stock (PIECE) | Expected customer credit | Key status |
| --- | ---: | ---: | --- |
| After both purchase receipts | 120 | 0 | Purchase `RECEIVED` |
| After delivery 1 | 110 | 0 | Delivery 1 `DELIVERED` |
| After return receipt | 112 | 60 | Return `RECEIVED` |
| After delivery 2 | 111 | 60 | Delivery 2 `DELIVERED` |
| After applying credit | 111 | 30 | Invoice 2 `PAID` |

## 6. Optional negative-test data

Use a new record or cancel the attempt when the form permits. Do not alter the
main workflow values above.

| Test | Input | Expected outcome |
| --- | --- | --- |
| Duplicate category | `TEST - Home Care` again | Duplicate rejected |
| Duplicate product SKU | `TEST-SOAP-100` again | Duplicate rejected |
| Too much receipt | Receive 6 CARTON on a 5-CARTON purchase | Rejected |
| Too much invoice quantity | Invoice 11 PIECE on `TEST-SO-2001` | Rejected |
| Too much customer payment | Pay 301 on the 300 invoice before payments | Rejected |
| Too much return quantity | Request 11 PIECE for the 10-PIECE sale | Rejected |

## 7. Cleanup and retention

There is no general delete/reset workflow in the current UI for the created
master data. Keep test records clearly prefixed and ask the environment owner
how they want test data retained or reset. Do not run manual SQL or delete
shared data to clean up. Products, customers, and suppliers can be made
inactive if the owner approves that as the test-environment cleanup method.
