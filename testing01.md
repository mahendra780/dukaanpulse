# DukaanPlus manual testing guide

This is a beginner-friendly guide for testing the application without changing
its code or database schema. It reflects the application code inspected on
2026-10-20. Where deployment details are not stored in the repository, this
guide labels them **owner confirmation required** rather than guessing.

Use the matching, internally consistent records in [sample_data.md](sample_data.md).
Every sample record begins with `TEST -` or `TEST-`, so it is easy to recognise.

## 1. Before you start

### Choose a safe environment

Use a dedicated test environment and test database. Do not create the sample
data in a shared live/production database. The application has no user-facing
tenant selection or tenant-isolation feature in the inspected code, so do not
try cross-tenant testing unless the system owner has separately provisioned
and verified that isolation.

Fill these in with information supplied by the system owner:

| Item | Value to obtain |
| --- | --- |
| Frontend address | `<OWNER-SUPPLIED-URL>` |
| Test environment/database | `<OWNER-SUPPLIED-NON-PRODUCTION-ENVIRONMENT>` |
| Test administrator | `<OWNER-CREATED-ADMIN-USERNAME>` |
| Test roles/users | `<OWNER-CREATED-ROLE-USERNAMES>` |
| Test date | `<YYYY-MM-DD>` |

Never put passwords, tokens, database connection strings, or real customer
data in this document, screenshots, or bug reports.

### How local access differs from remote access

For local testing, open the frontend address provided by the developer (often
an address on the same computer). For a remote test deployment, use only the
HTTPS address supplied by the owner. A `localhost` address works only on the
computer running the app; sending it to a colleague will not let them reach
your machine.

**Owner confirmation required:** the repository does not declare a deployed
URL, hosting provider, test accounts, or a test-data reset process.

## 2. Login, logout, and session checks

There is no self-registration, mobile login, OTP, or password-recovery flow in
the inspected application. An administrator creates users. The first
administrator is created by the system owner using the documented backend
administration process.

1. Open the supplied frontend address.
2. Enter an owner-created username and password, then select **Sign in**.
3. Confirm that a successful login opens the Dashboard (or the protected page
   you originally requested).
4. Select **Logout** in the navigation. Confirm you return to the login page.
5. Try a wrong password and an unknown username. Both should show the same
   generic message: `Incorrect username or password.` The app intentionally
   does not reveal which part was wrong.
6. While logged out, paste a protected application URL into the browser. You
   should be redirected to Login rather than seeing the page.

### Session expiry

