
# DukaanPulse: project briefing for an AI coding agent

You are being given the source code of DukaanPulse, a small ERP web app for a
wholesale distributor (inventory, purchasing, sales, invoicing, deliveries,
payments, returns). A human is sharing it with you to understand it, run it,
fix it, or extend it.

How to use this document:

- READ THE CODE BEFORE TRUSTING THIS DOCUMENT. It was written from memory of
  the project's history and may be slightly out of date. If code and document
  disagree, the code wins. Say so when you find a mismatch.
- Start by skimming the folders named below, then summarise your understanding
  back to the human and ask what they want to do. Do not start changing things.
- If you can't open the zip, ask the human to paste the specific files you need.
- Make minimal, targeted edits. Don't rewrite or "modernise" working code.
- Never ask for, print, or commit secrets (database URLs, passwords).

## 1. Stack and layout

Backend (backend/): FastAPI, SQLAlchemy 2.0 (Mapped / mapped_column), Pydantic v2,
PostgreSQL via psycopg v3 (hosted on Neon, any Postgres works).

- app/main.py: app setup, CORS (allows http://localhost:5173), includes all routers
- app/core/config.py: settings read from .env (DATABASE_URL)
- app/db/database.py: engine, SessionLocal, Base, get_db
- app/models/: SQLAlchemy models. app/models/__init__.py must import EVERY model
  (needed so relationship("Name") strings resolve). New model: register it there.
- app/schemas/: Pydantic request/response models
- app/routers/: one file per resource (categories, products, customers, suppliers,
  purchases, inventory, orders, invoices, deliveries, payments, purchase_payments,
  returns, dashboard). New router: include it in main.py.
- app/services/: shared business logic (inventory_service, invoice_service,
  order_service, purchase_service, return_service, status_rules)

Frontend (frontend/): React 18, Vite, react-router-dom 6, axios, recharts,
lucide-react. Plain JavaScript (no TypeScript), plain CSS in src/index.css with
design tokens (no Tailwind, no UI library).

- src/api/client.js: axios instance (30 s timeout) + extractErrorMessage()
- src/api/endpoints.js: one function per backend endpoint
- src/pages/: Dashboard, Products, Customers, Suppliers, Purchases, Orders,
  Invoices, InvoiceDetail, Deliveries, Payments (customer payments),
  PurchasePayments (supplier payments), Returns, Inventory (stock lookup)
- src/components/: Layout, Modal, Feedback (Spinner/EmptyState/ErrorBanner),
  StatCard, StatusBadge, ProductPackagingSelect, ToastProvider, ConfirmProvider,
  ErrorBoundary
- src/lib/: messages.js, formValidation.js

## 2. Running it

Backend:
  cd backend
  python -m venv venv  (activate it)
  pip install -r requirements.txt
  copy .env.example to .env and set DATABASE_URL (psycopg v3 driver, so the URL
  normally looks like postgresql+psycopg://user:pass@host/db?sslmode=require;
  check .env.example)
  uvicorn app.main:app --reload --port 8000
  API docs: http://127.0.0.1:8000/docs   health: /health and /health/db

Frontend:
  cd frontend
  npm install
  copy .env.example to .env  (VITE_API_BASE_URL=http://127.0.0.1:8000)
  npm run dev   (http://localhost:5173)

IMPORTANT: there are no migrations and no create_all(). The database schema
must already exist: load schema.sql into an empty Postgres database first. The app
also needs at least ONE row in `categories` before a product can be added
(there is no category-creation endpoint). Example:
  INSERT INTO categories (category_name, status) VALUES ('General', 'ACTIVE');
(check the real column names in schema.sql.)

## 3. Core design

- Inventory is an append-only ledger: table inventory_movements. Stock of a
  product = SUM(base_quantity). Quantities are stored in the product's BASE unit.
  product_packaging defines other units via conversion_to_base (e.g. 1 CARTON = 12
  PIECE). A composite FK guarantees a packaging belongs to its product.
- Movement types used by the app: PURCHASE (+), SALE (-), RETURN (+). The DB
  also allows OPENING / DAMAGE / ADJUSTMENT but nothing creates them. A DB CHECK
  (chk_inventory_reference) ties each type to the right reference column and sign.
- Many rules live in DB CHECK constraints (status lists, payment methods, positive
  quantities, GST regex...). If you add a status or payment method, update the
  constraint too (give the human the ALTER TABLE; don't assume you can run it).
  When the app returns a generic "conflicts with existing data" error, the real
  cause is usually a CHECK/UNIQUE violation; the 409 detail includes it.
- Status fields that look stored are often DERIVED and recalculated by a service:
  invoice status (invoice_service.recalculate_invoice_status), order status
  (order_service.recalculate_order_status), purchase status
  (purchase_service.recalculate_purchase_status). Don't set them by hand elsewhere.

## 4. Business rules (the part that's easy to break)

Purchases: statuses PENDING, PARTIALLY_RECEIVED, RECEIVED, CANCELLED. Always
created PENDING with received_quantity 0. Stock is added ONLY when goods are
received: PATCH /purchases/{id}/receive (incremental, per item) or PATCH
/purchases/{id}/status RECEIVED (receives whatever is still outstanding).
Cancelling keeps what was already received. Totals are validated server-side.

Orders: PENDING -> CONFIRMED -> COMPLETED, or CANCELLED. PARTIALLY_FULFILLED is
reached automatically. There is deliberately NO stock check when creating or
confirming an order (real wholesalers take orders before stock arrives).

Invoices: created from a CONFIRMED or PARTIALLY_FULFILLED order. One order can have
several invoices (partial invoicing): each line is validated against that line's
remaining quantity (ordered minus quantity on other non-cancelled invoices). No
order_items.fulfilled column exists; it's computed from invoice_items. Invoice
totals are validated server-side (tolerance 0.01). Creating an invoice does NOT
touch stock. An invoice can be cancelled only if UNPAID and it has no active
delivery; cancelling frees its quantity back onto the order.

Deliveries: PENDING -> DISPATCHED -> OUT_FOR_DELIVERY -> DELIVERED, FAILED (can
retry to OUT_FOR_DELIVERY), CANCELLED. Stock is deducted ONLY on the transition to
DELIVERED (create_sale_movement; it takes a Postgres advisory lock per product and
rejects the sale if stock is insufficient). A delivery covers the WHOLE invoice
(it has no line items), so partial delivery of one invoice is not supported; the
workaround is partial invoicing. At most one ACTIVE (non-cancelled) delivery per
invoice, enforced by a partial unique index, and a cancelled one can be re-done.

Customer payments (table payments): amount must not exceed the invoice's remaining
balance (advisory-locked). Allowed methods: CASH, UPI, BANK_TRANSFER, CHEQUE for
users; RETURN_CREDIT and CREDIT_APPLIED are system-generated only.

Returns: REQUESTED -> APPROVED -> RECEIVED (REJECTED/CANCELLED exist in the DB but
have no endpoint). Return lines must be products actually sold on that invoice,
and quantity <= sold minus already requested/returned (REJECTED/CANCELLED don't
count). On RECEIVE: only RESELLABLE items go back into stock; credit value =
quantity x the invoice's unit_price (discount/tax not prorated). That credit is
added to the invoice as a RETURN_CREDIT payment, CAPPED at what the invoice still
owes; any excess goes to customers.credit_balance. The customer later uses it via
POST /payments/apply-credit (a CREDIT_APPLIED payment that reduces credit_balance).
There is intentionally no cash-refund feature (matches wholesale credit-note practice).

Supplier payments (table purchase_payments): any non-cancelled purchase can be paid
(advance payments allowed); remaining = purchase total minus payments; there is no
payment-status column on purchases.

Active / inactive: an INACTIVE customer, supplier or product cannot be used on a NEW
order or purchase (backend: services/status_rules.py; frontend: dropdowns list active
only). Existing records are unaffected and can still be confirmed, received, paid.

Dashboard: purchase totals count only RECEIVED and PARTIALLY_RECEIVED purchases.
Pending amount is computed per invoice and floored at 0; refund_due_amount and
total_customer_credit are reported separately.

## 5. Conventions to follow

Backend:

- Write endpoints wrap their work in try/except: HTTPException -> rollback and
  re-raise; IntegrityError -> rollback + 409; SQLAlchemyError -> rollback + 500.
- The frontend shows the backend's `detail` text to end users as-is, so keep
  every `detail` human-readable, specific, and free of technical jargon.
- Some endpoints take `data: dict = Body(...)` (status changes, apply-credit). Their
  values arrive untyped: validate and cast IDs to int yourself, or Postgres
  rejects a bigint compared with a string.
- Money is Numeric in the DB but handled as float in Python with small tolerances
  (0.01 / 0.0001). Don't "fix" this casually.
- Some files use Windows (CRLF) line endings; preserve them.

Frontend:

- Page pattern: local state, a load() function, a create modal, row actions.
- Feedback pattern: success -> toast.success(successMessage("Product", "added"))
  producing "[Entity] [action] successfully."; failure inside a form modal -> inline
  ErrorBanner; failure of a row action -> toast.error; page-load failure ->
  persistent ErrorBanner; destructive or irreversible actions -> await confirm({...})
  first; buttons show busy labels ("Saving...") and are disabled while in flight.
- extractErrorMessage() turns API errors into text (backend detail first, then
  status-based fallbacks, timeout and network messages).
- formValidation.js produces friendly browser validation messages by reading each
  field's <label></label> inside a `.field` wrapper (or its placeholder). Keep that markup.

## 6. Known gaps (not bugs you introduced)

- No authentication or authorization at all; every endpoint is open.
- No category create/edit endpoint or page. No automated tests. No migrations.
- No inventory-movement history endpoint/page (only GET /inventory/stock/{id}); no
  endpoints for opening stock, damage or manual adjustments.
- Deliveries have no line items (no partial delivery per invoice).
- No reject/cancel endpoints for returns; no way to pay out customer credit in cash.
- Products list computes stock per product in a loop (N+1): fine at small scale.
- Form <label></label>s are not linked to inputs via htmlFor/id (accessibility gap).
- The toast / confirm-dialog / validation / modal-accessibility layer was added
  late and was only syntax-checked and logic-tested in isolation, not
  verified in a real browser. Treat it as lightly tested.
- Planned but not built: reports (customer receivables with aging, supplier
  payables, stock valuation). Profit/margin reports need a costing method decided first.

## 7. Working agreements for you

- Prefer small, reviewable changes; show the exact files or diffs you changed.
- Before changing the database, explain why and give the SQL for the human to run.
- Don't remove or weaken a business rule above without saying so explicitly.
- After a change, say what you actually verified (ran / read / assumed) and what
  you did not.