Access tokens have a configurable lifetime (the code's default is 480 minutes).
For a practical expiry check, ask the owner to provide a disposable test
environment with a short, temporary lifetime; do not change production
configuration or wait for the normal lifetime. After it expires, refresh a
protected page. The app should clear the local session and return to Login with
a session-expired message. **Owner confirmation required:** whether a separate
short-lifetime test environment is available.

### Password change

From the signed-in user menu, use **Change password**.

1. Enter the current password, a new password of at least 10 characters, and
   its confirmation.
2. Confirm a validation error for a short password, a mismatch, or a new
   password equal to the current password.
3. After a successful change, confirm the app signs the user out.
4. Sign in with the new password. The old password must fail.

Do not record the password used for this test.

## 3. Roles and permission checks

The backend enforces permissions; hiding a navigation item is only a user
interface convenience. A direct request without the required permission
returns a human-readable 403 response. Use separate owner-created users for
each role below. The application checks a user's active status and permissions
on requests, rather than trusting role details saved in the browser token.

| Role | Expected visible areas |
| --- | --- |
| ADMIN | All areas, including Users |
| SALES | Dashboard, Products, Customers, Suppliers, Orders, Invoices, Deliveries, Customer payments, Returns, Stock lookup |
| WAREHOUSE | Dashboard, Products, Customers, Suppliers, Purchases, Orders, Invoices, Deliveries, Returns, Stock lookup |
| ACCOUNTS | All business areas except Users |
| VIEWER | All business areas except Users, with read-only access |

Suggested check for each role:

1. Sign in as that role and open every visible sidebar entry. Each page should
   load without a permission error.
2. Confirm that write controls are absent where the role has read-only access.
3. For one action that should be forbidden, attempt it through the normal UI
   if a control is available. It must not succeed. Do not attempt to bypass the
   UI or authorization.

Important write permissions verified in the code include:

| Activity | Permission | Roles that have it |
| --- | --- | --- |
| Add category | `categories:write` | ADMIN, WAREHOUSE |
| Manage products | `products:write` | ADMIN, WAREHOUSE |
| Manage customers/orders/invoices/customer payments | corresponding `:write` | ADMIN, SALES; customer payments also ACCOUNTS |
| Manage suppliers/purchases/supplier payments | corresponding `:write` | ADMIN, WAREHOUSE for suppliers/purchases; ADMIN, ACCOUNTS for supplier payments |
| Approve returns | `returns:approve` | ADMIN, ACCOUNTS |
| Receive returns | `returns:receive` | ADMIN, WAREHOUSE |
| Create/manage users | `users:manage` | ADMIN only |

An inactive user should no longer be able to use an existing session. Have an
administrator deactivate a disposable test user, then refresh a protected page
in that user's existing browser session. It should require login again. Do not
deactivate or demote the only active administrator.

## 4. Build the test master data

Sign in as ADMIN or WAREHOUSE for categories/products, and ADMIN for the
complete sequence. Work through the rows in [sample_data.md](sample_data.md)
in order.

### Category and product

1. Open **Products**.
2. Select **Add category**. Enter `TEST - Home Care`, leave the status as
   Active, and save. A successful result shows a confirmation and refreshes
   the category choices.
3. Try adding the exact same category again. It should be rejected as a
   duplicate.
4. Select **Add product** and create `TEST - Sparkle Soap Bar 100 g` with the
   supplied SKU and packaging units.
5. Confirm the product appears in the list and that both packaging units are
   available in later purchase/order forms where appropriate.

The category name is required and limited to 100 characters. Product name,
SKU, category, status, and at least one packaging unit are required. A product
must have exactly one base unit; each conversion must be greater than zero.

### Supplier and customer

1. Open **Suppliers** and create the sample supplier. You may leave GST blank;
   if supplied, it must use the accepted GST format.
2. Open **Customers** and create the sample customer.
3. Confirm both records are Active and can be selected in the later forms.

Names need at least two characters. Customer address and area are required;
credit limit and payment terms cannot be negative. Supplier address is
required, and supplier payment terms cannot be negative.

If you deactivate a customer, supplier, or product, it should no longer be
usable for new relevant transactions. Use only disposable `TEST` records for
this check, then restore Active status before continuing.

## 5. End-to-end stock-to-cash workflow

Perform these in order because each step depends on the last one. Exact sample
values and expected calculations are in [sample_data.md](sample_data.md).

### A. Purchase and receive stock

1. Open **Purchases** and create purchase `TEST-PO-1001` for five CARTON of
   the sample soap at 480 each. Expected total: 2,400.
2. Confirm its initial status is Pending and that stock has not increased yet.
3. Use **Receive items** to receive three CARTON. This is a partial receipt.
4. Receive the remaining two CARTON. The purchase should be Received.
5. Open **Stock lookup** and confirm stock is 120 PIECE: five cartons times
   the 24-piece carton conversion.

Purchase quantities must be positive. Received quantity cannot exceed the
ordered quantity. A partial receipt creates stock only for what was received;
cancelling a partly received purchase does not remove stock already received.

### B. Supplier payment

1. Open **Supplier payments**.
2. Record a partial payment of 1,000 against `TEST-PO-1001`, then a second
   payment of 1,400.
3. Confirm the remaining amount is never allowed to go below zero.

The manual payment choices are Cash, UPI, Bank transfer, and Cheque. Keep any
reference value synthetic (for example, `TEST-UPI-SUP-001`).

### C. Sales order, invoice, delivery

1. Open **Orders** and create `TEST-SO-2001` for ten PIECE of the product at
   the sample customer.
2. Change its status from Pending to Confirmed. Do not mark it Completed
   manually if you intend to invoice it; invoice quantities drive the normal
   fulfilment state.
3. Open **Invoices**, create `TEST-INV-3001` from the confirmed order, and
   invoice ten PIECE at 30 each. Expected total: 300.
4. Open **Deliveries**, create a Pending delivery for that invoice, then move
   it through Dispatched and Out for delivery to Delivered.
5. Check **Stock lookup**. Expected stock is now 110 PIECE.

Creating an order or invoice does not reduce stock. Stock is reduced only when
a delivery reaches Delivered. If stock is insufficient then, delivery must
fail rather than making stock negative.

### D. Customer payment, return, and customer credit

1. Open **Customer payments** and record 120 against `TEST-INV-3001`.
   Confirm the invoice becomes Partially paid.
2. Record the remaining 180. Confirm the invoice becomes Paid.
3. Open **Returns** and request a return of two PIECE from that invoice with
   condition Resellable and reason Quality issue.
4. Sign in as an ACCOUNTS or ADMIN user to approve it. Then sign in as a
   WAREHOUSE or ADMIN user to receive it.
5. After receipt, confirm stock rises to 112 PIECE and the customer has a
   credit balance of 60. A fully paid invoice receives the return value as
   customer credit rather than another invoice payment.
6. Create and complete the second small order/invoice in the sample file.
   On its invoice detail page, apply 30 of the customer credit. Confirm the
   invoice is Paid and the remaining customer credit is 30.

Only Resellable returned stock goes back into inventory. All received return
values are calculated at the original product unit price. The app applies as
much as possible to the invoice; any excess becomes customer credit. There is
no cash-refund workflow in the inspected UI/API.

## 6. Status and validation checks

Use fresh `TEST` records where a check would make a transaction unusable.

| Area | Check | Expected result |
| --- | --- | --- |
| Category | Blank name or more than 100 characters | Form/API rejects it; no category created |
| Product | Duplicate SKU | Rejected; SKU remains unique |
| Purchase | Receive more than ordered | Rejected; stock does not over-increase |
| Purchase | Try to edit a Received or Cancelled purchase | Not permitted |
| Order | Move Pending directly to Completed | Not offered by the normal status flow |
| Invoice | Invoice more than the remaining order quantity | Rejected |
| Delivery | Create a second active delivery for one invoice | Rejected |
| Delivery | Mark Delivered without enough stock | Rejected; no negative stock |
| Customer payment | Amount above invoice balance | Rejected |
| Supplier payment | Amount above purchase balance | Rejected |
| Return | Quantity above available returnable quantity | Rejected |
| Return | Receive before approval | Not permitted |
| Invoice | Cancel a paid/partly paid invoice | Not permitted |

Normal workflow restrictions in the current UI include these status paths:

- Orders: Pending → Confirmed or Cancelled; Confirmed/Partially fulfilled →
  Completed or Cancelled. Invoice quantities normally drive Partially fulfilled
  and Completed.
- Deliveries: Pending → Dispatched or Cancelled; Dispatched → Out for delivery,
  Failed, or Cancelled; Out for delivery → Delivered, Failed, or Cancelled;
  Failed → Out for delivery or Cancelled.
- Returns: Requested → Approved → Received. Approval and receipt require
  different permissions.

## 7. Dashboard and regression smoke check

After the workflow, refresh the Dashboard and relevant lists. Confirm that
created records are searchable and displayed with their current statuses. The
dashboard is read-only; its totals and charts depend on transaction dates, so
select the sample-data year if the page provides a year choice.

Then run this short regression pass:

- Login and logout work; bad credentials remain generic.
- A Viewer can open visible pages but cannot create or change records.
- SALES can complete the customer/order/invoice/payment side but cannot manage
  products or purchases.
- WAREHOUSE can complete catalog/purchase/delivery/return-receipt tasks but
  cannot approve a return.
- ACCOUNTS can approve a return and record payments but cannot receive it.
- Existing non-test records still display normally.

## 8. Record results and report defects

For each test, record the tester, environment, role, test-data identifier,
actual result, and a screenshot with sensitive values obscured. A useful
defect report includes:

```text
Title: [area] short description
Environment: owner-supplied test environment
Role: ADMIN / SALES / WAREHOUSE / ACCOUNTS / VIEWER
Test record: TEST-...
Steps: numbered, repeatable actions
Expected: what this guide says should happen
Actual: what happened, including exact visible message
Evidence: screenshot/video with passwords, tokens, and personal data removed
```

## 9. Known limits and owner follow-up

These are code-confirmed limits, not failed tests:

- No self-registration, OTP, password recovery, opening-stock entry, inventory
  adjustment screen, inventory-movement history screen, or cash-refund flow is
  implemented in the inspected application.
- There is no documented deployed URL, test login, environment reset, or
  tenant-isolation implementation in the repository. The owner must provide
  those before external testing.
- Product, customer, and supplier records can be set inactive. There is no
  general delete/reset workflow in the UI for the master data created here.

Do not infer a missing feature from these instructions. Log it as a product
question for the owner if it is required for the test plan.
